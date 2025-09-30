from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from chat.models import Chat

@never_cache
def home_view(request):
    """Ana sayfa görünümü"""
    if request.user.is_authenticated:
        chats = Chat.objects.filter(user=request.user).only('id','title','updated_at')[:50]
        return render(request, 'home.html', {'chats': chats})
    else:
        return redirect('login')

@csrf_protect
def login_view(request):
    """Giriş yapma görünümü"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                if not remember_me:
                    # Oturum süresini kısalt (tarayıcı kapatıldığında oturum sona erer)
                    request.session.set_expiry(0)
                messages.success(request, f'Hoş geldiniz, {user.username}!')
                return redirect('home')
            else:
                messages.error(request, 'Kullanıcı adı veya şifre hatalı.')
        else:
            messages.error(request, 'Lütfen tüm alanları doldurun.')
    
    return render(request, 'login.html')

@login_required
def logout_view(request):
    """Çıkış yapma görünümü"""
    logout(request)
    messages.success(request, 'Başarıyla çıkış yaptınız.')
    return redirect('home')
