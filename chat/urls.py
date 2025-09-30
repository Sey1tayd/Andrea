from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('start/', views.start_chat, name='start'),
    path('<int:chat_id>/', views.chat_detail, name='detail'),
    path('<int:chat_id>/send/', views.send_message, name='send'),
    path('<int:chat_id>/check/', views.check_initial_response, name='check'),
    path('<int:chat_id>/delete/', views.delete_chat, name='delete'),
]
