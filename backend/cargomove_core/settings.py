"""
Django settings for cargomove_core project.
"""

from pathlib import Path
from decouple import config
from datetime import timedelta
import dj_database_url

# BASE_DIR points to the backend/ folder — Django uses this to find every other file.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Security (from .env locally, from Render's environment variables in production) ---
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

# Comma-separated list, e.g. "cargomove-backend.onrender.com,127.0.0.1,localhost"
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='127.0.0.1,localhost',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()],
)

# Needed so Django admin's CSRF-protected forms (e.g. the admin login) work
# over your deployed HTTPS domain. Empty by default for local dev.
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()],
)

# --- Apps ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',

    'api',  # your app
]

# --- Middleware (order matters: corsheaders must sit near the top,
# whitenoise must sit right after SecurityMiddleware so it can serve
# static files directly — no separate static file server needed) ---
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cargomove_core.urls'

# TEMPLATES is required even though we're not using Django's HTML templating
# (our frontend is separate vanilla JS) — the admin panel still needs it.
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'cargomove_core.wsgi.application'

# --- Database ---
# If DATABASE_URL is set (Render/Neon in production), use it.
# Otherwise fall back to the split DB_* vars (local dev, unchanged).
_database_url = config('DATABASE_URL', default='')

if _database_url:
    DATABASES = {
        'default': dj_database_url.parse(_database_url, conn_max_age=600, ssl_require=True)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST'),
            'PORT': config('DB_PORT'),
        }
    }

AUTH_USER_MODEL = 'api.User'

# --- Password validation (Django default — reasonable for a class project) ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- Internationalization ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Douala'
USE_I18N = True
USE_TZ = True

# --- Static files ---
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # collectstatic writes here; whitenoise serves from here

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- DRF: use JWT as the default way clients authenticate ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
# NOTE: Render's free web service has an ephemeral filesystem — anything
# written here (KYC photos, vehicle photos) is wiped on every restart or
# redeploy. Fine for a demo; if that becomes a problem, swap this for a
# free image host (e.g. Cloudinary) later.

CORS_ALLOW_ALL_ORIGINS = True

# --- Production security hardening (only applied when DEBUG=False, so
# local HTTP dev is unaffected) ---
if not DEBUG:
    # Render terminates SSL at its proxy and forwards plain HTTP internally,
    # so Django needs this header to know the original request was HTTPS —
    # without it, SECURE_SSL_REDIRECT below causes an infinite redirect loop.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7  # 1 week — conservative for a class project
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
