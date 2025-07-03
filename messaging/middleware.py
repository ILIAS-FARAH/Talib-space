from django.db.models import Count, Q
from .models import Message

class UnreadMessagesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Count unread messages for the user
            unread_count = Message.objects.filter(
                conversation__participants=request.user,
                is_read=False
            ).exclude(sender=request.user).count()
            
            # Add to request context
            request.unread_message_count = unread_count
        
        response = self.get_response(request)
        return response