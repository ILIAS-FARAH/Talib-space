from django.urls import path,include
from . import views

urlpatterns = [ 

    path('admin/reports/<int:message_id>/', views.message_detail, name='message_detail'),
    path('admin/reports/<int:message_id>/update-status/', views.update_message_status, name='update_message_status'),
    
]