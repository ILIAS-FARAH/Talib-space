from django.urls import path
from . import views

app_name = 'etudiants'

urlpatterns = [

    path('offers/<int:pk>/', views.offer_detail, name='offer_detail'),
    path('my-announcements/', views.my_announcements, name='my_announcements'),
    path('my-favorites/', views.my_favorites, name='my_favorites'),
    path('toggle-favorite/<int:announcement_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('accept-announcement/<int:pk>/', views.accept_announcement, name='accept_announcement'),
    path('create/', views.create_announcement_view, name='create_announcement'),
    path('update/<int:pk>/', views.update_announcement_view, name='update_announcement'),
    path('delete/<int:pk>/', views.delete_announcement_view, name='delete_announcement'),
    path('staff-delete/<int:pk>/', views.staff_delete_announcement_view, name='staff_delete_announcement'),
    path('delete-image/<int:announcement_id>/<int:image_id>/', views.delete_image_ajax, name='delete_image_ajax'),
    path('reorder-images/<int:announcement_id>/', views.reorder_images_ajax, name='reorder_images_ajax'),
    path('city-search/', views.city_search_redirect, name='city_search'),
    path('submit-quiz/<int:announcement_id>/', views.submit_quiz, name='submit_quiz'),
]