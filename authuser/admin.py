from django.contrib import admin
from .models import User, ContactMessage


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'surname', 'status', 'profile_status', 'is_staff', 'date_joined')
    list_filter = ('status', 'profile_status', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('email', 'name', 'surname')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('Personal info', {
            'fields': ('name', 'surname', 'profile_picture', 'description')
        }),
        ('Status', {
            'fields': ('status', 'profile_status', 'is_active')
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login')


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'status', 'priority', 'created_at', 'is_recent')
    list_filter = ('status', 'priority', 'subject', 'created_at')
    search_fields = ('name', 'email', 'message')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'responded_at')
    
    fieldsets = (
        ('Message Information', {
            'fields': ('name', 'email', 'subject', 'message')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority')
        }),
        ('Admin Response', {
            'fields': ('admin_response', 'responded_by', 'responded_at', 'admin_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        # Automatically set responded_by when admin_response is provided
        if obj.admin_response and not obj.responded_by:
            obj.responded_by = request.user
            if not obj.responded_at:
                from django.utils import timezone
                obj.responded_at = timezone.now()
        super().save_model(request, obj, form, change)
    
    def is_recent(self, obj):
        return obj.is_recent()
    is_recent.boolean = True
    is_recent.short_description = 'Recent (24h)'
    
    actions = ['mark_as_resolved', 'mark_as_in_progress', 'mark_as_pending']
    
    def mark_as_resolved(self, request, queryset):
        queryset.update(status='resolved')
        self.message_user(request, f'{queryset.count()} messages marked as resolved.')
    mark_as_resolved.short_description = 'Mark selected messages as resolved'
    
    def mark_as_in_progress(self, request, queryset):
        queryset.update(status='in_progress')
        self.message_user(request, f'{queryset.count()} messages marked as in progress.')
    mark_as_in_progress.short_description = 'Mark selected messages as in progress'
    
    def mark_as_pending(self, request, queryset):
        queryset.update(status='pending')
        self.message_user(request, f'{queryset.count()} messages marked as pending.')
    mark_as_pending.short_description = 'Mark selected messages as pending'