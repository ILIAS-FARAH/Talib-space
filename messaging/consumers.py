import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Conversation, Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        
        # Anonymous users can't connect
        if self.user.is_anonymous:
            await self.close()
            return
            
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        
        # Check if user is part of this conversation
        is_participant = await self.is_conversation_participant()
        if not is_participant:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type', 'message')
        
        if message_type == 'message':
            message = text_data_json['message']
            
            # Save message to database
            message_obj = await self.save_message(message)
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender_id': self.user.id,
                    'sender_name': f"{self.user.name} {self.user.surname}",
                    'timestamp': message_obj['timestamp'],
                    'message_id': message_obj['id']
                }
            )
        elif message_type == 'typing':
            is_typing = text_data_json.get('is_typing', False)
            
            # Send typing status to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_status',
                    'sender_id': self.user.id,
                    'sender_name': f"{self.user.name} {self.user.surname}",
                    'is_typing': is_typing
                }
            )
        elif message_type == 'read':
            # Mark messages as read
            await self.mark_messages_read()
            
            # Notify other users
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'messages_read',
                    'reader_id': self.user.id
                }
            )
    
    # Receive message from room group
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'timestamp': event['timestamp'],
            'message_id': event['message_id']
        }))
    
    # Receive typing status from room group
    async def typing_status(self, event):
        # Send typing status to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'is_typing': event['is_typing']
        }))
    
    # Receive read status from room group
    async def messages_read(self, event):
        # Send read status to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'read',
            'reader_id': event['reader_id']
        }))
    
    @database_sync_to_async
    def is_conversation_participant(self):
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return conversation.participants.filter(id=self.user.id).exists()
        except Conversation.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_message(self, content):
        conversation = Conversation.objects.get(id=self.conversation_id)
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            content=content
        )
        
        # Update conversation timestamp
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=['updated_at'])
        
        return {
            'id': message.id,
            'timestamp': message.timestamp.strftime('%b %d, %Y, %I:%M %p')
        }
    
    @database_sync_to_async
    def mark_messages_read(self):
        conversation = Conversation.objects.get(id=self.conversation_id)
        unread_messages = conversation.messages.filter(is_read=False).exclude(sender=self.user)
        unread_messages.update(is_read=True)