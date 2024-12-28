# C:\Reservon\Reservon\reservon\settings_staging.py
from pathlib import Path
from django.utils.translation import gettext_lazy as _
import os
import environ
import dj_database_url
import sys
import ssl

env = environ.Env(
    DEBUG=(bool, False)
)
DEBUG = True
BASE_DIR = Path(__file__).resolve().parent.parent

environ.Env.read_env(env_file=os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

INSTALLED_APPS = [
    'storages',
    'grappelli',
    'colorfield',
    'import_export',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sites', 
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_json_widget',
    'crispy_forms',
    'crispy_bootstrap4',
    'rest_framework',
    'webpush',
    'authentication',
    'main',
    'user_account.apps.UserAccountConfig',
    'salons',
    'debug_toolbar'
]

DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.history.HistoryPanel',
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.alerts.AlertsPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
    'debug_toolbar.panels.profiling.ProfilingPanel',
]

SITE_ID = 1

CRISPY_TEMPLATE_PACK = 'bootstrap4'

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)


LOGIN_REDIRECT_URL = '/salons'
LOGOUT_REDIRECT_URL = '/'

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
    'allauth.account.middleware.AccountMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
] 

INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
] + [ip.strip() for ip in os.environ.get('INTERNAL_IPS', '').split(',')]

ROOT_URLCONF = 'reservon.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'reservon', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
            ],
        },
    },
]

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
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    BASE_DIR / "main/static/",
    BASE_DIR / "salons/static/",
    BASE_DIR / "authentication/static/",
]
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Twilio Settings
TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = env('TWILIO_AUTH_TOKEN')
TWILIO_VERIFY_SERVICE_SID = env('TWILIO_VERIFY_SERVICE_SID')

ALLOWED_HOSTS = [
    'staging-reservon.am',
    'www.staging-reservon.am',
    'reservon-staging.herokuapp.com',
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {  
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'verbose',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'allauth': {
            'handlers': ['console', 'file'], 
            'level': 'DEBUG',
            'propagate': False,
        },
        'booking': {
            'handlers': ['console', 'file'], 
            'level': 'DEBUG',
            'propagate': False,
        },
        'main': {
            'handlers': ['console', 'file'], 
            'level': 'DEBUG',
            'propagate': False,
        },
        'authentication.adapters': {
            'handlers': ['console', 'file'], 
            'level': 'DEBUG',
            'propagate': False,
        },
        'boto3': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'botocore': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'django_storages': {
            'handlers': ['console'],
            'level': 'DEBUG',
        }
    },
    'root': {
        'handlers': ['console', 'file'], 
        'level': 'DEBUG',
    },
}

LOGGING['handlers']['console'] = {
    'level': 'INFO',
    'class': 'logging.StreamHandler',
    'stream': sys.stderr,
}

LOGGING['root'] = {
    'handlers': ['console', 'file'],
    'level': 'DEBUG',
}

LOGGING['loggers']['allauth'] = {
    'handlers': ['console', 'file'],
    'level': 'DEBUG',
    'propagate': False,
}

ADMIN_INTERFACE = {
    'HEADER': 'Reservon Admin',
    'TITLE': 'Reservon Administration',
    'SHOW_THEMES': True,
}

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Сохранять сессии в базе данных


SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

SOCIALACCOUNT_LOGIN_ON_GET = True
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "optional"  # или " mandatory", в зависимости требований

SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_ADAPTER = 'authentication.adapters.MySocialAccountAdapter'

ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'http'

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'LOGIN_ON_GET': True, 
    }
}
TEMPLATES[0]['OPTIONS']['debug'] = True

if DEBUG:
    CELERY_BROKER_URL = 'redis://redis:6379/0'
    CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
else:
    CELERY_BROKER_URL = os.environ.get('REDIS_URL')
    CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL')

CELERY_WORKER_POOL = 'solo'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'


WEBPUSH_SETTINGS = {
    "VAPID_PUBLIC_KEY": "BP-1Jkn85ndvrY2m0_F2KArCKEBmw0vPp9BjPPjreL-WORMW3GUjTLPbQ1teQT5A_-sgu2Lfn59Gtb5S69X_Dho",
    "VAPID_PRIVATE_KEY": "j5YA554oR44NkEYgXQ00f5mcNcHZyfw27BElPdNRXxQ",
    "VAPID_ADMIN_EMAIL": "tsigma.team@gmail.com"
}

BROKER_USE_SSL = {
    'ssl_cert_reqs': ssl.CERT_NONE
}
RESULT_BACKEND_USE_SSL = {
    'ssl_cert_reqs': ssl.CERT_NONE
}

CELERY_BROKER_USE_SSL = BROKER_USE_SSL
CELERY_REDIS_BACKEND_USE_SSL = RESULT_BACKEND_USE_SSL