import openai
import os
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class OpenRouterService:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = settings.OPENROUTER_BASE_URL
        self.model = settings.OPENROUTER_MODEL
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set in environment variables")
        
        # Attach OpenRouter recommended headers for better routing and auth context
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            default_headers={
                "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost"),
                "X-Title": os.getenv("OPENROUTER_APP_NAME", "Andrea Chat"),
            },
        )

    def chat(self, messages, *, model=None, temperature=None, max_tokens=None, fallback_model=None):
        """
        messages: [{'role':'system'|'user'|'assistant', 'content':'...'}, ...]
        """
        try:
            resp = self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature if temperature is not None else 0.7,
                max_tokens=max_tokens or 1024,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            # Check if it's a 404 error (model not found)
            if hasattr(e, 'response') and e.response and e.response.status_code == 404:
                logger.warning(f"Model 404: {model or self.model} → fallback {fallback_model or self.model}")
                if fallback_model and fallback_model != (model or self.model):
                    try:
                        resp = self.client.chat.completions.create(
                            model=fallback_model,
                            messages=messages,
                            temperature=temperature if temperature is not None else 0.7,
                            max_tokens=max_tokens or 1024,
                        )
                        return (resp.choices[0].message.content or "").strip()
                    except Exception as fallback_error:
                        logger.error(f"Fallback model also failed: {str(fallback_error)}")
                        return "Seçtiğin model şu an kullanılamıyor. Varsayılanla devam ettim."
                else:
                    return "Seçtiğin model şu an kullanılamıyor. Varsayılanla devam ettim."
            else:
                # Detect 401 Unauthorized to guide configuration fixes
                status = getattr(getattr(e, 'response', None), 'status_code', None)
                if status == 401:
                    logger.error("OpenRouter API 401 Unauthorized. Check OPENROUTER_API_KEY and base URL.")
                    return "Üzgünüm, kimlik doğrulama sorunu oluştu. Lütfen daha sonra tekrar deneyin."
                logger.error(f"OpenRouter API error: {str(e)}")
                return "Üzgünüm, şu anda bir hata oluştu. Lütfen daha sonra tekrar deneyin."

    def chat_with_persona(self, messages, persona=None, ui_model_key=None):
        """
        persona dict: {'system_prompt': str, 'model': optional, 'temperature': optional}
        ui_model_key: UI model key for fallback handling
        """
        if persona and persona.get("system_prompt"):
            messages = [{'role': 'system', 'content': persona['system_prompt']}] + messages

        # Get fallback model from mapping
        fallback_model = None
        if ui_model_key:
            from .personas import get_provider_model, DEFAULT_MODEL_KEY
            fallback_model = get_provider_model(DEFAULT_MODEL_KEY)

        return self.chat(
            messages,
            model=persona.get("model") if persona else None,
            temperature=persona.get("temperature") if persona else None,
            fallback_model=fallback_model
        )

    def generate_title(self, prompt, max_tokens=100):
        """
        İlk kullanıcı mesajından kısa, net bir sohbet başlığı üret.
        Çıktı: sadece başlık metni (tırnak, emoji yok), tercihen 50 karakteri geçmesin.
        Mesaj Türkçeyse Türkçe başlık, değilse orijinal dilde bırak.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "Kullanıcının ilk mesajına göre sohbet için kısa ve öz bir başlık üret. "
                    "Sadece başlığı döndür: tırnak, emoji, açıklama yok. 50 karakteri aşma."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        
        try:
            title = self.chat(messages, max_tokens=max_tokens, temperature=0.2)
            return (title or "").strip().strip('"').strip()
        except Exception as e:
            logger.error(f"OpenRouter title generation error: {str(e)}")
            return None

# Create a singleton instance (safe init)
try:
    openrouter_service = OpenRouterService()
except Exception as e:
    logger.warning(f"OpenRouterService disabled: {e}")
    openrouter_service = None
