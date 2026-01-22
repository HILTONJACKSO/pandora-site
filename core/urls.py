"""
PANDORA BOX - Core App URLs
================================
URL patterns for the main application
"""

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Submissions
    path('submissions/', views.submission_list, name='submission_list'),
    path('submissions/create/', views.submission_create, name='submission_create'),
    path('submissions/<int:pk>/', views.submission_detail, name='submission_detail'),
    path('submissions/<int:pk>/edit/', views.submission_edit, name='submission_edit'),
    path('submissions/<int:pk>/review/', views.submission_review, name='submission_review'),
    path('submissions/<int:pk>/delete/', views.submission_delete, name='submission_delete'),
    
    # Content Library
    path('library/', views.content_library, name='content_library'),
    
    # User Management (Admin only)
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    
    # MAC Management (Admin only)
    path('macs/', views.mac_list, name='mac_list'),
    path('macs/create/', views.mac_create, name='mac_create'),
    path('macs/<int:pk>/edit/', views.mac_edit, name='mac_edit'),
    path('macs/<int:pk>/delete/', views.mac_delete, name='mac_delete'),
    
    # Activity Log
    path('activity-log/', views.activity_log, name='activity_log'),
    
    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:pk>/read/', views.notification_read, name='notification_read'),
    
    # Profile
    path('profile/', views.profile, name='profile'),
]