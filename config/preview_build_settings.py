"""Static collection only: never connect to an existing database."""
from .test_settings import *
DEBUG = False
STATIC_ROOT = '/srv/static'
