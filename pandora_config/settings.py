"""
PANDORA BOX - Django Settings
================================
This file configures the entire Django project.

KEY CONCEPTS:
- INSTALLED_APPS: Tells Django what apps to use
- MIDDLEWARE: Security and session management
- TEMPLATES: How Django renders HTML
- DATABASES: Connection to PostgreSQL
- STATIC/MEDIA: File handling for CSS and uploads
"""

# import os
# import dj_database_url
# from pathlib import Path
# from decouple import config

from pathlib import Path
from decouple import config

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# We use python-decouple to keep secrets in .env file
SECRET_KEY = config('SECRET_KEY', default='your-secret-key-here-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)
# DEBUG = os.environ.get('RENDER') != 'true'

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')
# ALLOWED_HOSTS
# ALLOWED_HOSTS = [
#     'localhost',
#     '127.0.0.1',
#     '.onrender.com',  # Allow all Render domains
# ]

# For production, you can be more specific:
# ALLOWED_HOSTS = ['pandora-box.onrender.com', 'pandorabox.gov.lr']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',        # Django's built-in admin panel
    'django.contrib.auth',          # User authentication system
    'django.contrib.contenttypes',  # Content type system
    'django.contrib.sessions',      # Session management
    'django.contrib.messages',      # Messaging framework
    'django.contrib.staticfiles',   # Static files (CSS, JS, images)
    'core',                         # Our main app
]

# MIDDLEWARE: Request/Response processing
# These run on every request in order
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # 'whitenoise.middleware.WhiteNoiseMiddleware',  # new for static files
    'django.contrib.sessions.middleware.SessionMiddleware',  # Manages user sessions
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',            # Security against CSRF attacks
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Adds user to request
    'django.contrib.messages.middleware.MessageMiddleware',  # Flash messages
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'pandora_config.urls'

# TEMPLATES: How Django renders HTML
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Where to find HTML templates
        'APP_DIRS': True,  # Look in each app's templates folder
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',  # Adds 'request' to templates
                'django.contrib.auth.context_processors.auth',  # Adds 'user' to templates
                'django.contrib.messages.context_processors.messages',
                 'core.context_processors.notifications_context',# Adds 'messages'
            ],
        },
    },
]

WSGI_APPLICATION = 'pandora_config.wsgi.application'

# DATABASE: PostgreSQL Configuration
# Why PostgreSQL? Better for production, handles multiple users, reliable
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='pandora_box'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='postgres'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Database Configuration
# if 'DATABASE_URL' in os.environ:
#     # Production (Render)
#     DATABASES = {
#         'default': dj_database_url.config(
#             default=os.environ.get('DATABASE_URL'),
#             conn_max_age=600
#         )
#     }
# else:
#     # Development (Local)
#     DATABASES = {
#         'default': {
#             'ENGINE': 'django.db.backends.postgresql',
#             'NAME': config('DB_NAME', default='pandora_box'),
#             'USER': config('DB_USER', default='postgres'),
#             'PASSWORD': config('DB_PASSWORD', default='postgres'),
#             'HOST': config('DB_HOST', default='localhost'),
#             'PORT': config('DB_PORT', default='5432'),
#         }
#     }








# Custom User Model - We'll create this next
# Why? We need extra fields like role and MAC assignment
AUTH_USER_MODEL = 'core.User'

# Password validation
# Makes sure users create strong passwords
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8}
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Monrovia'  # Liberia timezone
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# STATIC_URL: URL prefix for static files in templates
# STATIC_ROOT: Where collectstatic puts all static files for deployment
# STATICFILES_DIRS: Additional locations for static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (User uploads)
# These are files users upload (documents, images, videos)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login/Logout URLs
# Where to redirect after login/logout
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# Email Configuration (for notifications)
# We'll use console backend for development (prints to terminal)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# For production, you'll use SMTP:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = config('EMAIL_HOST_USER')
# EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')

# File Upload Settings
# Maximum file size: 50MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB in bytes
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800

# Allowed file types for security
ALLOWED_FILE_EXTENSIONS = [
    'pdf', 'doc', 'docx', 'txt',
    'jpg', 'jpeg', 'png', 'gif',
    'mp4', 'avi', 'mov',
    'xlsx', 'xls', 'ppt', 'pptx'
]

# Session settings
# How long before user needs to login again (2 weeks)
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds
SESSION_SAVE_EVERY_REQUEST = True  # Refresh session on every request

# Email Backend Configuration
# For development (prints to console)
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    # For production (real emails)
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@pandorabox.gov.lr')
    SERVER_EMAIL = config('SERVER_EMAIL', default='admin@pandorabox.gov.lr')

# Email notification settings
EMAIL_SUBJECT_PREFIX = '[Pandora Box] '
ADMINS = [
    ('Admin', config('ADMIN_EMAIL', default='admin@pandorabox.gov.lr')),
]
MANAGERS = ADMINS

# # CSRF Settings for Render
# CSRF_TRUSTED_ORIGINS = [
#     'https://*.onrender.com',
# ]
