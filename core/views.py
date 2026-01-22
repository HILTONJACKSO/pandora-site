"""
PANDORA BOX - Views
================================
This file handles all user requests and returns responses.

WHAT ARE VIEWS?
Views are Python functions that:
1. Receive a request
2. Process data (query database, validate forms)
3. Return a response (render HTML template)

FLOW: URL → View → Template → HTML Response
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone

from .models import User, MAC, Submission, Comment, ActivityLog, Notification
from .utils import (
    log_activity, 
    create_notification, 
    get_dashboard_stats,
    role_required,
    mac_officer_required,
    micat_reviewer_required,
    admin_required
)

from django.db.models import Count, Q, Avg
from django.db.models.functions import TruncDate
from datetime import timedelta


# ============================================
# AUTHENTICATION VIEWS
# ============================================

def login_view(request):
    """
    Handle user login
    
    GET: Show login form
    POST: Process login credentials
    
    FLOW:
    1. User submits username + password
    2. Django checks if they match
    3. If yes → log them in and redirect to dashboard
    4. If no → show error message
    """
    
    # If already logged in, go to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    # Handle POST (form submission)
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check if user is active
            if user.is_active:
                # Log them in
                login(request, user)
                
                # Log activity
                log_activity(
                    user=user,
                    action='USER_LOGIN',
                    description=f"{user.username} logged in successfully",
                    request=request
                )
                
                # Success message
                messages.success(request, f"Welcome back, {user.get_full_name()}!")
                
                # Redirect to dashboard
                return redirect('dashboard')
            else:
                messages.error(request, "Your account has been deactivated. Contact admin.")
        else:
            messages.error(request, "Invalid username or password.")
    
    # Show login form (GET request or failed POST)
    return render(request, 'registration/login.html')


@login_required
def logout_view(request):
    """
    Handle user logout
    
    WHY @login_required?
    Only logged-in users can logout (prevents errors)
    """
    
    # Log activity before logout
    log_activity(
        user=request.user,
        action='USER_LOGIN',  # We'll add USER_LOGOUT to choices later
        description=f"{request.user.username} logged out",
        request=request
    )
    
    # Logout user
    logout(request)
    
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')


# ============================================
# DASHBOARD VIEWS
# ============================================

@login_required
def dashboard(request):
    """
    Main dashboard - different view based on user role
    
    WHY DIFFERENT DASHBOARDS?
    - MAC Officer: See only their submissions
    - MICAT Reviewer: See all submissions to review
    - Admin: See system-wide statistics
    
    CONTEXT: Data passed to template
    """
    
    user = request.user
    
    # Get statistics based on role
    stats = get_dashboard_stats(user)
    
    # Get recent submissions based on role
    if user.is_mac_officer():
        # MAC officers see only their MAC's submissions
        recent_submissions = Submission.objects.filter(
            mac=user.mac
        ).order_by('-submitted_at')[:10] if user.mac else []
        
    elif user.is_micat_reviewer():
        # MICAT reviewers see all pending/under review submissions
        recent_submissions = Submission.objects.filter(
            status__in=['PENDING', 'UNDER_REVIEW']
        ).order_by('-submitted_at')[:10]
        
    else:  # Admin
        # Admins see all recent submissions
        recent_submissions = Submission.objects.all().order_by('-submitted_at')[:10]
    
    # Get recent activity (last 10 actions)
    recent_activity = ActivityLog.objects.all()[:10]
    
    # Get unread notifications count
    unread_count = Notification.objects.filter(
        user=user,
        is_read=False
    ).count()
    
    # Prepare context (data for template)
    context = {
        'stats': stats,
        'recent_submissions': recent_submissions,
        'recent_activity': recent_activity,
        'unread_count': unread_count,
    }
    
    return render(request, 'core/dashboard.html', context)


# ============================================
# SUBMISSION VIEWS
# ============================================

@login_required
def submission_list(request):
    """
    List all submissions with filters
    
    FEATURES:
    - Search by title/description
    - Filter by status
    - Filter by MAC (for MICAT/Admin)
    - Pagination (coming in Day 3)
    """
    
    user = request.user
    
    # Base queryset based on role
    if user.is_mac_officer():
        # MAC officers see only their MAC's submissions
        submissions = Submission.objects.filter(mac=user.mac)
    else:
        # MICAT and Admin see all
        submissions = Submission.objects.all()
    
    # Apply filters from GET parameters
    status_filter = request.GET.get('status')
    mac_filter = request.GET.get('mac')
    search = request.GET.get('search')
    
    if status_filter:
        submissions = submissions.filter(status=status_filter)
    
    if mac_filter and not user.is_mac_officer():
        submissions = submissions.filter(mac_id=mac_filter)
    
    if search:
        submissions = submissions.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search) |
            Q(tags__icontains=search)
        )
    
    # Order by most recent
    submissions = submissions.order_by('-submitted_at')
    
    # Get all MACs for filter dropdown (if not MAC officer)
    macs = MAC.objects.filter(is_active=True) if not user.is_mac_officer() else None
    
    # Count by status
    status_counts = {
        'all': submissions.count(),
        'pending': submissions.filter(status='PENDING').count(),
        'under_review': submissions.filter(status='UNDER_REVIEW').count(),
        'approved': submissions.filter(status='APPROVED').count(),
        'denied': submissions.filter(status='DENIED').count(),
        'returned': submissions.filter(status='RETURNED').count(),
    }
    
    context = {
        'submissions': submissions,
        'macs': macs,
        'status_counts': status_counts,
        'current_status': status_filter,
        'current_mac': mac_filter,
        'search_query': search,
        'unread_count': Notification.objects.filter(user=user, is_read=False).count(),
    }
    
    return render(request, 'core/submission_list.html', context)


@login_required
@mac_officer_required
def submission_create(request):
    """
    Create new submission - MAC Officers only
    
    GET: Show upload form
    POST: Process form and save submission
    
    VALIDATION:
    - All required fields filled
    - Valid file type
    - User belongs to a MAC
    """
    
    user = request.user
    
    # Check if user has a MAC assigned
    if not user.mac:
        messages.error(request, "You must be assigned to a MAC to submit content.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        # Get form data
        title = request.POST.get('title')
        content_type = request.POST.get('content_type')
        description = request.POST.get('description')
        tags = request.POST.get('tags', '')
        is_confidential = request.POST.get('is_confidential') == 'on'
        file = request.FILES.get('file')
        
        # Validation
        errors = []
        
        if not title:
            errors.append("Title is required")
        if not description:
            errors.append("Description is required")
        if not file:
            errors.append("File is required")
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Create submission
            submission = Submission.objects.create(
                title=title,
                content_type=content_type,
                description=description,
                tags=tags,
                is_confidential=is_confidential,
                file=file,
                mac=user.mac,
                submitted_by=user,
                status='PENDING'
            )
            
            # Log activity
            log_activity(
                user=user,
                action='SUBMISSION_CREATED',
                submission=submission,
                description=f"Created submission: {title}",
                request=request
            )
            
            # Notify MICAT reviewers
            micat_reviewers = User.objects.filter(role='MICAT_REVIEWER', is_active=True)
            for reviewer in micat_reviewers:
                create_notification(
                    user=reviewer,
                    title="New Submission",
                    message=f"{user.mac.acronym} submitted: {title}",
                    submission=submission
                )
            
            messages.success(request, "Submission created successfully! It's now pending review.")
            return redirect('submission_detail', pk=submission.pk)
    
    # GET: Show form
    context = {
        'unread_count': Notification.objects.filter(user=user, is_read=False).count(),
    }
    
    return render(request, 'core/submission_create.html', context)


@login_required
def submission_detail(request, pk):
    """
    View submission details
    
    FEATURES:
    - View all information
    - See comments
    - Download file
    - Add comments (MICAT only)
    - Edit/Delete buttons (if allowed)
    """
    
    submission = get_object_or_404(Submission, pk=pk)
    user = request.user
    
    # Check permissions
    can_view = False
    
    if user.is_admin():
        can_view = True
    elif user.is_micat_reviewer():
        can_view = True
    elif user.is_mac_officer() and submission.mac == user.mac:
        can_view = True
    
    if not can_view:
        messages.error(request, "You don't have permission to view this submission.")
        return redirect('dashboard')
    
    # Handle comment submission
    if request.method == 'POST' and 'add_comment' in request.POST:
        if user.is_micat_reviewer():
            comment_text = request.POST.get('comment_text')
            is_internal = request.POST.get('is_internal') == 'on'
            
            if comment_text:
                Comment.objects.create(
                    submission=submission,
                    user=user,
                    text=comment_text,
                    is_internal=is_internal
                )
                
                # Log activity
                log_activity(
                    user=user,
                    action='COMMENT_ADDED',
                    submission=submission,
                    description=f"Added comment on '{submission.title}'",
                    request=request
                )
                
                # Notify submitter if not internal
                if not is_internal and submission.submitted_by:
                    create_notification(
                        user=submission.submitted_by,
                        title="New Comment",
                        message=f"MICAT added a comment on '{submission.title}'",
                        submission=submission
                    )
                
                messages.success(request, "Comment added successfully!")
                return redirect('submission_detail', pk=pk)
    
    # Get comments (internal comments only for reviewers/admins)
    if user.is_micat_reviewer() or user.is_admin():
        comments = submission.comments.all().order_by('-created_at')
    else:
        comments = submission.comments.filter(is_internal=False).order_by('-created_at')
    
    # Check if user can edit
    can_edit = submission.can_be_edited_by(user)
    
    # Process tags for display
    tag_list = []
    if submission.tags:
        tag_list = [tag.strip() for tag in submission.tags.split(',') if tag.strip()]
    
    context = {
        'submission': submission,
        'comments': comments,
        'can_edit': can_edit,
        'tag_list': tag_list,  # Add processed tags
    }
    
    return render(request, 'core/submission_detail.html', context)


# ============================================
# CONTENT LIBRARY
# ============================================

@login_required
def content_library(request):
    """
    Public library of approved content
    All users can view published content
    """
    
    # Only show approved and published content
    content = Submission.objects.filter(
        status='APPROVED',
        is_published=True
    ).order_by('-published_at')
    
    # Apply filters
    content_type_filter = request.GET.get('type')
    mac_filter = request.GET.get('mac')
    search = request.GET.get('search')
    
    if content_type_filter:
        content = content.filter(content_type=content_type_filter)
    
    if mac_filter:
        content = content.filter(mac_id=mac_filter)
    
    if search:
        content = content.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search) |
            Q(tags__icontains=search)
        )
    
    # Get MACs for filter
    macs = MAC.objects.filter(is_active=True)
    
    context = {
        'content': content,
        'macs': macs,
        'unread_count': Notification.objects.filter(user=request.user, is_read=False).count(),
    }
    
    return render(request, 'core/content_library.html', context)


# ============================================
# NOTIFICATIONS
# ============================================

@login_required
def notifications(request):
    """
    View all notifications
    """
    
    user_notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    context = {
        'notifications': user_notifications,
        'unread_count': user_notifications.filter(is_read=False).count(),
    }
    
    return render(request, 'core/notifications.html', context)


@login_required
def notification_read(request, pk):
    """
    Mark notification as read
    """
    
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    
    # Redirect to submission if linked
    if notification.submission:
        return redirect('submission_detail', pk=notification.submission.pk)
    
    return redirect('notifications')


# ============================================
# ACTIVITY LOG
# ============================================

@login_required
def activity_log(request):
    """
    View activity log
    Admin sees all, others see their own
    """
    
    if request.user.is_admin():
        logs = ActivityLog.objects.all()[:100]
    else:
        logs = ActivityLog.objects.filter(user=request.user)[:50]
    
    context = {
        'logs': logs,
        'unread_count': Notification.objects.filter(user=request.user, is_read=False).count(),
    }
    
    return render(request, 'core/activity_log.html', context)


# ============================================
# PROFILE
# ============================================

@login_required
def profile(request):
    """
    View and edit user profile
    """
    
    user = request.user
    
    if request.method == 'POST':
        # Update profile
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone = request.POST.get('phone', user.phone)
        
        # Handle profile picture
        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
        
        user.save()
        
        messages.success(request, "Profile updated successfully!")
        return redirect('profile')
    
    context = {
        'unread_count': Notification.objects.filter(user=user, is_read=False).count(),
    }
    
    return render(request, 'core/profile.html', context)


# Placeholder views for user/MAC management (Day 3-4)
@login_required
@admin_required
def user_list(request):
    """
    List all users - Admin only
    """
    
    users = User.objects.all().order_by('-date_joined')
    
    # Apply filters
    role_filter = request.GET.get('role')
    mac_filter = request.GET.get('mac')
    search = request.GET.get('search')
    status_filter = request.GET.get('status')
    
    if role_filter:
        users = users.filter(role=role_filter)
    
    if mac_filter:
        users = users.filter(mac_id=mac_filter)
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
    
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    # Get MACs for filter
    macs = MAC.objects.filter(is_active=True).order_by('acronym')
    
    # Count by role
    role_counts = {
        'all': User.objects.count(),
        'admin': User.objects.filter(role='ADMIN').count(),
        'micat': User.objects.filter(role='MICAT_REVIEWER').count(),
        'mac_officer': User.objects.filter(role='MAC_OFFICER').count(),
        'active': User.objects.filter(is_active=True).count(),
        'inactive': User.objects.filter(is_active=False).count(),
    }
    
    context = {
        'users': users,
        'macs': macs,
        'role_counts': role_counts,
        'current_role': role_filter,
        'current_mac': mac_filter,
        'search_query': search,
        'current_status': status_filter,
    }
    
    return render(request, 'core/user_list.html', context)


@login_required
@admin_required
def user_create(request):
    """
    Create new user - Admin only
    """
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        role = request.POST.get('role')
        mac_id = request.POST.get('mac')
        phone = request.POST.get('phone', '')
        is_active = request.POST.get('is_active') == 'on'
        
        # Validation
        errors = []
        
        if not username:
            errors.append("Username is required")
        elif User.objects.filter(username=username).exists():
            errors.append("Username already exists")
        
        if not email:
            errors.append("Email is required")
        elif User.objects.filter(email=email).exists():
            errors.append("Email already exists")
        
        if not first_name:
            errors.append("First name is required")
        
        if not last_name:
            errors.append("Last name is required")
        
        if not password:
            errors.append("Password is required")
        elif len(password) < 8:
            errors.append("Password must be at least 8 characters")
        elif password != password2:
            errors.append("Passwords do not match")
        
        if not role:
            errors.append("Role is required")
        
        if role == 'MAC_OFFICER' and not mac_id:
            errors.append("MAC is required for MAC Officers")
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role,
                phone=phone,
                is_active=is_active
            )
            
            # Assign MAC if provided
            if mac_id:
                user.mac = MAC.objects.get(pk=mac_id)
                user.save()
            
            # Log activity
            log_activity(
                user=request.user,
                action='USER_CREATED',
                description=f"Created user: {username} ({role})",
                request=request
            )
            
            messages.success(request, f"User '{username}' created successfully!")
            return redirect('user_list')
    
    # GET request
    macs = MAC.objects.filter(is_active=True).order_by('acronym')
    
    context = {
        'macs': macs,
    }
    
    return render(request, 'core/user_create.html', context)


@login_required
@admin_required
def user_edit(request, pk):
    """
    Edit user - Admin only
    """
    
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        role = request.POST.get('role')
        mac_id = request.POST.get('mac')
        phone = request.POST.get('phone', '')
        is_active = request.POST.get('is_active') == 'on'
        
        # Validation
        errors = []
        
        if not email:
            errors.append("Email is required")
        elif User.objects.filter(email=email).exclude(pk=pk).exists():
            errors.append("Email already in use by another user")
        
        if not first_name:
            errors.append("First name is required")
        
        if not last_name:
            errors.append("Last name is required")
        
        if role == 'MAC_OFFICER' and not mac_id:
            errors.append("MAC is required for MAC Officers")
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Update user
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.role = role
            user.phone = phone
            user.is_active = is_active
            
            # Update MAC
            if mac_id:
                user.mac = MAC.objects.get(pk=mac_id)
            else:
                user.mac = None
            
            user.save()
            
            # Log activity
            log_activity(
                user=request.user,
                action='USER_UPDATED',
                description=f"Updated user: {user.username}",
                request=request
            )
            
            messages.success(request, f"User '{user.username}' updated successfully!")
            return redirect('user_list')
    
    # GET request
    macs = MAC.objects.filter(is_active=True).order_by('acronym')
    
    context = {
        'edit_user': user,
        'macs': macs,
    }
    
    return render(request, 'core/user_edit.html', context)


@login_required
@admin_required
def user_delete(request, pk):
    """
    Delete user - Admin only
    """
    
    user = get_object_or_404(User, pk=pk)
    
    # Prevent deleting yourself
    if user == request.user:
        messages.error(request, "You cannot delete your own account!")
        return redirect('user_list')
    
    if request.method == 'POST':
        username = user.username
        
        # Log before deleting
        log_activity(
            user=request.user,
            action='USER_UPDATED',  # We don't have USER_DELETED
            description=f"Deleted user: {username}",
            request=request
        )
        
        user.delete()
        
        messages.success(request, f"User '{username}' has been deleted.")
        return redirect('user_list')
    
    context = {
        'delete_user': user,
    }
    
    return render(request, 'core/user_delete.html', context)

@login_required
@admin_required
def mac_list(request):
    """
    List all MACs - Admin only
    """
    
    macs = MAC.objects.all().order_by('acronym')
    
    # Apply filters
    search = request.GET.get('search')
    status_filter = request.GET.get('status')
    
    if search:
        macs = macs.filter(
            Q(name__icontains=search) |
            Q(acronym__icontains=search)
        )
    
    if status_filter == 'active':
        macs = macs.filter(is_active=True)
    elif status_filter == 'inactive':
        macs = macs.filter(is_active=False)
    
    # Count stats
    mac_counts = {
        'all': MAC.objects.count(),
        'active': MAC.objects.filter(is_active=True).count(),
        'inactive': MAC.objects.filter(is_active=False).count(),
    }
    
    context = {
        'macs': macs,
        'mac_counts': mac_counts,
        'search_query': search,
        'current_status': status_filter,
    }
    
    return render(request, 'core/mac_list.html', context)


@login_required
@admin_required
def mac_create(request):
    """
    Create new MAC - Admin only
    """
    
    if request.method == 'POST':
        name = request.POST.get('name')
        acronym = request.POST.get('acronym')
        description = request.POST.get('description', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        is_active = request.POST.get('is_active') == 'on'
        
        # Validation
        errors = []
        
        if not name:
            errors.append("Name is required")
        elif MAC.objects.filter(name=name).exists():
            errors.append("MAC with this name already exists")
        
        if not acronym:
            errors.append("Acronym is required")
        elif MAC.objects.filter(acronym=acronym).exists():
            errors.append("MAC with this acronym already exists")
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Create MAC
            mac = MAC.objects.create(
                name=name,
                acronym=acronym,
                description=description,
                email=email,
                phone=phone,
                address=address,
                is_active=is_active
            )
            
            # Log activity
            log_activity(
                user=request.user,
                action='MAC_CREATED',
                description=f"Created MAC: {acronym} - {name}",
                request=request
            )
            
            messages.success(request, f"MAC '{acronym}' created successfully!")
            return redirect('mac_list')
    
    return render(request, 'core/mac_create.html')


@login_required
@admin_required
def mac_edit(request, pk):
    """
    Edit MAC - Admin only
    """
    
    mac = get_object_or_404(MAC, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        acronym = request.POST.get('acronym')
        description = request.POST.get('description', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        is_active = request.POST.get('is_active') == 'on'
        
        # Validation
        errors = []
        
        if not name:
            errors.append("Name is required")
        elif MAC.objects.filter(name=name).exclude(pk=pk).exists():
            errors.append("MAC with this name already exists")
        
        if not acronym:
            errors.append("Acronym is required")
        elif MAC.objects.filter(acronym=acronym).exclude(pk=pk).exists():
            errors.append("MAC with this acronym already exists")
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Update MAC
            mac.name = name
            mac.acronym = acronym
            mac.description = description
            mac.email = email
            mac.phone = phone
            mac.address = address
            mac.is_active = is_active
            mac.save()
            
            # Log activity
            log_activity(
                user=request.user,
                action='MAC_UPDATED',
                description=f"Updated MAC: {acronym}",
                request=request
            )
            
            messages.success(request, f"MAC '{acronym}' updated successfully!")
            return redirect('mac_list')
    
    context = {
        'mac': mac,
    }
    
    return render(request, 'core/mac_edit.html', context)


@login_required
@admin_required
def mac_delete(request, pk):
    """
    Delete MAC - Admin only
    Warning: This will affect all users and submissions
    """
    
    mac = get_object_or_404(MAC, pk=pk)
    
    # Check if MAC has users or submissions
    user_count = mac.users.count()
    submission_count = mac.submissions.count()
    
    if request.method == 'POST':
        acronym = mac.acronym
        
        # Log before deleting
        log_activity(
            user=request.user,
            action='MAC_UPDATED',
            description=f"Deleted MAC: {acronym} ({user_count} users, {submission_count} submissions)",
            request=request
        )
        
        mac.delete()
        
        messages.success(request, f"MAC '{acronym}' has been deleted.")
        return redirect('mac_list')
    
    context = {
        'mac': mac,
        'user_count': user_count,
        'submission_count': submission_count,
    }
    
    return render(request, 'core/mac_delete.html', context)

@login_required
def submission_edit(request, pk):
    """
    Edit existing submission
    Only allowed if:
    - User is the submitter
    - Status is PENDING or RETURNED
    - Or user is admin
    """
    
    submission = get_object_or_404(Submission, pk=pk)
    user = request.user
    
    # Check permissions
    if not submission.can_be_edited_by(user):
        messages.error(request, "You don't have permission to edit this submission.")
        return redirect('submission_detail', pk=pk)
    
    if request.method == 'POST':
        # Get form data
        title = request.POST.get('title')
        content_type = request.POST.get('content_type')
        description = request.POST.get('description')
        tags = request.POST.get('tags', '')
        is_confidential = request.POST.get('is_confidential') == 'on'
        file = request.FILES.get('file')  # Optional on edit
        
        # Validation
        errors = []
        if not title:
            errors.append("Title is required")
        if not description:
            errors.append("Description is required")
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Update submission
            submission.title = title
            submission.content_type = content_type
            submission.description = description
            submission.tags = tags
            submission.is_confidential = is_confidential
            
            # Update file if new one uploaded
            if file:
                submission.file = file
            
            # If status was RETURNED, change back to PENDING
            if submission.status == 'RETURNED':
                submission.status = 'PENDING'
            
            submission.save()
            
            # Log activity
            log_activity(
                user=user,
                action='SUBMISSION_UPDATED',
                submission=submission,
                description=f"Updated submission: {title}",
                request=request
            )
            
            messages.success(request, "Submission updated successfully!")
            return redirect('submission_detail', pk=pk)
    
    context = {
        'submission': submission,
        'is_edit': True,
    }
    
    return render(request, 'core/submission_edit.html', context)


@login_required
def submission_delete(request, pk):
    """
    Delete submission
    Only allowed if:
    - User is the submitter and status is PENDING
    - Or user is admin
    """
    
    submission = get_object_or_404(Submission, pk=pk)
    user = request.user
    
    # Check permissions
    can_delete = False
    if user.is_admin():
        can_delete = True
    elif submission.submitted_by == user and submission.status == 'PENDING':
        can_delete = True
    
    if not can_delete:
        messages.error(request, "You don't have permission to delete this submission.")
        return redirect('submission_detail', pk=pk)
    
    if request.method == 'POST':
        title = submission.title
        mac_name = submission.mac.acronym
        
        # Log before deleting
        log_activity(
            user=user,
            action='SUBMISSION_UPDATED',  # We don't have DELETE action yet
            submission=None,
            description=f"Deleted submission: {title} from {mac_name}",
            request=request
        )
        
        # Delete the submission
        submission.delete()
        
        messages.success(request, f"Submission '{title}' has been deleted.")
        return redirect('submission_list')
    
    # GET request - show confirmation page
    context = {
        'submission': submission,
    }
    
    return render(request, 'core/submission_delete.html', context)

@login_required
@micat_reviewer_required
def submission_review(request, pk):
    """
    Review and approve/deny/return submission
    MICAT reviewers only
    """
    
    submission = get_object_or_404(Submission, pk=pk)
    user = request.user
    
    if request.method == 'POST':
        action = request.POST.get('action')
        comments = request.POST.get('reviewer_comments', '')
        priority = request.POST.get('priority', 'MEDIUM')
        
        # Update reviewer
        submission.reviewed_by = user
        submission.reviewed_at = timezone.now()
        submission.reviewer_comments = comments
        submission.priority = priority
        
        if action == 'approve':
            submission.status = 'APPROVED'
            submission.approved_at = timezone.now()
            submission.is_published = request.POST.get('publish') == 'on'
            if submission.is_published:
                submission.published_at = timezone.now()
            
            # Log activity
            log_activity(
                user=user,
                action='SUBMISSION_APPROVED',
                submission=submission,
                description=f"Approved submission: {submission.title}",
                request=request
            )
            
            # Notify submitter
            if submission.submitted_by:
                create_notification(
                    user=submission.submitted_by,
                    title="Submission Approved! 🎉",
                    message=f"Your submission '{submission.title}' has been approved and published.",
                    submission=submission
                )
            
            messages.success(request, "Submission approved successfully!")
            
        elif action == 'return':
            submission.status = 'RETURNED'
            
            # Log activity
            log_activity(
                user=user,
                action='SUBMISSION_RETURNED',
                submission=submission,
                description=f"Returned submission for edits: {submission.title}",
                request=request
            )
            
            # Notify submitter
            if submission.submitted_by:
                create_notification(
                    user=submission.submitted_by,
                    title="Submission Returned for Edits",
                    message=f"Please review and update your submission '{submission.title}'. Comments: {comments}",
                    submission=submission
                )
            
            messages.info(request, "Submission returned for edits.")
            
        elif action == 'deny':
            submission.status = 'DENIED'
            submission.denial_reason = request.POST.get('denial_reason', '')
            
            # Log activity
            log_activity(
                user=user,
                action='SUBMISSION_DENIED',
                submission=submission,
                description=f"Denied submission: {submission.title}",
                request=request
            )
            
            # Notify submitter
            if submission.submitted_by:
                create_notification(
                    user=submission.submitted_by,
                    title="Submission Denied",
                    message=f"Your submission '{submission.title}' has been denied. Reason: {submission.denial_reason}",
                    submission=submission
                )
            
            messages.warning(request, "Submission denied.")
        
        submission.save()
        return redirect('submission_detail', pk=pk)
    
    # Process tags for display
    tag_list = []
    if submission.tags:
        tag_list = [tag.strip() for tag in submission.tags.split(',') if tag.strip()]
    
    context = {
        'submission': submission,
        'tag_list': tag_list,  # Add processed tags
    }
    
    return render(request, 'core/submission_review.html', context)


@login_required
@admin_required
def analytics(request):
    """
    Advanced analytics dashboard - Admin only
    Shows system-wide statistics and trends
    """
    
    # Time period filter
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # Overall statistics
    total_stats = {
        'users': User.objects.filter(is_active=True).count(),
        'macs': MAC.objects.filter(is_active=True).count(),
        'submissions': Submission.objects.count(),
        'approved': Submission.objects.filter(status='APPROVED').count(),
        'pending': Submission.objects.filter(status='PENDING').count(),
        'denied': Submission.objects.filter(status='DENIED').count(),
    }
    
    # Calculate approval rate
    total_reviewed = Submission.objects.filter(
        status__in=['APPROVED', 'DENIED']
    ).count()
    
    if total_reviewed > 0:
        total_stats['approval_rate'] = round(
            (total_stats['approved'] / total_reviewed) * 100, 1
        )
    else:
        total_stats['approval_rate'] = 0
    
    # Submissions by MAC
    submissions_by_mac = MAC.objects.annotate(
        total=Count('submissions'),
        approved=Count('submissions', filter=Q(submissions__status='APPROVED')),
        pending=Count('submissions', filter=Q(submissions__status='PENDING'))
    ).order_by('-total')[:10]
    
    # Submissions by status
    submissions_by_status = Submission.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Submissions trend (last N days)
    submissions_trend = Submission.objects.filter(
        submitted_at__gte=start_date
    ).annotate(
        date=TruncDate('submitted_at')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Top submitters
    top_submitters = User.objects.filter(
        role='MAC_OFFICER'
    ).annotate(
        submission_count=Count('submissions')
    ).order_by('-submission_count')[:10]
    
    # Top reviewers
    top_reviewers = User.objects.filter(
        role='MICAT_REVIEWER'
    ).annotate(
        review_count=Count('reviewed_submissions')
    ).order_by('-review_count')[:10]
    
    # Recent activity summary
    recent_submissions = Submission.objects.filter(
        submitted_at__gte=start_date
    ).count()
    
    recent_approvals = Submission.objects.filter(
        approved_at__gte=start_date
    ).count()
    
    # Content type distribution
    content_types = Submission.objects.values('content_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    context = {
        'total_stats': total_stats,
        'submissions_by_mac': submissions_by_mac,
        'submissions_by_status': submissions_by_status,
        'submissions_trend': submissions_trend,
        'top_submitters': top_submitters,
        'top_reviewers': top_reviewers,
        'content_types': content_types,
        'recent_submissions': recent_submissions,
        'recent_approvals': recent_approvals,
        'days': days,
    }
    
    return render(request, 'core/analytics.html', context)


@login_required
def export_submissions(request):
    """
    Export submissions to CSV
    """
    import csv
    from django.http import HttpResponse
    
    # Get filters
    status = request.GET.get('status')
    mac_id = request.GET.get('mac')
    
    # Build queryset
    submissions = Submission.objects.all()
    
    if status:
        submissions = submissions.filter(status=status)
    
    if mac_id:
        submissions = submissions.filter(mac_id=mac_id)
    
    # Only show user's MAC submissions for MAC officers
    if request.user.is_mac_officer():
        submissions = submissions.filter(mac=request.user.mac)
    
    submissions = submissions.order_by('-submitted_at')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="submissions_export.csv"'
    
    writer = csv.writer(response)
    
    # Header row
    writer.writerow([
        'ID', 'Title', 'MAC', 'Content Type', 'Status', 
        'Submitted By', 'Submitted At', 'Reviewed By', 
        'Reviewed At', 'Tags'
    ])
    
    # Data rows
    for sub in submissions:
        writer.writerow([
            sub.id,
            sub.title,
            sub.mac.acronym,
            sub.get_content_type_display(),
            sub.get_status_display(),
            sub.submitted_by.get_full_name() if sub.submitted_by else 'N/A',
            sub.submitted_at.strftime('%Y-%m-%d %H:%M'),
            sub.reviewed_by.get_full_name() if sub.reviewed_by else 'N/A',
            sub.reviewed_at.strftime('%Y-%m-%d %H:%M') if sub.reviewed_at else 'N/A',
            sub.tags
        ])
    
    return response