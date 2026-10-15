"""Offline integration checks; production database settings are never used."""
import os
from unittest.mock import patch
import environ

with patch.object(environ.Env, "read_env"), patch.dict(os.environ, {
    "DB_NAME": "unused", "DB_USER": "unused", "DB_PASSWORD": "unused",
    "DB_HOST": "unused", "DB_PORT": "3306",
}):
    from .settings import *

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "/tmp/sprint7-integration.sqlite3"}}
SECRET_KEY = "isolated-integration-tests-only"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
