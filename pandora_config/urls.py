"""
PANDORA BOX - URL Configuration
================================
This file routes URLs to views.

HOW IT WORKS:
User visits URL → Django checks this file → Calls the right view → Returns HTML

STRUCTURE:
/admin/ → Django admin panel
/login/ → Login page
/dashboard/ → Main dashboard
/submissions/ → All submission-related pages
/users/ → User management
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static




urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),
    
    # Our app URLs
    path('', include('core.urls')),
]

# Serve media files in development
# In production, nginx/apache will handle this
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


 