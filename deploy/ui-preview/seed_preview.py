"""Idempotent account bootstrap; existing passwords and renamed MAIN survive."""
import os
from pathlib import Path
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.preview_settings')
django.setup()
from django.conf import settings
from django.core.management import CommandError
from accounts.preview_bootstrap import bootstrap_accounts

if os.environ.get('SNP_UI_PREVIEW') != '1' or settings.DATABASES['default']['NAME'] != 'snp_ui_preview' or settings.DATABASES['default']['HOST'] != 'db':
    raise RuntimeError('Refusing to seed outside the isolated preview database')


def read_secret(name):
    try:
        return (Path('/run/secrets') / name).read_text()
    except OSError:
        raise CommandError('Required preview bootstrap secret unavailable; no credentials were logged.') from None


bootstrap_accounts(read_secret)
print('Preview accounts ready; existing users, credentials and business records preserved.')
