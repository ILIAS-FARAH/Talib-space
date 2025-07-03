from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.utils import timezone
import os


def user_profile_pic_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"profile_pic.{ext}"
    return os.path.join('users', str(instance.id), filename)


class CustomUserManager(UserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('You have not provided a valid email')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('status', 'approved') 
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    PROFILE_STATUS_CHOICES = [
        ('looking', 'Looking for offers'),
        ('posting', 'Has posted announcement'),
    ]
    
    email = models.EmailField(blank=True, default='', unique=True)
    name = models.CharField(max_length=255, blank=True, default='')
    surname = models.CharField(max_length=255, blank=True, default='')
    
    # Status fields
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    profile_status = models.CharField(max_length=10, choices=PROFILE_STATUS_CHOICES, default='looking')
    is_active = models.BooleanField(default=True)  
    
    # Admin fields
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)

    profile_picture = models.ImageField(upload_to=user_profile_pic_path, blank=True, null=True)
    description = models.TextField(blank=True, default='')

    objects = CustomUserManager()
        
    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'surname']
    
    def __str__(self):
        return self.email
    
    def has_posted_announcement(self):
        """Set user as having posted an announcement"""
        self.profile_status = 'posting'
        self.save(update_fields=['profile_status'])
    
    def remove_announcement(self):
        """Reset user to looking for offers when announcement is deleted"""
        self.profile_status = 'looking'
        self.save(update_fields=['profile_status'])
    
    def update_profile_status(self):
        """
        Update profile status based on current announcements
        """
        has_active_announcements = self.announcements.filter(is_active=True).exists()
        
        if has_active_announcements and self.profile_status != 'posting':
            self.profile_status = 'posting'
            self.save(update_fields=['profile_status'])
        elif not has_active_announcements and self.profile_status != 'looking':
            self.profile_status = 'looking'
            self.save(update_fields=['profile_status'])
    
    def is_profile_complete(self):
        """Check if user has completed their profile (profile picture AND description)"""
        return bool(self.profile_picture and self.description.strip())
    
    def get_missing_profile_items(self):
        """Get list of missing profile items"""
        missing = []
        if not self.profile_picture:
            missing.append('Profile Picture')
        if not self.description.strip():
            missing.append('Description')
        return missing


class ContactMessage(models.Model):
    SUBJECT_CHOICES = [
        ('question', 'Question générale'),
        ('technical', 'Problème technique'),
        ('partnership', 'Partenariat'),
        ('other', 'Autre'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('in_progress', 'En cours'),
        ('resolved', 'Résolu'),
        ('closed', 'Fermé'),
    ]
    
    # Contact information
    name = models.CharField(max_length=255, verbose_name="Nom complet")
    email = models.EmailField(verbose_name="Email")
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES, verbose_name="Sujet")
    message = models.TextField(verbose_name="Message")
    
    # System fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Statut")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")
    
    # Admin response
    admin_response = models.TextField(blank=True, null=True, verbose_name="Réponse admin")
    responded_at = models.DateTimeField(blank=True, null=True, verbose_name="Date de réponse")
    responded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='contact_responses', verbose_name="Répondu par")
    
    # Priority and notes
    priority = models.CharField(max_length=10, choices=[
        ('low', 'Basse'),
        ('medium', 'Moyenne'),
        ('high', 'Haute'),
        ('urgent', 'Urgente')
    ], default='medium', verbose_name="Priorité")
    
    admin_notes = models.TextField(blank=True, null=True, verbose_name="Notes internes")
    
    class Meta:
        verbose_name = "Message de contact"
        verbose_name_plural = "Messages de contact"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.get_subject_display()} ({self.created_at.strftime('%d/%m/%Y %H:%M')})"
    
    def mark_as_resolved(self, admin_user=None, response=None):
        """Mark the message as resolved"""
        self.status = 'resolved'
        if response:
            self.admin_response = response
            self.responded_at = timezone.now()
            self.responded_by = admin_user
        self.save()
    
    def is_recent(self):
        """Check if message was created in the last 24 hours"""
        return (timezone.now() - self.created_at).days < 1
    
    def get_priority_color(self):
        """Return CSS class for priority color"""
        colors = {
            'low': 'text-green-600 bg-green-100',
            'medium': 'text-yellow-600 bg-yellow-100',
            'high': 'text-orange-600 bg-orange-100',
            'urgent': 'text-red-600 bg-red-100'
        }
        return colors.get(self.priority, 'text-gray-600 bg-gray-100')
    
    def get_status_color(self):
        """Return CSS class for status color"""
        colors = {
            'pending': 'text-yellow-600 bg-yellow-100',
            'in_progress': 'text-blue-600 bg-blue-100',
            'resolved': 'text-green-600 bg-green-100',
            'closed': 'text-gray-600 bg-gray-100'
        }
        return colors.get(self.status, 'text-gray-600 bg-gray-100')