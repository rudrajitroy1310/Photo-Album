from django.contrib import admin
from django.urls import path, include
from gallery.views import album_list   # 👈 import this


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),

    # HOME PAGE
    path('', album_list, name='home'),

    # GALLERY
    path('gallery/', include('gallery.urls')),
]

