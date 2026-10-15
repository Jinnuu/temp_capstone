"""Only for the disposable, network-disabled MariaDB test container."""
from .test_settings import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "sprint7_integration",
        "USER": "root",
        "PASSWORD": "isolated-test-password",
        "HOST": "",
        "PORT": "",
        "OPTIONS": {"unix_socket": "/integration-db/mysqld.sock", "connect_timeout": 5},
        "TEST": {"NAME": "test_sprint7_integration"},
    }
}
