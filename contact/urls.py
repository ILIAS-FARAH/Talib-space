from django.urls import path
from . import views

app_name = 'contact'

urlpatterns = [
    path('', views.contact_view, name='contact'),
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('mark-read/<int:message_id>/', views.mark_as_read, name='mark_as_read'),
    path('test-data/', views.test_contact_data, name='test_data'),  # Ajout de l'URL manquante
]