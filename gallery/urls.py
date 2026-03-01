from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Map the root to 'home' to match your navbar links
    path('', views.album_list, name='home'),
    path('<int:pk>/', views.album_detail, name='album_detail'),
    path('register/', views.signin, name='register'),
    path('upload/', views.upload_photo, name='upload_photo'),
    
    # Point these to the 'register' subfolder
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    #delete album (only for superusers)
    path('albums/delete-selected/', views.delete_albums_bulk, name='delete_albums_bulk'),

    #delete photos (only for superusers or the user who uploaded them)

    path('photos/delete-bulk/', views.delete_photos_bulk, name='delete_photos_bulk'),

    path('photos/view/<int:photo_id>/', views.view_photo, name='view_photo'),
    path('photos/download/<int:photo_id>/', views.download_photo, name='download_photo'),
    path(
    'albums/cover/<int:album_id>/',
    views.view_album_cover,
    name='view_album_cover'
),
]