"""
PANDORA BOX - Database Models
================================
This file defines the database structure.

WHAT ARE MODELS?
Models are Python classes that represent database tables.
Each model = one table. Each attribute = one column.

WHY THIS STRUCTURE?
- User: Stores login info + role
- MAC: Government agencies (Ministry, Agency, Commission)
- Submission: Content uploaded by MAC officers
- Comment: Feedback from MICAT reviewers
- ActivityLog: Audit trail of all actions
- Notification: In-app alerts for users
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.utils import timezone
import os


# ============================================
# USER MODEL
# ============================================
class User(AbstractUser):
    """
    Custom User Model extending Django's built-in User
    
    Why extend? We need extra fields:
    - role: What can they do?
    - mac: Which agency do they belong to?
    - phone: Contact information
    
    ROLES:
    - MAC_OFFICER: Can submit content
    - MICAT_REVIEWER: Can review and approve
    - ADMIN: Full system access
    """
    
    ROLE_CHOICES = [
        ('MAC_OFFICER', 'MAC PR Officer'),
        ('MICAT_REVIEWER', 'MICAT Reviewer/Editor'),
        ('ADMIN', 'System Administrator'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='MAC_OFFICER',
        help_text="User's role in the system"
    )
    
    mac = models.ForeignKey(
        'MAC',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text="Which MAC this user belongs to"
    )
    
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Contact phone number"
    )
    
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        null=True,
        blank=True
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Can this user log in?"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['username']
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    def get_mac_name(self):
        """Get the name of user's MAC"""
        return self.mac.name if self.mac else "N/A"
    
    def is_mac_officer(self):
        return self.role == 'MAC_OFFICER'
    
    def is_micat_reviewer(self):
        return self.role == 'MICAT_REVIEWER'
    
    def is_admin(self):
        return self.role == 'ADMIN'


# ============================================
# MAC MODEL (Ministries, Agencies, Commissions)
# ============================================
class MAC(models.Model):
    """
    Government Agencies
    
    Each MAC has:
    - Official name and acronym
    - Contact information
    - Logo
    - Active status
    """
    
    name = models.CharField(
        max_length=200,
        unique=True,
        help_text="Full name of the Ministry/Agency/Commission"
    )
    
    acronym = models.CharField(
        max_length=20,
        unique=True,
        help_text="Short name (e.g., MICAT, MOH, MOE)"
    )
    
    description = models.TextField(
        blank=True,
        help_text="What this MAC does"
    )
    
    email = models.EmailField(
        blank=True,
        help_text="Official contact email"
    )
    
    phone = models.CharField(
        max_length=20,
        blank=True
    )
    
    address = models.TextField(blank=True)
    
    logo = models.ImageField(
        upload_to='mac_logos/',
        null=True,
        blank=True
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Is this MAC currently active?"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['acronym']
        verbose_name = 'MAC'
        verbose_name_plural = 'MACs'
    
    def __str__(self):
        return f"{self.acronym} - {self.name}"
    
    def get_total_submissions(self):
        """Count all submissions from this MAC"""
        return self.submissions.count()
    
    def get_pending_submissions(self):
        """Count pending submissions"""
        return self.submissions.filter(status='PENDING').count()


# ============================================
# SUBMISSION MODEL
# ============================================
class Submission(models.Model):
    """
    Content submitted by MAC officers
    
    WORKFLOW:
    1. MAC officer uploads → PENDING
    2. MICAT reviews → UNDER_REVIEW
    3. MICAT decides → APPROVED/DENIED/RETURNED
    4. If approved → published to library
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('UNDER_REVIEW', 'Under Review'),
        ('APPROVED', 'Approved'),
        ('DENIED', 'Denied'),
        ('RETURNED', 'Returned for Edits'),
    ]
    
    CONTENT_TYPE_CHOICES = [
        ('PRESS_RELEASE', 'Press Release'),
        ('ANNOUNCEMENT', 'Announcement'),
        ('SPEECH', 'Speech'),
        ('PHOTO', 'Photo'),
        ('VIDEO', 'Video'),
        ('DOCUMENT', 'Document'),
        ('OTHER', 'Other'),
    ]
    
    # Basic Information
    title = models.CharField(
        max_length=300,
        help_text="Title of the content"
    )
    
    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPE_CHOICES,
        default='PRESS_RELEASE'
    )
    
    description = models.TextField(
        help_text="Summary or description of the content"
    )
    
    tags = models.CharField(
        max_length=500,
        blank=True,
        help_text="Keywords separated by commas (e.g., health, covid, vaccine)"
    )
    
    # File Upload
    file = models.FileField(
        upload_to='submissions/%Y/%m/',
        validators=[FileExtensionValidator(
            allowed_extensions=['pdf', 'doc', 'docx', 'txt', 
                              'jpg', 'jpeg', 'png', 'gif',
                              'mp4', 'avi', 'mov', 'xlsx', 'xls']
        )],
        help_text="Upload the content file"
    )
    
    # Relationships
    mac = models.ForeignKey(
        MAC,
        on_delete=models.CASCADE,
        related_name='submissions',
        help_text="Which MAC submitted this"
    )
    
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='submissions',
        help_text="Which officer submitted this"
    )
    
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_submissions',
        help_text="MICAT reviewer assigned"
    )
    
    # Status and Workflow
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    
    is_confidential = models.BooleanField(
        default=False,
        help_text="Is this content confidential?"
    )
    
    is_published = models.BooleanField(
        default=False,
        help_text="Is this visible in the public library?"
    )
    
    priority = models.CharField(
        max_length=20,
        choices=[
            ('LOW', 'Low'),
            ('MEDIUM', 'Medium'),
            ('HIGH', 'High'),
            ('URGENT', 'Urgent'),
        ],
        default='MEDIUM',
        blank=True
    )
    
    # Feedback
    reviewer_comments = models.TextField(
        blank=True,
        help_text="Comments from MICAT reviewer"
    )
    
    denial_reason = models.TextField(
        blank=True,
        help_text="Reason if denied"
    )
    
    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Submission'
        verbose_name_plural = 'Submissions'
        indexes = [
            models.Index(fields=['status', '-submitted_at']),
            models.Index(fields=['mac', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.mac.acronym} ({self.status})"
    
    def get_file_extension(self):
        """Get file extension"""
        return os.path.splitext(self.file.name)[1][1:].upper()
    
    def get_file_size(self):
        """Get file size in MB"""
        if self.file:
            return round(self.file.size / (1024 * 1024), 2)
        return 0
    
    def get_status_color(self):
        """Return color code for status badge"""
        colors = {
            'PENDING': 'orange',
            'UNDER_REVIEW': 'amber',
            'APPROVED': 'green',
            'DENIED': 'red',
            'RETURNED': 'blue',
        }
        return colors.get(self.status, 'gray')
    
    def can_be_edited_by(self, user):
        """Check if user can edit this submission"""
        if user.is_admin():
            return True
        if user.is_mac_officer() and self.submitted_by == user:
            return self.status in ['PENDING', 'RETURNED']
        return False


# ============================================
# COMMENT MODEL
# ============================================
class Comment(models.Model):
    """
    Comments and feedback on submissions
    Used for communication between MAC officers and MICAT reviewers
    """
    
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    
    text = models.TextField()
    
    is_internal = models.BooleanField(
        default=False,
        help_text="Internal notes (not visible to MAC officer)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment by {self.user.username} on {self.submission.title}"


# ============================================
# ACTIVITY LOG MODEL
# ============================================
class ActivityLog(models.Model):
    """
    Audit trail of all actions in the system
    WHO did WHAT and WHEN
    """
    
    ACTION_CHOICES = [
        ('SUBMISSION_CREATED', 'Submission Created'),
        ('SUBMISSION_UPDATED', 'Submission Updated'),
        ('SUBMISSION_REVIEWED', 'Submission Reviewed'),
        ('SUBMISSION_APPROVED', 'Submission Approved'),
        ('SUBMISSION_DENIED', 'Submission Denied'),
        ('SUBMISSION_RETURNED', 'Submission Returned for Edits'),
        ('SUBMISSION_PUBLISHED', 'Submission Published'),
        ('COMMENT_ADDED', 'Comment Added'),
        ('USER_LOGIN', 'User Logged In'),
        ('USER_CREATED', 'User Created'),
        ('USER_UPDATED', 'User Updated'),
        ('MAC_CREATED', 'MAC Created'),
        ('MAC_UPDATED', 'MAC Updated'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activity_logs'
    )
    
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES
    )
    
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activity_logs'
    )
    
    description = models.TextField(
        help_text="Details of what happened"
    )
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
    
    def __str__(self):
        return f"{self.user} - {self.get_action_display()} at {self.created_at}"


# ============================================
# NOTIFICATION MODEL
# ============================================
class Notification(models.Model):
    """
    In-app notifications for users
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    is_read = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"
