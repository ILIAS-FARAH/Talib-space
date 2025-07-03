from django.contrib.auth.decorators import login_required
from .forms import ProfileUpdateForm
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import ContactMessage
from .forms import ContactForm, AdminResponseForm
from django.shortcuts import render, redirect





@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    context = {
        'form': form,
        'user': request.user,
    }
    return render(request, 'profile.html', context)



@staff_member_required
def reports_dashboard(request):
    """Admin dashboard for viewing all contact messages"""
   
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    subject_filter = request.GET.get('subject', '')
    search_query = request.GET.get('search', '')
    
  
    messages_list = ContactMessage.objects.all()
    
    
    if status_filter:
        messages_list = messages_list.filter(status=status_filter)
    
    if priority_filter:
        messages_list = messages_list.filter(priority=priority_filter)
    
    if subject_filter:
        messages_list = messages_list.filter(subject=subject_filter)
    
    if search_query:
        messages_list = messages_list.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(message__icontains=search_query)
        )
    
    
    messages_list = messages_list.order_by('-created_at')
    
    
    paginator = Paginator(messages_list, 10)  
    page_number = request.GET.get('page')
    messages_page = paginator.get_page(page_number)
    
   
    stats = {
        'total': ContactMessage.objects.count(),
        'pending': ContactMessage.objects.filter(status='pending').count(),
        'in_progress': ContactMessage.objects.filter(status='in_progress').count(),
        'resolved': ContactMessage.objects.filter(status='resolved').count(),
        'recent': ContactMessage.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).count(),
    }
    
   
    filter_choices = {
        'status_choices': ContactMessage.STATUS_CHOICES,
        'priority_choices': ContactMessage._meta.get_field('priority').choices,
        'subject_choices': ContactMessage.SUBJECT_CHOICES,
    }
    
    context = {
        'messages': messages_page,
        'stats': stats,
        'filter_choices': filter_choices,
        'current_filters': {
            'status': status_filter,
            'priority': priority_filter,
            'subject': subject_filter,
            'search': search_query,
        },
        'page_title': 'Reports Dashboard'
    }
    
    return render(request, 'welcompage/reports_dashboard.html', context)


@staff_member_required
def message_detail(request, message_id):
    """View and respond to a specific contact message"""
    message = get_object_or_404(ContactMessage, id=message_id)
    
    if request.method == 'POST':
        form = AdminResponseForm(request.POST, instance=message)
        if form.is_valid():
            updated_message = form.save(commit=False)
            
           
            if updated_message.admin_response and not message.responded_at:
                updated_message.responded_at = timezone.now()
                updated_message.responded_by = request.user
            
            updated_message.save()

            if updated_message.admin_response and 'admin_response' in form.changed_data:
                try:
                    send_mail(
                        subject=f'Réponse à votre message - {message.get_subject_display()}',
                        message=f'''
                        Bonjour {message.name},
                        
                        Nous avons bien reçu votre message concernant "{message.get_subject_display()}" et voici notre réponse:
                        
                        {updated_message.admin_response}
                        
                        Cordialement,
                        L'équipe Talib Space
                        
                        ---
                        Votre message original:
                        {message.message}
                        ''',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[message.email],
                        fail_silently=True
                    )
                    messages.success(request, 'Réponse envoyée avec succès!')
                except Exception as e:
                    messages.warning(request, f'Message mis à jour mais l\'email n\'a pas pu être envoyé: {e}')
            else:
                messages.success(request, 'Message mis à jour avec succès!')
            
            return redirect('message_detail', message_id=message.id)
    else:
        form = AdminResponseForm(instance=message)
    
    context = {
        'message': message,
        'form': form,
        'page_title': f'Message #{message.id}'
    }
    
    return render(request, 'welcompage/message_detail.html', context)


@staff_member_required
def update_message_status(request, message_id):
    """AJAX endpoint to quickly update message status"""
    if request.method == 'POST':
        message = get_object_or_404(ContactMessage, id=message_id)
        new_status = request.POST.get('status')
        
        if new_status in dict(ContactMessage.STATUS_CHOICES):
            message.status = new_status
            message.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Statut mis à jour avec succès'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Erreur lors de la mise à jour'
    })

