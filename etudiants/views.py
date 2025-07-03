from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .models import Announcement, Favorite, AnnouncementImage, QuizAttempt
from .forms import AnnouncementForm, AnnouncementUpdateForm
import json
from django.urls import reverse
from urllib.parse import urlencode
import logging

logger = logging.getLogger(__name__)

class AnnouncementListView(ListView):
    model = Announcement
    template_name = 'etudiants/offers.html'
    context_object_name = 'announcements'
    paginate_by = 12

    def get_queryset(self):
        queryset = Announcement.objects.all().prefetch_related('images')
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(city__icontains=search_query)
            )
        
        # Filter by room type
        room_type = self.request.GET.get('room_type')
        if room_type:
            queryset = queryset.filter(room_type=room_type)
        
        # Filter by city
        city = self.request.GET.get('city')
        if city:
            queryset = queryset.filter(city__icontains=city)
        
        # Price range filter
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['room_types'] = Announcement.ROOM_TYPES
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_room_type'] = self.request.GET.get('room_type', '')
        context['selected_city'] = self.request.GET.get('city', '')
        context['min_price'] = self.request.GET.get('min_price', '')
        context['max_price'] = self.request.GET.get('max_price', '')
        
        if self.request.user.is_authenticated:
            user_favorites = list(
                Favorite.objects.filter(user=self.request.user)
                .values_list('announcement_id', flat=True)
            )
            context['user_favorites'] = user_favorites
        else:
            context['user_favorites'] = []
        
        return context

def offer_detail(request, pk):
    """Display detailed view of an announcement"""
    announcement = get_object_or_404(Announcement, pk=pk)
    
    context = {
        'announcement': announcement,
    }
    
    if request.user.is_authenticated:
        user_favorites = list(
            Favorite.objects.filter(user=request.user)
            .values_list('announcement_id', flat=True)
        )
        context['user_favorites'] = user_favorites
        
        # Check if user has completed the quiz for this announcement
        quiz_completed = QuizAttempt.objects.filter(
            user=request.user,
            announcement=announcement
        ).exists()
        context['quiz_completed'] = quiz_completed
    else:
        context['user_favorites'] = []
        context['quiz_completed'] = False
    
    return render(request, 'etudiants/offer_detail.html', context)

@login_required
def submit_quiz(request, announcement_id):
    """Handle quiz submission"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        announcement = get_object_or_404(Announcement, id=announcement_id, is_active=True)
        
        # Check if user has already completed this quiz
        existing_attempt = QuizAttempt.objects.filter(
            user=request.user,
            announcement=announcement
        ).first()
        
        if existing_attempt:
            return JsonResponse({
                'success': False, 
                'error': 'You have already completed this quiz.',
                'already_completed': True
            }, status=400)
        
        # Get JSON data from request
        data = json.loads(request.body)
        quiz_type = data.get('quiz_type', 'shared')
        answers = data.get('answers', [])
        questions = data.get('questions', [])
        
        if not answers or not questions:
            return JsonResponse({'success': False, 'error': 'Missing quiz data'}, status=400)
        
        # Prepare quiz data for storage
        quiz_data = {
            'quiz_type': quiz_type,
            'questions': questions,
            'answers': answers,
            'completed_at': timezone.now().isoformat(),
            'announcement_title': announcement.title,
            'announcement_city': announcement.city
        }
        
        # Create quiz attempt (no longer using update_or_create since we check above)
        quiz_attempt = QuizAttempt.objects.create(
            user=request.user,
            announcement=announcement,
            answers=quiz_data
        )
        
        # Create or find conversation
        from messaging.models import Conversation
        conversation = Conversation.objects.filter(
            participants=request.user
        ).filter(
            participants=announcement.user
        ).filter(
            announcement=announcement
        ).first()
        
        if not conversation:
            conversation = Conversation.objects.create(announcement=announcement)
            conversation.participants.add(request.user, announcement.user)
        
        return JsonResponse({
            'success': True,
            'message': 'Quiz submitted successfully!',
            'conversation_id': conversation.id,
            'redirect_url': f'/messaging/conversation/{conversation.id}/'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error submitting quiz: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'An error occurred'}, status=500)

class AnnouncementCreateView(LoginRequiredMixin, CreateView):
    model = Announcement
    form_class = AnnouncementForm
    template_name = 'etudiants/create_announcement.html'
    success_url = reverse_lazy('etudiants:my_announcements')

    def dispatch(self, request, *args, **kwargs):
        # Check if profile is complete before allowing access
        if not request.user.is_profile_complete():
            messages.error(request, 'Please complete your profile (add profile picture and description) before creating announcements.')
            return redirect('etudiants:my_announcements')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Announcement created successfully!')
        return super().form_valid(form)

class AnnouncementUpdateView(LoginRequiredMixin, UpdateView):
    model = Announcement
    form_class = AnnouncementUpdateForm
    template_name = 'etudiants/update_announcement.html'

    def get_queryset(self):
        return Announcement.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse_lazy('etudiants:offer_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Announcement updated successfully!')
        return super().form_valid(form)

class AnnouncementDeleteView(LoginRequiredMixin, DeleteView):
    model = Announcement
    template_name = 'etudiants/delete_announcement.html'
    success_url = reverse_lazy('etudiants:my_announcements')

    def get_queryset(self):
        return Announcement.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Announcement deleted successfully!')
        return super().delete(request, *args, **kwargs)

@login_required
def create_announcement_view(request):
    # Check if profile is complete
    if not request.user.is_profile_complete():
        messages.error(request, 'Please complete your profile (add profile picture and description) before creating announcements.')
        return redirect('etudiants:my_announcements')
    
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES, request=request)
        
        if form.is_valid():
            try:
                announcement = form.save(commit=False)
                announcement.user = request.user
                announcement.save()
                
                images = request.FILES.getlist('images')
                if images:
                    for i, image in enumerate(images):
                        AnnouncementImage.objects.create(
                            announcement=announcement,
                            image=image
                        )
                    
                try:
                    profile = request.user.profile_status
                    if hasattr(profile, 'has_posted_announcement'):
                        profile.has_posted_announcement = True
                        profile.save()
                except AttributeError:
                    pass
                 
                messages.success(request, f"Announcement '{announcement.title}' created successfully with {len(images)} images!")
                return redirect('etudiants:my_announcements')
                    
            except Exception as e:
                messages.error(request, f"Error creating announcement: {str(e)}")
                return render(request, 'etudiants/create_announcement.html', {
                    'form': form,
                    'page_title': 'Create New Announcement'
                })
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AnnouncementForm(request=request)

    return render(request, 'etudiants/create_announcement.html', {
        'form': form,
        'page_title': 'Create New Announcement'
    })

@login_required
def update_announcement_view(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = AnnouncementUpdateForm(request.POST, request.FILES, instance=announcement, request=request)
        if form.is_valid():
            try:
                updated_announcement = form.save()
                
                delete_images = request.POST.getlist('delete_images')
                if delete_images:
                    AnnouncementImage.objects.filter(
                        id__in=delete_images,
                        announcement=announcement
                    ).delete()
                
                new_images = request.FILES.getlist('images')
                for image in new_images:
                    AnnouncementImage.objects.create(
                        announcement=updated_announcement,
                        image=image
                    )
                
                messages.success(request, "Announcement updated successfully!")
                return redirect('etudiants:my_announcements')
            except Exception as e:
                messages.error(request, f"Error updating announcement: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AnnouncementUpdateForm(instance=announcement, request=request)

    images = announcement.images.all()

    return render(request, 'etudiants/update_announcement.html', {
        'form': form,
        'announcement': announcement,
        'images': images,
        'page_title': 'Update Announcement'
    })

@login_required
def my_announcements(request):
    """Display user's own announcements with profile completion check"""
    announcements = Announcement.objects.filter(user=request.user).order_by('-created_at')
    
    # Check if user's profile is complete
    profile_complete = request.user.is_profile_complete()
    missing_items = request.user.get_missing_profile_items()
    
    return render(request, 'etudiants/my_announcements.html', {
        'announcements': announcements,
        'profile_complete': profile_complete,
        'missing_items': missing_items,
    })

@login_required
def delete_announcement_view(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk, user=request.user)
    
    if request.method == 'POST':
        title = announcement.title
        announcement.delete()
        messages.success(request, f"Announcement '{title}' deleted successfully!")
        return redirect('etudiants:my_announcements')

    return render(request, 'etudiants/delete_announcement.html', {
        'announcement': announcement,
        'page_title': 'Delete Announcement'
    })

@login_required
def staff_delete_announcement_view(request, pk):
    """Staff-only view to delete any announcement"""
    if not request.user.is_staff:
        messages.error(request, "Vous n'avez pas les permissions nécessaires pour effectuer cette action.")
        return redirect('pages:offers')
    
    announcement = get_object_or_404(Announcement, pk=pk, is_active=True)
    
    if request.method == 'POST':
        title = announcement.title
        user_email = announcement.user.email
        announcement.delete()
        messages.success(request, f"L'annonce '{title}' de {user_email} a été supprimée avec succès!")
        return redirect('pages:offers')

    return render(request, 'etudiants/staff_delete_announcement.html', {
        'announcement': announcement,
        'page_title': 'Supprimer Annonce (Admin)'
    })



@login_required
@require_POST
def toggle_favorite(request, announcement_id):
    """Toggle favorite status for an announcement"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    try:
        announcement = get_object_or_404(Announcement, id=announcement_id)
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            announcement=announcement
        )
        
        if not created:
            favorite.delete()
            is_favorited = False
            message = 'Removed from favorites'
        else:
            is_favorited = True
            message = 'Added to favorites'
        
        return JsonResponse({
            'success': True,
            'is_favorited': is_favorited,
            'message': message,
            'favorites_count': announcement.get_favorites_count()
        })
        
    except Exception as e:
        logger.error(f"Error toggling favorite: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while updating favorites'
        }, status=500)

@login_required
@require_POST
def accept_announcement(request, pk):
    """Accept an announcement (mark as expired)"""
    try:
        announcement = get_object_or_404(Announcement, pk=pk)
        
        # Check if user is the owner of the announcement
        if announcement.user != request.user:
            return JsonResponse({
                'success': False,
                'message': 'You are not authorized to accept this announcement.'
            }, status=403)
        
        # Check if already accepted
        if announcement.is_accepted:
            return JsonResponse({
                'success': False,
                'message': 'This announcement has already been accepted.'
            }, status=400)
        
        # Accept the announcement
        announcement.accept_announcement(request.user)
        
        return JsonResponse({
            'success': True,
            'message': 'Announcement accepted successfully!',
            'is_accepted': True
        })
        
    except Exception as e:
        logger.error(f"Error accepting announcement: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=500)


@login_required
def my_favorites(request):
    # Filtrer les favoris pour exclure les annonces expirées (acceptées)
    favorites = Favorite.objects.filter(
        user=request.user,
        announcement__is_accepted=False  # Exclure les annonces acceptées/expirées
    ).select_related('announcement')
    
    selected_city = request.GET.get('city', '')
    selected_room_type = request.GET.get('room_type', '')

    if selected_city:
        favorites = favorites.filter(announcement__city__icontains=selected_city)
    if selected_room_type:
        favorites = favorites.filter(announcement__room_type=selected_room_type)

    # Obtenir les villes uniquement des annonces non expirées
    favorite_cities = favorites.values_list('announcement__city', flat=True).distinct()

    paginator = Paginator(favorites, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'favorites': page_obj,
        'favorite_cities': favorite_cities,
        'room_types': Announcement.ROOM_TYPES,
        'selected_city': selected_city,
        'selected_room_type': selected_room_type,
        'total_favorites': favorites.count(),
    }

    return render(request, 'etudiants/my_favorites.html', context)
@login_required
def delete_image_ajax(request, announcement_id, image_id):
    try:
        announcement = get_object_or_404(Announcement, pk=announcement_id, user=request.user)
        image = get_object_or_404(AnnouncementImage, pk=image_id, announcement=announcement)
        
        image.delete()
        
        remaining_images = announcement.images.all()
        if remaining_images.exists():
            announcement.image = remaining_images.first().image
            announcement.save(update_fields=['image'])
        else:
            announcement.image = None
            announcement.save(update_fields=['image'])
        
        return JsonResponse({
            'success': True,
            'message': 'Image deleted successfully',
            'remaining_count': remaining_images.count()
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)

@login_required
def reorder_images_ajax(request, announcement_id):
    try:
        announcement = get_object_or_404(Announcement, pk=announcement_id, user=request.user)
        data = json.loads(request.body)
        image_ids = data.get('image_ids', [])
        
        for index, image_id in enumerate(image_ids):
            AnnouncementImage.objects.filter(
                id=image_id, 
                announcement=announcement
            ).update(created_at=announcement.created_at.replace(second=index))

        if image_ids:
            first_image = AnnouncementImage.objects.get(id=image_ids[0])
            announcement.image = first_image.image
            announcement.save(update_fields=['image'])
        
        return JsonResponse({
            'success': True,
            'message': 'Images reordered successfully'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)

def city_search_redirect(request):
    if request.method == 'POST':
        city = request.POST.get('city', '').strip()
        if city:
            base_url = reverse('pages:offers')
            query_params = urlencode({'city': city})
            redirect_url = f"{base_url}?{query_params}"
            return redirect(redirect_url)
    
    return redirect('pages:offers')

def _format_answer(answer_data):
    """Helper function to format different answer types for display"""
    if isinstance(answer_data, dict):
        if 'text' in answer_data:
            return answer_data['text']
        elif 'value' in answer_data:
            return str(answer_data['value'])
        return str(answer_data)
    elif isinstance(answer_data, bool):
        return 'Yes' if answer_data else 'No'
    elif isinstance(answer_data, str):
        answer_data = answer_data.strip()
        if answer_data.lower() in ['true', 'yes']:
            return 'Yes'
        elif answer_data.lower() in ['false', 'no']:
            return 'No'
        return answer_data.capitalize()
    return str(answer_data)