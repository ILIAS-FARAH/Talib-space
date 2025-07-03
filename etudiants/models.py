from django.db import models
from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
import logging


class Announcement(models.Model):
    ROOM_TYPES = [
        ('single_room', 'Single Room'),
        ('shared_room', 'Shared Room'),
        ('apartment', 'Entire Apartment'),
    ]
    
    GENDER_PREFERENCES = [
        ('any', 'Any'),
        ('male', 'Male Only'),
        ('female', 'Female Only'),
    ]
    
    AMENITIES_CHOICES = [
        ('wifi', 'WiFi'),
        ('kitchen', 'Kitchen'),
        ('laundry', 'Laundry'),
        ('heating', 'Heating'),
        ('parking', 'Parking'),
        ('furnished', 'Furnished'),
        ('ac', 'Air Conditioning'),
        ('tv', 'Television'),
        ('workspace', 'Workspace'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='announcements')
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    city = models.CharField(max_length=100)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='shared_room')
    gender_preference = models.CharField(max_length=10, choices=GENDER_PREFERENCES, default='any')
    amenities = models.CharField(max_length=255, blank=True, help_text="Comma-separated list of amenities")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='accepted_announcements'
    )
    
    # Add favorites relationship
    favorited_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='Favorite',
        related_name='favorite_announcements',
        blank=True
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Announcement'
        verbose_name_plural = 'Announcements'
        
    def __str__(self):
        return f"{self.title} - {self.city}"
    
    def get_amenities_list(self):
        """Return amenities as a cleaned list"""
        if self.amenities:
            return [amenity.strip() for amenity in self.amenities.split(',') if amenity.strip()]
        return []
    
    def set_amenities(self, amenities_list):
        """Set amenities from a list"""
        self.amenities = ','.join([str(amenity).strip() for amenity in amenities_list if str(amenity).strip()])
    
    def get_display_image(self):
        """Get the first image or default image"""
        if self.images.exists():
            return self.images.first().image
        return None

    def is_favorited_by(self, user):
        """Check if this announcement is favorited by a specific user"""
        if user.is_authenticated:
            return self.favorited_by.filter(id=user.id).exists()
        return False

    def get_favorites_count(self):
        """Get the total number of users who favorited this announcement"""
        return self.favorited_by.count()

    def accept_announcement(self, accepted_by_user):
        """Mark announcement as accepted"""
        self.is_accepted = True
        self.accepted_at = timezone.now()
        self.accepted_by_user = accepted_by_user
        self.is_active = False  # Désactiver l'annonce
        self.save()

    @property
    def is_expired(self):
        """Check if announcement is expired (accepted)"""
        return self.is_accepted


class Favorite(models.Model):
    """Intermediate model for favorites with timestamp"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'announcement')
        verbose_name = 'Favorite'
        verbose_name_plural = 'Favorites'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.name} favorited {self.announcement.title}"


class AnnouncementImage(models.Model):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='announcements/images/')
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Announcement Image'
        verbose_name_plural = 'Announcement Images'
        
    def __str__(self):
        return f"Image for {self.announcement.title} (Order: {self.order})"


class QuizAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts')
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='quiz_attempts')
    answers = models.JSONField(help_text="Stores the user's quiz answers and metadata")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'announcement')
        ordering = ['-created_at']
        verbose_name = 'Quiz Attempt'
        verbose_name_plural = 'Quiz Attempts'
        
    def __str__(self):
        return f"Quiz attempt by {self.user.name} for {self.announcement.title}"
    
    def get_quiz_type(self):
        """Get the quiz type from stored answers"""
        if self.answers and isinstance(self.answers, dict):
            return self.answers.get('quiz_type', self.announcement.room_type)
        return self.announcement.room_type
    
    def get_total_questions(self):
        """Get total number of questions answered"""
        if self.answers and isinstance(self.answers, dict):
            return len(self.answers.get('answers', []))
        return 0
    
    def get_completion_rate(self):
        """Get completion rate as percentage"""
        total_questions = self.get_total_questions()
        if total_questions > 0:
            return 100  # Assuming all questions were answered if quiz was submitted
        return 0


# Signal handlers for automatic user status updates
logger = logging.getLogger(__name__)

@receiver(post_save, sender=Announcement)
def update_user_status_on_announcement_change(sender, instance, created, **kwargs):
    """
    Handle both creation and status changes of announcements
    """
    try:
        user = instance.user
        
        if created and instance.is_active:
            # New active announcement created
            user.has_posted_announcement()
            logger.info(f"Set profile_status to 'posting' for user {user.id} - new announcement created")
        else:
            # Announcement was updated, check current status
            has_active_announcements = Announcement.objects.filter(user=user, is_active=True).exists()
            
            if has_active_announcements and user.profile_status != 'posting':
                user.has_posted_announcement()
                logger.info(f"Set profile_status to 'posting' for user {user.id} - has active announcements")
            elif not has_active_announcements and user.profile_status != 'looking':
                user.remove_announcement()
                logger.info(f"Set profile_status to 'looking' for user {user.id} - no active announcements")
                
    except Exception as e:
        logger.error(f"Error updating user status on announcement change: {str(e)}")


@receiver(post_delete, sender=Announcement)
def update_user_status_on_delete(sender, instance, **kwargs):
    """
    Update user's profile status when an announcement is deleted
    """
    try:
        user = instance.user
        
        # Check if user has any other active announcements
        remaining_announcements = Announcement.objects.filter(user=user, is_active=True).count()
        
        if remaining_announcements == 0:
            # No more active announcements, set status to looking
            user.remove_announcement()
            logger.info(f"Set profile_status to 'looking' for user {user.id} - deleted last announcement")
        else:
            logger.info(f"User {user.id} still has {remaining_announcements} active announcements, keeping 'posting' status")
            
    except Exception as e:
        logger.error(f"Error updating user status on announcement deletion: {str(e)}")