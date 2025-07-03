from django.db.models import Count, Q
from .models import Message

def unread_messages(request):
    """Add unread message count to context"""
    if request.user.is_authenticated:
        unread_count = Message.objects.filter(
            conversation__participants=request.user,
            is_read=False
        ).exclude(sender=request.user).count()
        
        return {'unread_message_count': unread_count}
    return {'unread_message_count': 0}