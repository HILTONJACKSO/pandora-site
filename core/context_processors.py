"""
PANDORA BOX - Context Processors
================================
These functions add variables to ALL templates automatically.

WHAT IS A CONTEXT PROCESSOR?
It's a function that runs for every request and adds data to the template context.
This means you don't have to pass 'unread_count' manually in every view.

WHY USE THIS?
- DRY (Don't Repeat Yourself)
- Unread notification count is needed on every page
- Makes templates cleaner
"""

from .models import Notification


def notifications_context(request):
    """
    Add notification count to all templates
    
    This runs on EVERY request and adds 'unread_count' to the template context.
    Now any template can use {{ unread_count }} without explicitly passing it.
    """
    
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
    else:
        unread_count = 0
    
    return {
        'unread_count': unread_count
    }