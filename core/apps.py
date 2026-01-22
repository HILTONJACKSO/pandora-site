"""
PANDORA BOX - App Configuration
================================
This file configures the core app
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """
    Configuration for the core app
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Pandora Box Core'
    
    def ready(self):
        """
        This runs when Django starts
        Good place for:
        - Importing signals
        - Registering system checks
        - Starting background tasks
        
        We'll use this later for signals
        """
        pass
