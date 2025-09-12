from pathlib import Path
import os
from os import getenv
from dotenv import load_dotenv
import warnings
from django.urls import reverse_lazy

# Figure out which environment we're in
ENVIRONMENT = os.getenv("ENVIRONMENT", "local").lower()


IS_LOCAL = ENVIRONMENT == "local"
IS_STAGING = ENVIRONMENT == "staging"
IS_PROD = ENVIRONMENT == "production"
IS_LIVE = ENVIRONMENT in ("staging", "production")  # HTTPS on both


# Load the appropriate .env file based on the environment
if ENVIRONMENT == "local":
    load_dotenv(".env.local")
elif ENVIRONMENT == "staging":
    load_dotenv(".env.staging")
else:
    load_dotenv(".env.production")

DB_NAME = os.environ.get('DB_NAME')
DB_USERNAME = os.environ.get('DB_USERNAME')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': DB_NAME,
        'USER': DB_USERNAME,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
    }
}

# Amazon SES configuration
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND')
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_SES_REGION_NAME = os.environ.get('AWS_SES_REGION_NAME')
AWS_SES_REGION_ENDPOINT = os.environ.get('AWS_SES_REGION_ENDPOINT')
DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL', 'Omnivore Arts <oliver@omnivorearts.com>')
SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000")

# Celery configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

# Good defaults
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_TIME_LIMIT = 30
CELERY_TASK_SOFT_TIME_LIMIT = 25
CELERY_TASK_ROUTES = {
    "main.tasks.send_like_email_task": {"queue": "emails"},
    "main.tasks.send_comment_email_task": {"queue": "emails"},
    "main.tasks.send_shared_art_email_task": {"queue": "emails"},
}

# During first local test you can force inline execution:
# CELERY_TASK_ALWAYS_EAGER = True


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = (os.getenv("DEBUG", "False").lower() == "true") if IS_LOCAL else False

# Security flags – on for staging & production
SECURE_SSL_REDIRECT = IS_LIVE
SESSION_COOKIE_SECURE = IS_LIVE
CSRF_COOKIE_SECURE = IS_LIVE
CSRF_COOKIE_SAMESITE = "Lax"


ALLOWED_HOSTS = ["*"]

# Enable time zone support
USE_TZ = True
TIME_ZONE = 'UTC'


# Throw an exception when getting a naive datetime error - used for debugging
# warnings.filterwarnings(
#     "error",
#     r"DateTimeField .* received a naive datetime",
#     RuntimeWarning,
#     r"django\.db\.models\.fields",
# )

# Application definition

INSTALLED_APPS = [
    'main.apps.MainConfig',
    'about',
    'crispy_forms',
    'crispy_bootstrap5',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

CRISPY_TEMPLATE_PACK = "bootstrap5"

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'main.middleware.RequestIDMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'main.middleware.BlockWordPressPathsMiddleware',
    'main.middleware.UserOrCookieTimezoneMiddleware',
]

ROOT_URLCONF = 'omnivore.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / "templates"
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'main.context_processors.notifications_context',
                "main.context_processors.unread_notifications",
            ],
        },
    },
]

WSGI_APPLICATION = 'omnivore.wsgi.application'

STORAGES = {
    # ...
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        "OPTIONS": {
            # which user fields to compare against
            "user_attributes": ("email", "first_name", "last_name"),
            # be a bit less strict than default 0.7
            "max_similarity": 0.9,
        },
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


AUTH_USER_MODEL = 'main.CustomUser'


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

FORMS_URLFIELD_ASSUME_HTTPS = True

NEW_BADGE_WINDOW_DAYS = 30

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/


STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_URL = 'static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = reverse_lazy('home')     # after successful login
LOGOUT_REDIRECT_URL = reverse_lazy('home')    # optional, nice to have

CSRF_TRUSTED_ORIGINS = [
    'https://web-production-4a6f.up.railway.app',
    'https://web-staging-f21f.up.railway.app',
    'http://localhost',
    'http://127.0.0.1',
    'http://localhost:8001',
    'http://127.0.0.1:8001',
    'http://192.168.1.237:8000',
    "https://omnivorearts.com",
    "https://www.omnivorearts.com",
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_FAILURE_VIEW = 'main.views.csrf_failure'

handler404 = 'main.views.custom_404'

ADMINS = [("Jonathan", "jonathan@omnivorearts.com")]
SERVER_EMAIL = "support@omnivorearts.com"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


class RequestIDFilter:
    def filter(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "verbose": {
            "format": "%(asctime)s [%(levelname)s] %(name)s %(message)s request_id=%(request_id)s",
        },
    },

    "filters": {
        "request_id": {
            "()": RequestIDFilter,  # or "omnivore.settings.RequestIDFilter"
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "level": LOG_LEVEL,
            "filters": ["request_id"],
        },
        "mail_admins": {
            "class": "django.utils.log.AdminEmailHandler",
            "level": "ERROR",
            "include_html": True,
            "filters": ["request_id"],
        },
    },

    "root": {"handlers": ["console"], "level": LOG_LEVEL},

    "loggers": {
        # send 4xx/5xx request errors to console + email
        "django.request": {
            "handlers": ["console", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "whitenoise": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "main": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "gunicorn.error": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "gunicorn.access": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
