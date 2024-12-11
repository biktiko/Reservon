# reservon/settings.py

from pathlib import Path
from django.utils.translation import gettext_lazy as _
import os
import environ
import dj_database_url
import sys

# Initialize django-environ
env = environ.Env(
    DEBUG=(bool, False)
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Read the .env file
environ.Env.read_env(env_file=os.path.join(BASE_DIR, '.env'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')  # Moved to .env

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

# Application definition

INSTALLED_APPS = [
    # 'suit',
    'grappelli',
    'colorfield',
    'import_export',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_json_widget',
    'crispy_forms',
    'crispy_bootstrap4',
    'rest_framework',
    'storages',
    'authentication',
    'main',
    'salons.apps.SalonsConfig',
    'account',
]

CRISPY_TEMPLATE_PACK = 'bootstrap4'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware', 
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'reservon.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # You can add template directories here if needed
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',  # Required for some Django features
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
            ],
        },
    },
]

# JSON Editor Settings (если используете)
JSON_EDITOR_JS = [
    'https://cdnjs.cloudflare.com/ajax/libs/jsoneditor/9.5.6/jsoneditor.min.js',
]

JSON_EDITOR_CSS = [
    'https://cdnjs.cloudflare.com/ajax/libs/jsoneditor/9.5.6/jsoneditor.min.css',
]

GRAPPELLI_ADMIN_TITLE = "Reservon Admin"

WSGI_APPLICATION = 'reservon.wsgi.application'

DATABASES = {
    'default': dj_database_url.config(default='sqlite:///db.sqlite3')
}

LOGOUT_REDIRECT_URL = '/'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

USE_I18N = True
USE_L10N = True
USE_TZ = True
TIME_ZONE = 'UTC'

LANGUAGE_CODE = 'en'

# AUTH_USER_MODEL = 'authentication.CustomUser'

LANGUAGES = [
    ('en', _('English')),
    ('ru', _('Russian')),
    ('hy', _('Armenian')),
]

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

DATE_FORMAT = _('j E')
TIME_FORMAT = _('H:i')

SHORT_DATE_FORMAT = DATE_FORMAT
SHORT_TIME_FORMAT = TIME_FORMAT

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / "main/static/",
    BASE_DIR / "salons/static/",
    BASE_DIR / "authentication/static/",
]

# Media files (Uploaded by users)
# Медиа-файлы
if DEBUG:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
else:
    # Настройки Cloudflare R2
    
    AWS_ACCESS_KEY_ID = env('CLOUDFLARE_R2_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = env('CLOUDFLARE_R2_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = env('CLOUDFLARE_R2_BUCKET_NAME')
    AWS_S3_REGION_NAME = 'auto'
    AWS_S3_ENDPOINT_URL = f'https://{env("CLOUDFLARE_R2_ACCOUNT_ID")}.r2.cloudflarestorage.com'
    # AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.{env("CLOUDFLARE_R2_ACCOUNT_ID")}.r2.cloudflarestorage.com'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    AWS_DEFAULT_ACL = None

    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_S3_CUSTOM_DOMAIN = env('AWS_S3_CUSTOM_DOMAIN')
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Twilio Settings
TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = env('TWILIO_AUTH_TOKEN')
TWILIO_VERIFY_SERVICE_SID = env('TWILIO_VERIFY_SERVICE_SID')

ALLOWED_HOSTS = [
    'www.reservon.am', 
    'reservon.am', 
    'staging-reservon.am', 
    'reservon-8b5da3853ffa.herokuapp.com', 
    'localhost', 
    '127.0.0.1'
    ]

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {  # Используем консоль для логов
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {  # Логгер для Django
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'booking': {  # кастомный логгер
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Настройки django-admin-interface
ADMIN_INTERFACE = {
    'HEADER': 'Reservon Admin',
    'TITLE': 'Reservon Administration',
    'SHOW_THEMES': True,  # Включает возможность смены тем
}

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


LOGGING['handlers']['console'] = {
    'level': 'DEBUG',
    'class': 'logging.StreamHandler',
    'stream': sys.stdout,
}

LOGGING['root'] = {
    'handlers': ['console'],
    'level': 'INFO',
}

if DEBUG:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
else:
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_DOMAIN = 'reservon.am'
    CSRF_COOKIE_SECURE = True
    CSRF_TRUSTED_ORIGINS = ['https://reservon.am', 'https://www.reservon.am']
