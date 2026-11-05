"""Disposable auth-verification MariaDB only; hostname cannot target production."""
from .auth_test_settings import *
DATABASES={'default':{'ENGINE':'django.db.backends.mysql','NAME':'snp_auth_verification','USER':'root',
    'PASSWORD':os.environ['AUTH_TEST_DB_PASSWORD'],'HOST':'auth-db','PORT':'3306',
    'OPTIONS':{'charset':'utf8mb4'}}}
