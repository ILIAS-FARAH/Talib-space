from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Max, OuterRef, Subquery
from django.utils import timezone
import json
from .models import Conversation, Message
from .forms import MessageForm
from etudiants.models import Announcement, QuizAttempt
import datetime
import logging

logger = logging.getLogger(__name__)
from django.db import models

@login_required
def inbox(request):
    """Display the user's message inbox"""
    latest_message = Message.objects.filter(
        conversation=OuterRef('pk')
    ).order_by('-timestamp')
    
    conversations = Conversation.objects.filter(
        participants=request.user
    ).annotate(
        latest_message_time=Subquery(latest_message.values('timestamp')[:1]),
        latest_message_content=Subquery(latest_message.values('content')[:1]),
        latest_message_sender=Subquery(latest_message.values('sender')[:1]),
        unread_count=Subquery(
            Message.objects.filter(
                conversation=OuterRef('pk'),
                is_read=False
            ).exclude(sender=request.user).values('conversation').annotate(
                count=models.Count('id')
            ).values('count')[:1]
        )
    ).order_by('-latest_message_time')
    
    for conversation in conversations:
        conversation.other_participant = conversation.get_other_participant(request.user)
    
    return render(request, 'messaging/inbox.html', {
        'conversations': conversations,
        'current_user': request.user,
    })

@login_required
def conversation_detail(request, conversation_id):
    """Display a specific conversation with quiz responses visible to both users"""
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    other_user = conversation.get_other_participant(request.user)
    
    conversations = Conversation.objects.filter(participants=request.user).order_by('-updated_at')
    
    for conv in conversations:
        conv.other_participant = conv.get_other_participant(request.user)
    
    # Mark messages as read
    conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    
    quiz_responses = []
    announcement = None
    
    # Get quiz responses for the announcement in this conversation
    if hasattr(conversation, 'announcement') and conversation.announcement is not None:
        announcement = conversation.announcement
        
        # Get all quiz attempts related to this announcement and conversation participants
        conversation_participants = list(conversation.participants.all())
        
        try:
            # Get quiz attempts from both users in the conversation
            attempts = QuizAttempt.objects.filter(
                announcement=announcement,
                user__in=conversation_participants  # Only get attempts from conversation participants
            ).select_related('user').order_by('-created_at')
            
            for attempt in attempts:
                try:
                    answers_data = attempt.answers
                    
                    # Parse JSON if it's a string
                    if isinstance(answers_data, str):
                        try:
                            answers_data = json.loads(answers_data)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse JSON for quiz attempt {attempt.id}")
                            continue
                    elif not isinstance(answers_data, dict):
                        logger.warning(f"Invalid answers data format for quiz attempt {attempt.id}")
                        continue
                    
                    # Extract questions and answers with better error handling
                    questions = answers_data.get('questions', [])
                    user_answers = answers_data.get('answers', [])
                    quiz_type = answers_data.get('quiz_type', 'shared')
                    
                    # Handle nested data structures
                    if not questions or not user_answers:
                        # Try to find questions/answers in nested structure
                        for key, value in answers_data.items():
                            if isinstance(value, dict):
                                nested_questions = value.get('questions', [])
                                nested_answers = value.get('answers', [])
                                if nested_questions and nested_answers:
                                    questions = nested_questions
                                    user_answers = nested_answers
                                    quiz_type = value.get('quiz_type', quiz_type)
                                    break
                    
                    # Create paired question-answer responses
                    paired_responses = []
                    max_items = max(len(questions), len(user_answers))
                    
                    for i in range(max_items):
                        question_text = "Question unavailable"
                        answer_text = "No answer provided"
                        
                        # Get question text
                        if i < len(questions):
                            question = questions[i]
                            if isinstance(question, dict):
                                question_text = (
                                    question.get('text') or 
                                    question.get('question') or 
                                    question.get('title') or 
                                    f'Question {i+1}'
                                )
                            elif isinstance(question, str):
                                question_text = question
                            else:
                                question_text = str(question)
                        
                        # Get answer text
                        if i < len(user_answers):
                            answer = user_answers[i]
                            answer_text = _format_answer(answer)
                        
                        paired_responses.append({
                            'question': question_text,
                            'answer': answer_text,
                            'index': i + 1
                        })
                    
                    # Only add if we have actual responses
                    if paired_responses:
                        # Get user display name with fallbacks
                        user_display_name = "Unknown User"
                        if attempt.user:
                            if hasattr(attempt.user, 'get_full_name') and attempt.user.get_full_name():
                                user_display_name = attempt.user.get_full_name()
                            elif hasattr(attempt.user, 'name') and attempt.user.name:
                                user_display_name = attempt.user.name
                            elif hasattr(attempt.user, 'username') and attempt.user.username:
                                user_display_name = attempt.user.username
                            else:
                                user_display_name = f"User {attempt.user.id}"
                        
                        quiz_responses.append({
                            'id': attempt.id,
                            'user': {
                                'id': attempt.user.id if attempt.user else None,
                                'name': user_display_name,
                                'is_current_user': attempt.user == request.user if attempt.user else False
                            },
                            'responses': paired_responses,
                            'quiz_type': quiz_type.title() if quiz_type else 'Quiz',
                            'submitted_at': attempt.created_at.strftime('%b %d, %Y at %I:%M %p'),
                            'total_questions': len(paired_responses)
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing individual quiz attempt {attempt.id}: {str(e)}", exc_info=True)
                    continue
                    
        except Exception as e:
            logger.error(f"Error processing quiz responses for announcement {announcement.id}: {str(e)}", exc_info=True)
    
    # Handle form submission
    if request.method == 'POST':
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # AJAX message submission
            content = request.POST.get('content', '').strip()
            if not content:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Message cannot be empty'
                }, status=400)
            
            try:
                message = Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    content=content
                )
                
                conversation.updated_at = timezone.now()
                conversation.save(update_fields=['updated_at'])
                
                return JsonResponse({
                    'status': 'success',
                    'message': {
                        'id': message.id,
                        'content': message.content,
                        'timestamp': message.timestamp.strftime('%g:%ia'),
                        'is_sender': True
                    }
                })
            except Exception as e:
                logger.error(f"Error sending message: {str(e)}")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Failed to send message'
                }, status=500)
        else:
            # Regular form submission
            form = MessageForm(request.POST)
            if form.is_valid():
                message = form.save(commit=False)
                message.conversation = conversation
                message.sender = request.user
                message.save()
                conversation.updated_at = timezone.now()
                conversation.save(update_fields=['updated_at'])
                return redirect('conversation_detail', conversation_id=conversation.id)
    else:
        form = MessageForm()
    
    context = {
        'conversation': conversation,
        'conversations': conversations,
        'other_user': other_user,
        'messages': conversation.messages.all().order_by('timestamp'),
        'form': form,
        'quiz_responses': quiz_responses,
        'announcement': announcement,
        'has_quiz_responses': len(quiz_responses) > 0,  # Add this line
    }
    
    return render(request, 'messaging/conversation_detail.html', context)

def _format_answer(answer_data):
    """Helper function to format different answer types for display"""
    if answer_data is None:
        return "No answer provided"
    
    if isinstance(answer_data, dict):
        # Handle structured answer data
        possible_keys = ['text', 'answer_text', 'answer', 'value', 'selected_option', 'response']
        for key in possible_keys:
            if key in answer_data and answer_data[key] is not None:
                return str(answer_data[key]).strip()
        
        # If no standard keys found, try to find any meaningful value
        for key, value in answer_data.items():
            if isinstance(value, (str, int, float, bool)) and value != '':
                return str(value)
        
        return str(answer_data)
    
    elif isinstance(answer_data, bool):
        return 'Yes' if answer_data else 'No'
    
    elif isinstance(answer_data, (int, float)):
        return str(answer_data)
    
    elif isinstance(answer_data, str):
        answer_data = answer_data.strip()
        if not answer_data:
            return "No answer provided"
        
        # Handle common boolean-like strings
        if answer_data.lower() in ['true', 'yes', 'oui']:
            return 'Yes'
        elif answer_data.lower() in ['false', 'no', 'non']:
            return 'No'
        
        return answer_data.capitalize()
    
    elif isinstance(answer_data, list):
        if not answer_data:
            return "No options selected"
        return ", ".join(str(item) for item in answer_data)
    
    return str(answer_data)

@login_required
def start_conversation(request, announcement_id):
    """Start a new conversation about an announcement"""
    announcement = get_object_or_404(Announcement, id=announcement_id)
    owner = announcement.user
    
    if owner == request.user:
        return redirect('etudiants:offer_detail', pk=announcement_id)
    
    conversation = Conversation.objects.filter(
        participants=request.user
    ).filter(
        participants=owner
    ).filter(
        announcement=announcement
    ).first()
    
    if not conversation:
        conversation = Conversation.objects.create(announcement=announcement)
        conversation.participants.add(request.user, owner)
    
    return redirect('conversation_detail', conversation_id=conversation.id)

@login_required
def send_message_ajax(request, conversation_id):
    """AJAX endpoint for sending a message"""
    if request.method != 'POST' or not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
    
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    
    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'status': 'error', 'message': 'Message cannot be empty'}, status=400)
    
    try:
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content
        )
        
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=['updated_at'])
        
        return JsonResponse({
            'status': 'success',
            'message': {
                'id': message.id,
                'content': message.content,
                'timestamp': message.timestamp.strftime('%b %d, %Y, %I:%M %p'),
                'is_sender': True
            }
        })
        
    except Exception as e:
        logger.error(f"Error sending message via AJAX: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to send message'
        }, status=500)