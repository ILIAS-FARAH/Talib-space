from django.urls import path
from . import views

urlpatterns = [
    path('inbox/', views.inbox, name='inbox'),
    path('conversation/<int:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('start/<int:announcement_id>/', views.start_conversation, name='start_conversation'),
    path('send/<int:conversation_id>/', views.send_message_ajax, name='send_message_ajax'),
]   