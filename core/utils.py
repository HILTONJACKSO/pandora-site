"""
PANDORA BOX - Utility Functions
================================
Reusable helper functions used throughout the app

WHY SEPARATE UTILITIES?
- Keeps views.py clean
- Reusable code
- Easier to test
- Single source of truth
"""

from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from .models import ActivityLog, Notification
from functools import wraps


# ============================================
# ACTIVITY LOGGING
# ============================================

def log_activity(user, action, submission=None, description="", request=None):
    """
    Log user activity for audit trail
    
    Args:
        user: User who performed the action
        action: Action type (from ActivityLog.ACTION_CHOICES)
        submission: Related submission (optional)
        description: Details of what happened
        request: HTTP request object (to get IP address)
    
    Example:
        log_activity(request.user, 'SUBMISSION_CREATED', 
                    submission=sub, description="Created press release")
    """
    ip_address = None
    if request:
        # Get user's IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
    
    ActivityLog.objects.create(
        user=user,
        action=action,
        submission=submission,
        description=description,
        ip_address=ip_address
    )


# ============================================
# NOTIFICATION SYSTEM
# ============================================

def create_notification(user, title, message, submission=None):
    """
    Create an in-app notification for a user
    
    Args:
        user: User to notify
        title: Notification title
        message: Notification message
        submission: Related submission (optional)
    
    Example:
        create_notification(mac_officer, "Submission Approved", 
                          "Your press release has been approved!")
    """
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        submission=submission
    )


def send_email_notification(user, subject, message):
    """
    Send email notification to user
    
    In development, this prints to console.
    In production, this sends actual email.
    
    Args:
        user: User to email
        subject: Email subject
        message: Email body
    """
    try:
        send_mail(
            subject=f"[Pandora Box] {subject}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@pandorabox.gov.lr',
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Email error: {e}")


def notify_submission_status_change(submission, old_status, new_status):
    """
    Notify relevant users when submission status changes
    
    This is called whenever a submission status is updated.
    Sends notifications to MAC officer and/or reviewers.
    """
    
    # Notify the submitter
    if submission.submitted_by:
        title = f"Submission Status Updated: {submission.title}"
        
        if new_status == 'APPROVED':
            message = f"Great news! Your submission has been approved and will be published."
        elif new_status == 'DENIED':
            message = f"Your submission has been denied. Reason: {submission.denial_reason}"
        elif new_status == 'RETURNED':
            message = f"Your submission has been returned for edits. Please review the comments."
        elif new_status == 'UNDER_REVIEW':
            message = f"Your submission is now under review by MICAT."
        else:
            message = f"Your submission status changed from {old_status} to {new_status}."
        
        create_notification(
            user=submission.submitted_by,
            title=title,
            message=message,
            submission=submission
        )
        
        # Also send email
        send_email_notification(submission.submitted_by, title, message)


# ============================================
# PERMISSION DECORATORS
# ============================================

def role_required(*roles):
    """
    Decorator to restrict view access to specific roles
    
    Usage:
        @role_required('MAC_OFFICER', 'ADMIN')
        def my_view(request):
            # Only MAC officers and admins can access this
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and request.user.role in roles:
                return view_func(request, *args, **kwargs)
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, "You don't have permission to access this page.")
            return redirect('dashboard')
        return _wrapped_view
    return decorator


def mac_officer_required(view_func):
    """Decorator: Only MAC officers can access"""
    return role_required('MAC_OFFICER')(view_func)


def micat_reviewer_required(view_func):
    """Decorator: Only MICAT reviewers can access"""
    return role_required('MICAT_REVIEWER')(view_func)


def admin_required(view_func):
    """Decorator: Only admins can access"""
    return role_required('ADMIN')(view_func)


# ============================================
# FILE HANDLING
# ============================================

def get_file_icon(filename):
    """
    Return appropriate icon/class for file type
    
    Args:
        filename: Name of the file
    
    Returns:
        String: CSS class or icon name
    """
    extension = filename.split('.')[-1].lower() if '.' in filename else ''
    
    icon_map = {
        'pdf': 'file-pdf',
        'doc': 'file-word',
        'docx': 'file-word',
        'xls': 'file-excel',
        'xlsx': 'file-excel',
        'ppt': 'file-powerpoint',
        'pptx': 'file-powerpoint',
        'jpg': 'file-image',
        'jpeg': 'file-image',
        'png': 'file-image',
        'gif': 'file-image',
        'mp4': 'file-video',
        'avi': 'file-video',
        'mov': 'file-video',
        'txt': 'file-text',
    }
    
    return icon_map.get(extension, 'file')


def format_file_size(size_bytes):
    """
    Convert bytes to human-readable format
    
    Args:
        size_bytes: File size in bytes
    
    Returns:
        String: "1.5 MB", "230 KB", etc.
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


# ============================================
# STATUS HELPERS
# ============================================

def get_status_badge_class(status):
    """
    Return CSS class for status badge
    
    Args:
        status: Status string (PENDING, APPROVED, etc.)
    
    Returns:
        String: CSS class name
    """
    status_classes = {
        'PENDING': 'badge-warning',
        'UNDER_REVIEW': 'badge-info',
        'APPROVED': 'badge-success',
        'DENIED': 'badge-danger',
        'RETURNED': 'badge-primary',
    }
    return status_classes.get(status, 'badge-secondary')


# ============================================
# STATISTICS HELPERS
# ============================================

def get_dashboard_stats(user):
    """
    Get statistics for dashboard based on user role
    
    Args:
        user: Current user
    
    Returns:
        Dict: Statistics relevant to user's role
    """
    from .models import Submission
    
    stats = {}
    
    if user.is_mac_officer():
        # MAC Officer sees only their MAC's stats
        stats = {
            'total': Submission.objects.filter(mac=user.mac).count(),
            'pending': Submission.objects.filter(mac=user.mac, status='PENDING').count(),
            'under_review': Submission.objects.filter(mac=user.mac, status='UNDER_REVIEW').count(),
            'approved': Submission.objects.filter(mac=user.mac, status='APPROVED').count(),
            'denied': Submission.objects.filter(mac=user.mac, status='DENIED').count(),
            'returned': Submission.objects.filter(mac=user.mac, status='RETURNED').count(),
        }
    
    elif user.is_micat_reviewer():
        # MICAT sees all submissions
        stats = {
            'total': Submission.objects.all().count(),
            'pending': Submission.objects.filter(status='PENDING').count(),
            'under_review': Submission.objects.filter(status='UNDER_REVIEW').count(),
            'approved': Submission.objects.filter(status='APPROVED').count(),
            'denied': Submission.objects.filter(status='DENIED').count(),
            'returned': Submission.objects.filter(status='RETURNED').count(),
            'my_reviews': Submission.objects.filter(reviewed_by=user).count(),
        }
    
    elif user.is_admin():
        # Admin sees everything
        from .models import User, MAC
        stats = {
            'total_submissions': Submission.objects.all().count(),
            'pending': Submission.objects.filter(status='PENDING').count(),
            'total_users': User.objects.filter(is_active=True).count(),
            'total_macs': MAC.objects.filter(is_active=True).count(),
            'approved_today': Submission.objects.filter(
                status='APPROVED',
                approved_at__date=timezone.now().date()
            ).count() if hasattr(Submission.objects.filter(status='APPROVED').first(), 'approved_at') else 0,
        }
    
    return stats


# Import timezone for date comparisons
from django.utils import timezone