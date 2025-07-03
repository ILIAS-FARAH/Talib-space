from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from .forms import ContactForm
from .models import ContactMessage
import logging

# Configuration du logging
logger = logging.getLogger(__name__)

def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Sauvegarder le message en base de données
            contact_message = form.save()
            
            # Préparer les données pour l'email
            context = {
                'name': contact_message.name,
                'email': contact_message.email,
                'subject': contact_message.get_subject_display_full(),
                'message': contact_message.message,
                'date': contact_message.created_at,
            }
            
            try:
                logger.info(f"📧 Tentative d'envoi d'email pour {contact_message.name}")
                
                # Email pour l'administrateur
                admin_subject = f"Nouveau message de contact - {contact_message.get_subject_display_full()}"
                admin_html_message = render_to_string('welcompage/email_admin.html', context)
                admin_plain_message = strip_tags(admin_html_message)
                
                send_mail(
                    subject=admin_subject,
                    message=admin_plain_message,
                    html_message=admin_html_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.CONTACT_EMAIL],
                    fail_silently=False,
                )
                
                logger.info("✅ Email administrateur envoyé avec succès")
                
                # Email de confirmation pour l'utilisateur
                user_subject = "Confirmation de réception de votre message - Talib Space"
                user_html_message = render_to_string('welcompage/email_user_confirmation.html', context)
                user_plain_message = strip_tags(user_html_message)
                
                send_mail(
                    subject=user_subject,
                    message=user_plain_message,
                    html_message=user_html_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[contact_message.email],
                    fail_silently=False,
                )
                
                logger.info("✅ Email de confirmation utilisateur envoyé avec succès")
                
                messages.success(request, 'Votre message a été envoyé avec succès ! Nous vous répondrons dans les plus brefs délais.')
                return redirect('contact:contact')
                
            except Exception as e:
                # Log l'erreur pour le débogage
                logger.error(f"❌ Erreur d'envoi d'email: {e}")
                
                # Message d'erreur plus informatif
                if 'authentication' in str(e).lower() or 'username' in str(e).lower():
                    error_msg = 'Erreur d\'authentification Gmail. Vérifiez le mot de passe d\'application.'
                elif 'connection' in str(e).lower() or 'network' in str(e).lower():
                    error_msg = 'Erreur de connexion. Vérifiez votre connexion internet.'
                elif 'smtp' in str(e).lower():
                    error_msg = 'Erreur SMTP. Vérifiez la configuration Gmail.'
                else:
                    error_msg = f'Erreur technique: {str(e)}'
                
                # Le message est quand même sauvegardé en base
                messages.warning(request, f'Votre message a été enregistré mais l\'envoi par email a échoué: {error_msg}')
                print(f"❌ Erreur d'envoi d'email: {e}")
                
        else:
            messages.error(request, 'Veuillez corriger les erreurs dans le formulaire.')
    else:
        form = ContactForm()
    
    return render(request, 'welcompage/contact.html', {'form': form})


@staff_member_required
def reports_dashboard(request):
    """Vue pour afficher tous les messages de contact (pour les admins)"""
    print("🔍 DEBUG: Entering reports_dashboard view")
    print(f"🔍 DEBUG: User: {request.user.name}, is_staff: {request.user.is_staff}")
    
    try:
        # Test direct de la base de données
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM contact_contactmessage")
            db_count = cursor.fetchone()[0]
            print(f"🔍 DEBUG: Direct DB query count: {db_count}")
        
        # Test du modèle
        total_messages_in_db = ContactMessage.objects.count()
        print(f"🔍 DEBUG: Model query count: {total_messages_in_db}")
        
        if total_messages_in_db == 0:
            print("❌ DEBUG: No messages found in database!")
            # Créer un message de test
            test_message = ContactMessage.objects.create(
                name="Test User",
                email="test@example.com",
                subject="question",
                message="This is a test message created by the debug system."
            )
            print(f"✅ DEBUG: Created test message with ID: {test_message.id}")
            total_messages_in_db = ContactMessage.objects.count()
        
        # Récupérer tous les messages de contact
        contact_messages = ContactMessage.objects.all()
        print(f"🔍 DEBUG: Retrieved {contact_messages.count()} messages")
        
        # Afficher les premiers messages pour debug
        for i, msg in enumerate(contact_messages[:3]):
            print(f"🔍 DEBUG: Message {i+1}: ID={msg.id}, Name={msg.name}, Email={msg.email}")
        
        # Filtres
        subject_filter = request.GET.get('subject')
        read_status_filter = request.GET.get('read_status')
        search_query = request.GET.get('search')
        
        print(f"🔍 DEBUG: Applied filters - subject: {subject_filter}, read_status: {read_status_filter}, search: {search_query}")
        
        # Appliquer les filtres seulement s'ils existent
        original_count = contact_messages.count()
        
        if subject_filter:
            contact_messages = contact_messages.filter(subject=subject_filter)
            print(f"🔍 DEBUG: After subject filter: {contact_messages.count()}/{original_count}")
        
        if read_status_filter == 'read':
            contact_messages = contact_messages.filter(is_read=True)
            print(f"🔍 DEBUG: After read filter: {contact_messages.count()}/{original_count}")
        elif read_status_filter == 'unread':
            contact_messages = contact_messages.filter(is_read=False)
            print(f"🔍 DEBUG: After unread filter: {contact_messages.count()}/{original_count}")
        
        if search_query:
            contact_messages = contact_messages.filter(
                Q(name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(message__icontains=search_query)
            )
            print(f"🔍 DEBUG: After search filter: {contact_messages.count()}/{original_count}")
        
        # Ordonner par date de création (plus récent en premier)
        contact_messages = contact_messages.order_by('-created_at')
        
        # Calculer les statistiques sur TOUS les messages (pas les filtrés)
        all_messages = ContactMessage.objects.all()
        total_count = all_messages.count()
        unread_count = all_messages.filter(is_read=False).count()
        read_count = all_messages.filter(is_read=True).count()
        
        # Messages de cette semaine
        week_ago = timezone.now() - timedelta(days=7)
        recent_count = all_messages.filter(created_at__gte=week_ago).count()
        
        # Messages par statut pour les graphiques (optionnel)
        today = timezone.now().date()
        messages_today = all_messages.filter(created_at__date=today).count()
        
        # Sujets les plus fréquents (optionnel pour analytics)
        subject_stats = (
            all_messages.values('subject')
            .annotate(count=Count('subject'))
            .order_by('-count')[:5]
        )
        
        # Debug final
        final_messages_list = list(contact_messages.values('id', 'name', 'email', 'subject', 'is_read'))
        print(f"🔍 DEBUG: Final messages to display: {len(final_messages_list)}")
        for msg in final_messages_list[:3]:
            print(f"   - {msg}")
        
        context = {
            'contact_messages': contact_messages,
            'total_count': total_count,
            'unread_count': unread_count,
            'read_count': read_count,
            'recent_count': recent_count,
            'messages_today': messages_today,
            'subject_stats': subject_stats,
            # Filter values for maintaining form state
            'current_subject_filter': subject_filter,
            'current_read_status_filter': read_status_filter,
            'current_search_query': search_query,
        }
        
        print(f"🔍 DEBUG: Context prepared with {len(context)} keys")
        print(f"🔍 DEBUG: contact_messages in context: {context['contact_messages'].count()} items")
        
        return render(request, 'welcompage/reports_dashboard.html', context)
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR in reports_dashboard: {type(e).__name__}: {e}")
        import traceback
        print(f"❌ Stack trace: {traceback.format_exc()}")
        
        # Retourner une vue d'erreur avec des données vides
        context = {
            'contact_messages': ContactMessage.objects.none(),
            'total_count': 0,
            'unread_count': 0,
            'read_count': 0,
            'recent_count': 0,
            'error_message': str(e),
        }
        
        return render(request, 'welcompage/reports_dashboard.html', context)

@staff_member_required
def debug_dashboard(request):
    """Vue de debug complète pour diagnostiquer les problèmes"""
    print("🔍 DEBUG: Entering debug_dashboard view")
    
    try:
        # Test direct de la base de données
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM contact_contactmessage")
            db_count = cursor.fetchone()[0]
        
        # Test du modèle
        all_messages = ContactMessage.objects.all()
        total_count = all_messages.count()
        
        context = {
            'contact_messages': all_messages,
            'total_count': total_count,
            'unread_count': all_messages.filter(is_read=False).count(),
            'read_count': all_messages.filter(is_read=True).count(),
            'recent_count': all_messages.filter(created_at__gte=timezone.now() - timedelta(days=7)).count(),
            'db_count': db_count,
            'debug_mode': True,
        }
        
        return render(request, 'welcompage/debug_dashboard.html', context)
        
    except Exception as e:
        print(f"❌ Error in debug_dashboard: {e}")
        context = {
            'error_message': str(e),
            'contact_messages': ContactMessage.objects.none(),
            'total_count': 0,
        }
        return render(request, 'welcompage/debug_dashboard.html', context)

@staff_member_required
def mark_as_read(request, message_id):
    """Marquer un message comme lu"""
    try:
        message = get_object_or_404(ContactMessage, id=message_id)
        message.is_read = True
        message.save()
        messages.success(request, f"Message de {message.name} marqué comme lu.")
        print(f"✅ Message {message_id} marqué comme lu par {request.user.username}")
    except Exception as e:
        print(f"❌ Erreur lors du marquage: {e}")
        
    
    return redirect('contact:reports_dashboard')


@staff_member_required
def test_contact_data(request):
    """Vue de test pour vérifier les données de contact"""
    print("🧪 DEBUG: Entering test_contact_data view")
    
    try:
        messages_count = ContactMessage.objects.count()
        recent_messages = ContactMessage.objects.all().order_by('-created_at')[:5]
        
        print(f"🧪 Test des données:")
        print(f"   - Nombre total de messages: {messages_count}")
        print(f"   - Messages récents: {[f'{m.name} ({m.email})' for m in recent_messages]}")
        
        # Si pas de messages, en créer quelques-uns pour les tests
        if messages_count == 0:
            print("🧪 Creating test data...")
            test_messages = [
                {
                    'name': 'Jean Dupont',
                    'email': 'jean.dupont@example.com',
                    'subject': 'question',
                    'message': 'Bonjour, j\'ai une question concernant votre service.'
                },
                {
                    'name': 'Marie Martin',
                    'email': 'marie.martin@example.com',
                    'subject': 'technical',
                    'message': 'J\'ai un problème technique avec mon compte.'
                },
                {
                    'name': 'Pierre Durand',
                    'email': 'pierre.durand@example.com',
                    'subject': 'partnership',
                    'message': 'Je souhaiterais discuter d\'un partenariat.'
                }
            ]
            
            for test_data in test_messages:
                ContactMessage.objects.create(**test_data)
                print(f"✅ Created test message for {test_data['name']}")
            
            # Recalculer après création
            messages_count = ContactMessage.objects.count()
            recent_messages = ContactMessage.objects.all().order_by('-created_at')[:5]
        
        context = {
            'messages_count': messages_count,
            'recent_messages': recent_messages,
        }
        
        return render(request, 'contact/test_data.html', context)
        
    except Exception as e:
        print(f"❌ Error in test_contact_data: {e}")
        context = {
            'messages_count': 0,
            'recent_messages': [],
            'error': str(e)
        }
        return render(request, 'contact/test_data.html', context)