from django.db import models
from django.conf import settings
from django.utils import timezone

class Conversation(models.Model):
    """Model representing a conversation between two users"""
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Link to the announcement this conversation is about (optional)
    announcement = models.ForeignKey('etudiants.Announcement', on_delete=models.SET_NULL, 
                                     null=True, blank=True, related_name='conversations')
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Conversation {self.id} between {', '.join([str(p) for p in self.participants.all()])}"
    
  
    def get_other_participant(self, user):
        """Returns the other participant in the conversation"""
        return self.participants.exclude(id=user.id).first()

    def last_message(self):
        """Get the last message in this conversation"""
        return self.messages.order_by('-timestamp').first()
    
    def unread_count(self, user):
        """Count unread messages for a specific user"""
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class Message(models.Model):
    """Model representing a message within a conversation"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"Message from {self.sender} at {self.timestamp}"
    
    def mark_as_read(self):
        """Mark this message as read"""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])