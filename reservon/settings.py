# reservon/settings.py

from pathlib import Path
from django.utils.translation import gettext_lazy as _
import os
import environ
import dj_database_url
import sys

env = environ.Env(
    DEBUG=(bool, False)
)

BASE_DIR = Path(__file__).resolve().parent.parent

environ.Env.read_env(env_file=os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

INSTALLED_APPS = [
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
    'storages',
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

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / "main/static/",
    BASE_DIR / "salons/static/",
    BASE_DIR / "authentication/static/",
]

if DEBUG:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
else:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

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
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.{env("CLOUDFLARE_R2_ACCOUNT_ID")}.r2.cloudflarestorage.com'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    AWS_DEFAULT_ACL = None

    # Дополнительные настройки для совместимости с Cloudflare R2
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_S3_ADDRESSING_STYLE = 'virtual'  # Попробуйте 'path' если 'virtual' не работает
    AWS_QUERYSTRING_AUTH = False  # Для публичного доступа без подписей
    AWS_S3_VERIFY = True 

    # DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    DEFAULT_FILE_STORAGE = 'reservon.custom_storages.MediaStorage' 

    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
    
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

import sys

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

if DEBUG:
    SESSION_COOKIE_SAMESITE = 'Strict'
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
else:
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_DOMAIN = 'reservon.am'
    CSRF_COOKIE_SECURE = True
    CSRF_TRUSTED_ORIGINS = ['https://reservon.am', 'https://www.reservon.am']
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 3600

SOCIALACCOUNT_LOGIN_ON_GET = True
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "optional"  # или " mandatory", в зависимости требований

SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_ADAPTER = 'authentication.adapters.MySocialAccountAdapter'

if DEBUG:
    ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'http'
else:
    ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

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

# Добавьте настройки Celery
CELERY_WORKER_POOL = 'solo'
CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

WEBPUSH_SETTINGS = {
    "VAPID_PUBLIC_KEY": "BFTnI0-japfr3vyHgVnVWcX3OY4ErYXVrNhY9Xxe1KmJ_qXfUspPGxjX7gbg3XJ21BpktlYiPfouzwYjRWRi2A8",
    "VAPID_PRIVATE_KEY": """
-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgvNdm62CO8dVwbN2C
KyF5ReXThL3jdiq7wwIdZt1cVcChRANCAARU5yNPo2qX6978h4FZ1VnF9zmOBK2F
1azYWPV8XtSpif6l31LKTxsY1+4G4N1ydtQaZLZWIj36Ls8GI0VkYtgP
-----END PRIVATE KEY-----
""",
    "VAPID_ADMIN_EMAIL": "tsigma.team@gmail.com"
}
