"""
Django settings for RAOLY BTP (Carorles) project.
Construction equipment rental company.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-change-me-in-production'

DEBUG = True

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    'raolybtp.pythonanywhere.com',
]

# Ngrok support (auth/register/login over HTTPS tunnel)
CSRF_TRUSTED_ORIGINS = [
    'https://azotic-pseudoartistically-angla.ngrok-free.dev',
    'https://*.ngrok-free.dev',
    'https://raolybtp.pythonanywhere.com',
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'crispy_forms',
    'crispy_bootstrap5',
    'core',
    'accounts',
    'equipment',
    'cart',
    'payments',
    'contracts',
    'blockchain',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
]

ROOT_URLCONF = 'bekouma.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'core.context_processors.site_info',
                'accounts.context_processors.kyc_rental_gate',
            ],
        },
    },
]

WSGI_APPLICATION = 'bekouma.wsgi.application'

# Database - SQLite for development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Custom user model
AUTH_USER_MODEL = 'accounts.CustomUser'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Auth URLs
LOGIN_URL = '/comptes/login/'
LOGIN_REDIRECT_URL = '/comptes/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# Notch Pay — clés de test : https://business.notchpay.co/ → Sandbox → Settings → API Keys (pk_test_…)
# Hash webhook (signature x-notch-signature) : Settings → Webhooks → hash (ex. hsk_test_…)

NOTCHPAY_PUBLIC_KEY = os.getenv('NOTCHPAY_PUBLIC_KEY', 'pk_test.uxWbsvPfAFG6Ocjz0Z93KnuFSA98FKju4OfdBL4oj8Rw2IF8n0MjHetrSAFEtdRkIW18TaSxD7CFFm92WK6VdKjwZjFYQr6UlovbN4hYMgHD3UvmD8jMlwMpHw7Xq')
NOTCHPAY_WEBHOOK_HASH = os.getenv('NOTCHPAY_WEBHOOK_HASH', 'hsk_test.i4KITc5srN18NJyN4qD6qmDRyX43i6BUJvZhToIqSEOmenLvqhyIDIzt6OHt1WyrVVDsP14ow8YKugLESEPihaBqBLVtdwUe5MGNCsLARMWjZJw5QMiP285jw3dFQ')
NOTCHPAY_API_BASE = os.getenv('NOTCHPAY_API_BASE', 'https://api.notchpay.co')

# Pings GPS live (téléphone) : prise en compte si plus récent que N minutes
LIVE_TRACKING_MAX_AGE_MINUTES = int(os.getenv('LIVE_TRACKING_MAX_AGE_MINUTES', '45'))

# Tarif journalier entreprise = tarif particulier + ce montant (FCFA)
EQUIPMENT_ENTERPRISE_PRICE_EXTRA_FCFA = int(os.getenv('EQUIPMENT_ENTERPRISE_PRICE_EXTRA_FCFA', '10000'))

# Admin / simulation: rayon (km) autour du point déclaré — au-delà = « hors zone »
DECLARED_ZONE_ALERT_RADIUS_KM = float(os.getenv('DECLARED_ZONE_ALERT_RADIUS_KM', '3'))

# Email / Password reset
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'no-reply@raolybtp.com')
