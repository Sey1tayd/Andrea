from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils.text import Truncator
from django.middleware.csrf import get_token
from django.contrib import messages
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import logging
import threading

from .models import Chat, Message
from .services import openrouter_service
from .personas import PERSONAS, get_provider_model, DEFAULT_MODEL_KEY

logger = logging.getLogger(__name__)

def generate_initial_response_async(chat_id, persona_key=None):
    """Asenkron olarak ilk LLM yanıtını oluştur"""
    try:
        chat = Chat.objects.get(pk=chat_id)
        persona = PERSONAS.get(persona_key)

        # OpenRouter API ile yanıt oluştur
        if settings.OPENROUTER_API_KEY and openrouter_service:
            # DB'deki tüm mesajları (system + user) sırayla al
            previous = list(chat.messages.all().values('role', 'content'))
            messages = [{'role': m['role'], 'content': m['content']} for m in previous]
            assistant_response = openrouter_service.chat_with_persona(messages, persona=persona, ui_model_key=persona_key)
        else:
            # API key yoksa varsayılan mesaj (kişiliğe saygılı)
            first_user = chat.messages.filter(role='user').first()
            user_prompt = first_user.content if first_user else ''
            if persona_key == 'monday':
                # Kısa, iğneleyici ama yardımcı – giriş cümlesi yok
                assistant_response = f"{user_prompt}\n\nTamam. Ne istiyorsun? Hızlı söyle, çözeyim."
            else:
                assistant_response = f"{user_prompt}\n\nNasıl yardımcı olayım?"
        
        Message.objects.create(chat=chat, role='assistant', content=assistant_response)
        logger.info(f"Async LLM response generated for chat {chat_id}")
        
    except Exception as e:
        logger.error(f"OpenRouter API error in generate_initial_response_async: {str(e)}")
        try:
            chat = Chat.objects.get(pk=chat_id)
            first_user = chat.messages.filter(role='user').first()
            safe_text = first_user.content if first_user else ''
            # Kredi hatası durumunda daha kibar bir mesaj
            if "402" in str(e) or "credits" in str(e).lower():
                assistant_response = (
                    f"Merhaba! Mesajınızı aldım: '{safe_text}'\n\nŞu anda API kredilerimiz tükendi, ancak sohbet etmeye devam edebiliriz. "
                    "Ne hakkında konuşmak istersiniz? Sorularınızı sorabilir, sohbet edebilir veya herhangi bir konuda yardım isteyebilirsiniz."
                )
            else:
                assistant_response = (
                    f"Merhaba! İlk mesajınızı aldım: '{safe_text}'\n\nBen Andrea AI'yım ve size yardımcı olmaya hazırım. "
                    "Ne hakkında konuşmak istersiniz? Sorularınızı sorabilir, sohbet edebilir veya herhangi bir konuda yardım isteyebilirsiniz."
                )
            Message.objects.create(chat=chat, role='assistant', content=assistant_response)
        except Exception as db_error:
            logger.error(f"Database error in generate_initial_response_async: {str(db_error)}")

def _update_title_async(chat_id, prompt):
    try:
        if not openrouter_service:
            return
        title = openrouter_service.generate_title(prompt)
        if title:
            from .models import Chat
            Chat.objects.filter(pk=chat_id).update(title=Truncator(title).chars(50))
    except Exception as e:
        logger.error(f"Async title update error: {e}")

@login_required
@require_POST
def start_chat(request):
    prompt = (request.POST.get('prompt') or '').strip()
    if not prompt:
        return redirect('home')

    persona_key = (request.POST.get('persona') or '').strip()
    persona = PERSONAS.get(persona_key)

    # 1) ANI: hızlı, yerel başlıkla sohbeti oluştur
    fast_title = Truncator(prompt).chars(50)
    chat = Chat.objects.create(user=request.user, title=fast_title)

    # 2) (Opsiyonel) persona için system mesajını DB'ye yaz
    if persona and persona.get("system_prompt"):
        Message.objects.create(chat=chat, role='system', content=persona["system_prompt"])

    # 3) Kullanıcı mesajını yaz
    Message.objects.create(chat=chat, role='user', content=prompt)

    # 4) İlk yanıt: arkada
    t1 = threading.Thread(target=generate_initial_response_async, args=(chat.id, persona_key), daemon=True)
    t1.start()

    # 5) Başlık: arkada (LLM)
    if settings.OPENROUTER_API_KEY and openrouter_service:
        t2 = threading.Thread(target=_update_title_async, args=(chat.id, prompt), daemon=True)
        t2.start()

    # 6) HEMEN detay sayfasına geç
    return redirect('chat:detail', chat_id=chat.id)

@login_required
def chat_detail(request, chat_id):
    chat = get_object_or_404(Chat, pk=chat_id, user=request.user)
    # Sidebar için kullanıcının sohbetleri:
    chats = request.user.chats.only('id','title','updated_at')[:50]
    # CSRF token (AJAX post'lar için lazım)
    csrf_token = get_token(request)
    return render(request, 'chat/detail.html', {
        'chat': chat,
        'messages': chat.messages.all(),
        'chats': chats,
        'csrf_token': csrf_token
    })

@login_required
@require_POST
def send_message(request, chat_id):
    chat = get_object_or_404(Chat, pk=chat_id, user=request.user)
    text = (request.POST.get('message') or '').strip()
    if not text:
        return JsonResponse({'ok': False, 'error': 'Mesaj boş olamaz.'}, status=400)

    # Get model key from request (if provided)
    model_key = request.POST.get('model_key', DEFAULT_MODEL_KEY)
    used_fallback = False

    # Kullanıcı mesajını kaydet
    user_msg = Message.objects.create(chat=chat, role='user', content=text)

    # OpenRouter API ile yanıt oluştur
    try:
        if settings.OPENROUTER_API_KEY and openrouter_service:
            previous = list(chat.messages.all().values('role','content'))
            messages = [{'role': m['role'], 'content': m['content']} for m in previous]
            
            # Get the actual model name from mapping
            provider_model = get_provider_model(model_key)
            fallback_model = get_provider_model(DEFAULT_MODEL_KEY)
            
            assistant_response = openrouter_service.chat(
                messages, 
                model=provider_model,
                fallback_model=fallback_model
            )
            
            # Check if fallback was used
            if provider_model != fallback_model and "Seçtiğin model şu an kullanılamıyor" in assistant_response:
                used_fallback = True
        else:
            # API key yoksa varsayılan yanıt
            assistant_response = f"Mesajınızı aldım: '{text}'\n\nBu konuda size nasıl yardımcı olabilirim? Başka sorularınız varsa çekinmeden sorun!"
    except Exception as e:
        logger.error(f"OpenRouter API error in send_message: {str(e)}")
        assistant_response = f"Mesajınızı aldım: '{text}'\n\nBu konuda size nasıl yardımcı olabilirim? Başka sorularınız varsa çekinmeden sorun!"
    
    assistant_msg = Message.objects.create(chat=chat, role='assistant', content=assistant_response)

    return JsonResponse({
        'ok': True,
        'used_fallback': used_fallback,
        'messages': [
            {'role': user_msg.role, 'content': user_msg.content, 'created_at': user_msg.created_at.isoformat()},
            {'role': assistant_msg.role, 'content': assistant_msg.content, 'created_at': assistant_msg.created_at.isoformat()},
        ]
    })

@login_required
def check_initial_response(request, chat_id):
    """İlk LLM yanıtının hazır olup olmadığını kontrol et"""
    chat = get_object_or_404(Chat, pk=chat_id, user=request.user)
    
    # Assistant mesajı var mı kontrol et
    assistant_messages = chat.messages.filter(role='assistant')
    
    if assistant_messages.exists():
        latest_message = assistant_messages.latest('created_at')
        return JsonResponse({
            'ok': True,
            'ready': True,
            'message': {
                'role': latest_message.role,
                'content': latest_message.content,
                'created_at': latest_message.created_at.isoformat()
            }
        })
    else:
        return JsonResponse({
            'ok': True,
            'ready': False
        })

@login_required
@require_POST
def delete_chat(request, chat_id):
    chat = get_object_or_404(Chat, pk=chat_id, user=request.user)
    chat_title = chat.title
    chat.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'message': f'Sohbet "{chat_title}" silindi.'})
    else:
        messages.success(request, f'Sohbet "{chat_title}" başarıyla silindi.')
        return redirect('home')