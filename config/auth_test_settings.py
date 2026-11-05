"""Task-only SQLite/mail-capture settings; never imports preview DB secrets."""
from .test_settings import *
ACCOUNT_RECOVERY_DELIVERY_MODE = 'test'
ACCOUNT_RECOVERY_ALLOW_TEST_DELIVERY = True
ACCOUNT_RECOVERY_BASE_URL = os.environ.get('AUTH_TEST_BASE_URL','http://127.0.0.1:18011')
ACCOUNT_RECOVERY_REDIS_URL = os.environ.get('ACCOUNT_RECOVERY_REDIS_URL','redis://auth-cache:6379/0')
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'auth-mail'
EMAIL_PORT = 1025
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = 'snp-test@example.invalid'
