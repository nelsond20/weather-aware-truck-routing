import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
DEBUG = os.environ.get('DJANGO_DEBUG','0') == '1'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY','')
if not SECRET_KEY:
    raise ImproperlyConfigured('DJANGO_SECRET_KEY is required.')
ALLOWED_HOSTS = [v.strip() for v in os.environ.get('DJANGO_ALLOWED_HOSTS','localhost,127.0.0.1').split(',') if v.strip()]
ROOT_URLCONF = 'config.urls'
INSTALLED_APPS = ['rest_framework','routing']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'routing.api.middleware.DeliveryHeadersMiddleware', 'routing.api.middleware.BodyLimitMiddleware']
FRONTEND_DIST = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', '0') == '1'
SECURE_HSTS_SECONDS = 31536000 if SECURE_SSL_REDIRECT else 0
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
if os.environ.get('DJANGO_TRUST_PROXY_HTTPS', '0') == '1':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
DATABASES = {'default':{'ENGINE':'django.db.backends.sqlite3','NAME':':memory:'}}
USE_TZ = True
TIME_ZONE = 'UTC'
DATA_UPLOAD_MAX_MEMORY_SIZE = 2*1024*1024
REST_FRAMEWORK = {'DEFAULT_AUTHENTICATION_CLASSES':[], 'DEFAULT_PERMISSION_CLASSES':[], 'UNAUTHENTICATED_USER':None,
                  'EXCEPTION_HANDLER':'routing.api.errors.exception_handler', 'DEFAULT_RENDERER_CLASSES':['rest_framework.renderers.JSONRenderer']}
PROVIDER_MODE = os.environ.get('PROVIDER_MODE','demo')
if PROVIDER_MODE not in ('demo', 'live'):
    raise ImproperlyConfigured('PROVIDER_MODE must be demo or live.')
LIVE_ROUTING_PROVIDER = os.environ.get('LIVE_ROUTING_PROVIDER', 'valhalla')
if LIVE_ROUTING_PROVIDER not in ('osrm', 'valhalla'):
    raise ImproperlyConfigured('LIVE_ROUTING_PROVIDER must be osrm or valhalla.')
CACHES = {'default':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache'}}
# Production proxy must enforce shared limits before multiple workers.

LOGGING = {'version':1,'disable_existing_loggers':False,'handlers':{'discard':{'class':'logging.NullHandler'}},'loggers':{'django.server':{'handlers':['discard'],'propagate':False}}}
