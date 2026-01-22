"""
PANDORA BOX - Custom Template Filters
================================
Custom filters for use in Django templates

HOW TO USE:
1. Create this file: core/templatetags/custom_filters.py
2. Create __init__.py in templatetags folder
3. In template: {% load custom_filters %}
4. Use: {{ value|filter_name }}
"""

from django import template

register = template.Library()


@register.filter
def split_tags(value, delimiter=','):
    """
    Split a string and return list of stripped items
    
    Usage: {% for tag in submission.tags|split_tags %}
    
    Args:
        value: String to split (e.g., "health, covid, vaccine")
        delimiter: Character to split on (default: comma)
    
    Returns:
        List of stripped strings
    """
    if not value:
        return []
    
    return [item.strip() for item in value.split(delimiter) if item.strip()]


@register.filter
def get_item(dictionary, key):
    """
    Get item from dictionary
    
    Usage: {{ mydict|get_item:key }}
    
    Useful when you can't use mydict.key syntax
    """
    return dictionary.get(key)


@register.filter
def multiply(value, arg):
    """
    Multiply value by arg
    
    Usage: {{ price|multiply:quantity }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """
    Calculate percentage
    
    Usage: {{ count|percentage:total }}
    Returns: "45.2%"
    """
    try:
        if float(total) == 0:
            return "0%"
        return f"{(float(value) / float(total) * 100):.1f}%"
    except (ValueError, TypeError, ZeroDivisionError):
        return "0%"


@register.filter
def days_ago(date_value):
    """
    Return how many days ago a date was
    
    Usage: {{ submission.created_at|days_ago }}
    Returns: "3 days ago" or "Today" or "Yesterday"
    """
    from django.utils import timezone
    from datetime import timedelta
    
    if not date_value:
        return ""
    
    now = timezone.now()
    
    # Make both timezone-aware or both naive
    if timezone.is_aware(date_value) and not timezone.is_aware(now):
        now = timezone.make_aware(now)
    elif not timezone.is_aware(date_value) and timezone.is_aware(now):
        date_value = timezone.make_aware(date_value)
    
    diff = now - date_value
    
    if diff.days == 0:
        return "Today"
    elif diff.days == 1:
        return "Yesterday"
    elif diff.days < 7:
        return f"{diff.days} days ago"
    elif diff.days < 30:
        weeks = diff.days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif diff.days < 365:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"


@register.filter
def file_size_mb(size_bytes):
    """
    Convert bytes to MB
    
    Usage: {{ file.size|file_size_mb }}
    Returns: "2.5 MB"
    """
    try:
        mb = float(size_bytes) / (1024 * 1024)
        return f"{mb:.2f} MB"
    except (ValueError, TypeError):
        return "0 MB"