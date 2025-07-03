from django.db import models
from django.utils import timezone

class ContactMessage(models.Model):
    SUBJECT_CHOICES = [
        ('question', 'Question générale'),
        ('technical', 'Problème technique'),
        ('partnership', 'Partenariat'),
        ('other', 'Autre'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Nom complet")
    email = models.EmailField(verbose_name="Email")
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES, verbose_name="Sujet")
    message = models.TextField(verbose_name="Message")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Date de création")
    is_read = models.BooleanField(default=False, verbose_name="Lu")
    
    class Meta:
        verbose_name = "Message de contact"
        verbose_name_plural = "Messages de contact"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.get_subject_display()}"
    
    def get_subject_display_full(self):
        return dict(self.SUBJECT_CHOICES)[self.subject]