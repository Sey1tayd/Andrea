from django.contrib import admin
from .models import Chat, Message

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('role','content','created_at')

@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('id','title','user','created_at','updated_at')
    list_filter = ('user',)
    search_fields = ('title', 'user__username')
    inlines = [MessageInline]