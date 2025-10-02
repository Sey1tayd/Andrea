"""
URL configuration for andrea_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.conf.urls.static import static
from users.views import home_view, login_view, logout_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', lambda _request: HttpResponse("ok")),
    path('healthz/', lambda _request: HttpResponse("ok")),
    path('whoami/', login_required(lambda r: HttpResponse(f"hi {r.user.username}"))),
    path('', home_view, name='home'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('users/', include('users.urls')),
    path('chat/', include('chat.urls', namespace='chat')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
