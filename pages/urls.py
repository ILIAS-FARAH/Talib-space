from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
app_name = 'pages'  
urlpatterns = [
    # Homepage and main pages
    path('', views.homepage, name='homepage'),
    path('offers/', views.offers_view, name='offers'),
    path('how-works/', views.howworks, name='howworks'),
    path('testimonials/', views.test, name='testo'),
    
    # Authentication URLs
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password Reset URLs
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.password_reset_done_view, name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset-complete/', views.password_reset_complete_view, name='password_reset_complete'),
    
    # Dashboard and admin
    path('dashboard/', views.dashboard, name='admin_dashboard'),
    path('user-dashboard/', views.user_dashboard, name='user_dashboard'),
    path('settings/', views.settings, name='settings'),
    path('profile/', views.profile, name='profile'),
    
    # User management
    path('approve-user/<int:user_id>/', views.approve_user, name='approve_user'),
    path('reject-user/<int:user_id>/', views.reject_user, name='reject_user'),
    path('update-user-status/', views.update_user_status, name='update_user_status'),
    path('update-approval-status/', views.update_approval_status, name='update_approval_status'),
    
    # Utility
    path('clear-registration-flag/', views.clear_registration_flag, name='clear_registration_flag'),
    
    
]