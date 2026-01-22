"""
PANDORA BOX - Admin Configuration
================================
This makes our models accessible through Django's admin panel.

WHY USE THE ADMIN?
- Quick way to manage data during development
- Useful for superusers to fix issues
- Good for initial data setup

WHAT WE'RE DOING:
- Registering each model
- Customizing how they display
- Adding filters and search
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, MAC, Submission, Comment, ActivityLog, Notification


# ============================================
# USER ADMIN
# ============================================
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin for User model
    Extends Django's built-in UserAdmin
    """
    
    # What fields to show in the list view
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'mac', 'is_active']
    
    # Add filters on the right sidebar
    list_filter = ['role', 'is_active', 'mac', 'date_joined']
    
    # Add search functionality
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    # Add our custom fields to the form
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Pandora Box Info', {
            'fields': ('role', 'mac', 'phone', 'profile_picture')
        }),
    )
    
    # When creating a new user
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Pandora Box Info', {
            'fields': ('role', 'mac', 'phone')
        }),
    )


# ============================================
# MAC ADMIN
# ============================================
@admin.register(MAC)
class MACAdmin(admin.ModelAdmin):
    """
    Admin for MAC (Ministries, Agencies, Commissions)
    """
    
    list_display = ['acronym', 'name', 'email', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'acronym', 'email']
    
    # Make the form organized
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'acronym', 'description', 'logo')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'address')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


# ============================================
# SUBMISSION ADMIN
# ============================================
@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    """
    Admin for Submissions
    """
    
    list_display = [
        'title', 
        'mac', 
        'content_type', 
        'status', 
        'submitted_by', 
        'submitted_at'
    ]
    
    list_filter = [
        'status', 
        'content_type', 
        'mac', 
        'is_confidential', 
        'is_published',
        'submitted_at'
    ]
    
    search_fields = ['title', 'description', 'tags']
    
    # Make certain fields read-only
    readonly_fields = ['submitted_at', 'reviewed_at', 'approved_at', 'published_at']
    
    fieldsets = (
        ('Content Information', {
            'fields': ('title', 'content_type', 'description', 'tags', 'file')
        }),
        ('Ownership', {
            'fields': ('mac', 'submitted_by', 'reviewed_by')
        }),
        ('Status', {
            'fields': ('status', 'priority', 'is_confidential', 'is_published')
        }),
        ('Review', {
            'fields': ('reviewer_comments', 'denial_reason')
        }),
        ('Timestamps', {
            'fields': ('submitted_at', 'reviewed_at', 'approved_at', 'published_at')
        }),
    )
    
    # Order by most recent first
    ordering = ['-submitted_at']


# ============================================
# COMMENT ADMIN
# ============================================
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """
    Admin for Comments
    """
    
    list_display = ['submission', 'user', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'created_at']
    search_fields = ['text', 'submission__title']
    readonly_fields = ['created_at']
    
    fieldsets = (
        (None, {
            'fields': ('submission', 'user', 'text', 'is_internal')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )


# ============================================
# ACTIVITY LOG ADMIN
# ============================================
@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """
    Admin for Activity Logs
    Read-only audit trail
    """
    
    list_display = ['user', 'action', 'submission', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['description', 'user__username']
    readonly_fields = ['user', 'action', 'submission', 'description', 'ip_address', 'created_at']
    
    # Don't allow editing or deleting logs
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


# ============================================
# NOTIFICATION ADMIN
# ============================================
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Admin for Notifications
    """
    
    list_display = ['user', 'title', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['title', 'message', 'user__username']
    readonly_fields = ['created_at']


# Customize admin site header
admin.site.site_header = "Pandora Box Administration"
admin.site.site_title = "Pandora Box Admin"
admin.site.index_title = "Welcome to Pandora Box Administration"
