from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from authuser.models import User
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseNotAllowed, JsonResponse
from django.views.decorators.http import require_POST
from etudiants.models import Announcement
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from authuser.forms import ProfileUpdateForm, CustomPasswordResetForm, CustomSetPasswordForm
from django.contrib import messages
from django.urls import reverse_lazy
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.core.exceptions import ValidationError
import logging

from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib import messages

logger = logging.getLogger(__name__)

# Create your views here.

def homepage(request):
    show_popup = request.session.pop('show_registration_success', False)
    
    if show_popup:
        request.session.modified = True
    
    return render(request, 'welcompage/welcompage.html', {
        'show_popup': show_popup
    })

def user_dashboard(request):
    return render(request, 'dashboard/userdashboard.html')

def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            if user.status == 'approved' and user.is_active:
                auth_login(request, user)
                # Ajouter le message de succès avec un délai pour l'affichage après redirection
                if user.is_staff:
                    messages.success(request, f'Bienvenue admin {user.name or user.email}! Connexion réussie.')
                    return redirect('pages:admin_dashboard')
                else:
                    messages.success(request, f'Bienvenue {user.name or user.email}! Connexion réussie.')
                    return redirect('pages:offers')
            elif user.status == 'pending':
                messages.info(request, 'Votre compte est en attente d\'approbation par l\'administrateur.')
            elif user.status == 'rejected':
                messages.error(request, 'Votre compte a été rejeté. Contactez l\'administrateur pour plus d\'informations.')
            else:
                messages.warning(request, 'Votre compte n\'est pas actif. Veuillez contacter l\'administrateur.')
        else:
            messages.error(request, 'Email ou mot de passe incorrect. Veuillez réessayer.')
    
    return render(request, 'loginandsignup/login.html')

def register(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        name = request.POST.get('name')
        surname = request.POST.get('surname')
        
        if not all([email, password, name, surname]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'loginandsignup/register.html')

        try:
            user = User.objects.create_user(
                email=email, 
                password=password, 
                name=name, 
                surname=surname,
                status='pending',
                is_active=True
            )
            # Add flag to show popup on homepage
            request.session['show_registration_success'] = True
            messages.success(request, f'Votre compte a été créé avec succès ! Un administrateur examinera votre demande et vous contactera bientôt.')
            return redirect('pages:homepage')
        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')
            return render(request, 'loginandsignup/register.html')
    
    return render(request, 'loginandsignup/register.html')

def logout_view(request):
    """Vue de déconnexion qui nettoie les messages de la session"""
    # Ajouter le message AVANT la déconnexion et la redirection
    messages.info(request, 'Vous avez été déconnecté avec succès.')
    
    logout(request)
    
    # Optionnel : nettoyer les anciens messages si nécessaire
    # storage = messages.get_messages(request)
    # storage.used = True
    
    return redirect('pages:homepage')

# ============================================
# PASSWORD RESET VIEWS
# ============================================

class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
    template_name = 'loginandsignup/password_reset.html'
    email_template_name = 'loginandsignup/password_reset_email.html'
    subject_template_name = 'loginandsignup/password_reset_subject.txt'
    success_url = reverse_lazy('pages:password_reset_done')
    
    def form_valid(self, form):
        try:
            # Check if user exists first
            email = form.cleaned_data['email']
            if not User.objects.filter(email=email).exists():
                messages.error(
                    self.request,
                    'Aucun compte n\'est associé à cette adresse email.'
                )
                return self.form_invalid(form)
            
            # Check email backend configuration properly
            email_backend = getattr(settings, 'EMAIL_BACKEND', '')
            
            # Send the email using parent class method
            response = super().form_valid(form)
            
            # Show appropriate success message based on email backend
            if 'console' in email_backend.lower():
                messages.success(
                    self.request, 
                    'Un email de réinitialisation a été envoyé à votre adresse. '
                    'En mode développement, vérifiez la console du serveur pour voir l\'email.'
                )
                logger.info(f"Password reset email sent to {email} (console backend)")
            else:
                messages.success(
                    self.request, 
                    'Un email de réinitialisation a été envoyé à votre adresse. '
                    'Vérifiez votre boîte de réception et suivez les instructions.'
                )
                logger.info(f"Password reset email sent to {email} (SMTP backend)")
            
            return response
                
        except Exception as e:
            logger.error(f"Error sending password reset email: {e}")
            
            # More specific error messages
            error_str = str(e).lower()
            if 'authentication' in error_str or 'username' in error_str:
                error_msg = 'Erreur d\'authentification email. Vérifiez les identifiants Gmail.'
            elif 'connection' in error_str or 'network' in error_str:
                error_msg = 'Erreur de connexion. Vérifiez votre connexion internet.'
            elif 'smtp' in error_str:
                error_msg = 'Erreur SMTP. Vérifiez la configuration Gmail.'
            else:
                error_msg = 'Erreur technique lors de l\'envoi de l\'email.'
            
            messages.error(
                self.request,
                f'{error_msg} Contactez l\'administrateur si le problème persiste.'
            )
            return self.form_invalid(form)

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = CustomSetPasswordForm
    template_name = 'loginandsignup/password_reset_confirm.html'
    success_url = reverse_lazy('pages:password_reset_complete')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            'Votre mot de passe a été modifié avec succès ! Vous pouvez maintenant vous connecter.'
        )
        return response

def password_reset_done_view(request):
    return render(request, 'loginandsignup/password_reset_done.html')

def password_reset_complete_view(request):
    return render(request, 'loginandsignup/password_reset_complete.html')

# ============================================
# EXISTING VIEWS (UNCHANGED)
# ============================================

def offers_view(request):
    announcements = Announcement.objects.all().order_by('-created_at')
    
    if request.user.is_authenticated:
        announcements = announcements.exclude(user=request.user)
    
    city = request.GET.get('city')
    if city:
        announcements = announcements.filter(city__icontains=city)
    
    room_type = request.GET.get('room_type')
    if room_type:
        announcements = announcements.filter(room_type=room_type)
 
    gender = request.GET.get('gender')
    if gender:
        announcements = announcements.filter(gender_preference=gender)
    
    all_cities = Announcement.objects.values_list('city', flat=True).distinct()
    
    context = {
        'announcements': announcements,
        'all_cities': all_cities,
        'room_types': Announcement.ROOM_TYPES,
        'selected_city': room_type,
        'selected_room_type': room_type,
        'selected_gender': gender,
    }
    return render(request, 'navbaroffers/offers.html', context)

def howworks(request):
    return  render(request, 'navbaroffers/howworks.html')

def test(request):
    return  render(request, 'navbaroffers/testimonials.html')

@login_required
@user_passes_test(lambda u: u.is_staff) 
def settings(request):
    pending_users = User.objects.filter(status='pending')
    approved_users = User.objects.filter(status='approved')
    rejected_users = User.objects.filter(status='rejected')
    
    context = {
        'pending_users': pending_users,
        'approved_users': approved_users,
        'rejected_users': rejected_users,
    }
    return render(request, 'dashboard/settings.html', context)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_staff)
def approve_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        user.status = 'approved'
        user.is_active = True
        user.save()
        messages.success(request, f'User {user.email} has been approved.')
        return redirect('pages:settings')
    return HttpResponseNotAllowed(['POST'])

@require_POST
@login_required
@user_passes_test(lambda u: u.is_staff)
def reject_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        user.status = 'rejected'
        user.is_active = False
        user.save()
        messages.success(request, f'User {user.email} has been rejected.')
        return redirect('settings')
    return HttpResponseNotAllowed(['POST'])

def clear_registration_flag(request):
    if 'show_registration_success' in request.session:
        del request.session['show_registration_success']
    return JsonResponse({'status': 'ok'})

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Case, When, IntegerField
from django.contrib.auth import get_user_model

User = get_user_model()

@login_required
def dashboard(request):
    if not request.user.is_staff and not request.user.is_superuser:
        return redirect('home')  

    # Calculate profile status counts with proper handling
    # Users with active announcements are "posting", others are "looking"
    users_with_active_announcements = User.objects.filter(
        announcements__is_active=True
    ).distinct().values_list('id', flat=True)
    
    # Count users who are actually posting (have active announcements)
    posting_count = len(users_with_active_announcements)
    
    # Count all other users as looking (excluding staff/superusers if needed)
    total_users = User.objects.filter(
        is_active=True,
        is_staff=False,  # Exclude staff from counts if desired
        is_superuser=False  # Exclude superusers from counts if desired
    ).count()
    
    looking_count = total_users - posting_count
    
    # Alternative approach using database aggregation (more efficient for large datasets)
    # Uncomment this section if you prefer database-level calculation:
    """
    profile_status_counts = User.objects.filter(
        is_active=True,
        is_staff=False,
        is_superuser=False
    ).aggregate(
        posting_count=Count(
            Case(
                When(announcements__is_active=True, then=1),
                output_field=IntegerField(),
                distinct=True
            )
        ),
        total_count=Count('id')
    )
    
    posting_count = profile_status_counts['posting_count']
    looking_count = profile_status_counts['total_count'] - posting_count
    """
    
    # Calculate approval status counts (handle potential None values)
    status_counts = User.objects.filter(
        is_active=True,
        is_staff=False,
        is_superuser=False
    ).aggregate(
        approved_count=Count(Case(When(status='approved', then=1), output_field=IntegerField())),
        pending_count=Count(Case(When(Q(status='pending') | Q(status__isnull=True), then=1), output_field=IntegerField())),
        rejected_count=Count(Case(When(status='rejected', then=1), output_field=IntegerField()))
    )
    
    # Extract counts from the aggregation
    approved_count = status_counts['approved_count']
    pending_count = status_counts['pending_count'] 
    rejected_count = status_counts['rejected_count']
    
    # Additional stats that might be useful
    total_announcements = Announcement.objects.count()
    active_announcements = Announcement.objects.filter(is_active=True).count()
    inactive_announcements = total_announcements - active_announcements
    
    context = {
        'looking_count': looking_count,
        'posting_count': posting_count,
        'approved_count': approved_count,
        'pending_count': pending_count,
        'rejected_count': rejected_count,
        # Additional context for more detailed dashboard
        'total_users': total_users,
        'total_announcements': total_announcements,
        'active_announcements': active_announcements,
        'inactive_announcements': inactive_announcements,
    }
    
    return render(request, 'dashboard/admindashboard.html', context)
@login_required
@csrf_protect
@require_POST
def update_user_status(request):
    if not request.user.is_staff and not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        status = data.get('status')
        
        looking_count = User.objects.filter(profile_status='looking').count()
        posting_count = User.objects.filter(profile_status='posting').count()
        
        return JsonResponse({
            'profile_data': {
                'looking': looking_count,
                'posting': posting_count
            }
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@csrf_protect
@require_POST
def update_approval_status(request):
    if not request.user.is_staff and not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        new_status = data.get('new_status')
        old_status = data.get('old_status')
        
        approved_count = User.objects.filter(status='approved').count()
        pending_count = User.objects.filter(status='pending').count()
        rejected_count = User.objects.filter(status='rejected').count()
        
        return JsonResponse({
            'approval_data': {
                'approved': approved_count,
                'pending': pending_count,
                'rejected': rejected_count
            }
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    
@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('pages:homepage')
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    context = {
        'form': form,
        'user': request.user,
    }
    return render(request, 'dashboard/profile.html', context)