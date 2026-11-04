"""Independent UI demo settings; no operational database/secret fallback."""
import os
from pathlib import Path

if os.environ.get('SNP_UI_PREVIEW') != '1':
    raise RuntimeError('UI preview must be started explicitly')

def secret(name):
    value = (Path('/run/secrets') / name).read_text().strip()
    if not value:
        raise RuntimeError(f'Empty preview secret: {name}')
    return value

# Base settings require these variables. They always target our Compose DB service.
os.environ.update(DB_NAME='snp_ui_preview', DB_USER='snp_ui_preview',
                  DB_PASSWORD=secret('db_password'), DB_HOST='db', DB_PORT='3306')
from .settings import *
SECRET_KEY = secret('django_secret')
DEBUG = False
ALLOWED_HOSTS = os.environ['SNP_PREVIEW_ALLOWED_HOSTS'].split(',')
CSRF_TRUSTED_ORIGINS = [x for x in os.environ.get('SNP_PREVIEW_CSRF_ORIGINS', '').split(',') if x]
DATABASES['default']['CONN_MAX_AGE'] = 60
DATABASES['default']['OPTIONS'] = {'charset': 'utf8mb4', 'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"}
STATIC_ROOT = '/srv/static'
SESSION_COOKIE_NAME = 'snp_ui_preview_session'
CSRF_COOKIE_NAME = 'snp_ui_preview_csrf'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = os.environ.get('SNP_PREVIEW_HTTPS') == '1'
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
# Proxy overwrites X-Forwarded-Proto from its own connection; no arbitrary client trust.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'

TEMPLATES[0]['OPTIONS']['context_processors'] = [*TEMPLATES[0]['OPTIONS']['context_processors'], 'config.preview_context.preview_banner']
