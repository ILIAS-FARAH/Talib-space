from django.contrib import admin
from .models import Announcement, QuizAttempt, AnnouncementImage, Favorite

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'city', 'room_type', 'price', 'created_at', 'is_active', 'get_favorites_count']
    list_filter = ['room_type', 'gender_preference', 'city', 'is_active', 'created_at']
    search_fields = ['title', 'description', 'city', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at', 'get_favorites_count']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'title', 'description', 'price', 'city')
        }),
        ('Preferences', {
            'fields': ('room_type', 'gender_preference', 'amenities')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Statistics', {
            'fields': ('get_favorites_count',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_favorites_count(self, obj):
        return obj.get_favorites_count()
    get_favorites_count.short_description = 'Favorites Count'


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'announcement', 'created_at']
    list_filter = ['created_at', 'announcement__room_type', 'announcement__city']
    search_fields = ['user__email', 'user__name', 'announcement__title']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Favorite Information', {
            'fields': ('user', 'announcement', 'created_at')
        }),
    )


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'announcement', 'get_quiz_type', 'get_total_questions', 'created_at']
    list_filter = ['created_at', 'announcement__room_type']
    search_fields = ['user__email', 'user__name', 'announcement__title']
    readonly_fields = ['created_at', 'updated_at', 'get_quiz_type', 'get_total_questions']
    
    fieldsets = (
        ('Attempt Information', {
            'fields': ('user', 'announcement')
        }),
        ('Quiz Data', {
            'fields': ('answers', 'get_quiz_type', 'get_total_questions'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_quiz_type(self, obj):
        return obj.get_quiz_type()
    get_quiz_type.short_description = 'Quiz Type'
    
    def get_total_questions(self, obj):
        return obj.get_total_questions()
    get_total_questions.short_description = 'Total Questions'


@admin.register(AnnouncementImage)
class AnnouncementImageAdmin(admin.ModelAdmin):
    list_display = ['announcement', 'caption', 'order', 'created_at']
    list_filter = ['created_at', 'announcement__room_type']
    search_fields = ['announcement__title', 'caption']
    ordering = ['announcement', 'order']