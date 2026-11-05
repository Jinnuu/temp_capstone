"""Create preview-only secrets without overwriting any existing value."""
import argparse
from pathlib import Path
import secrets
import socket

parser = argparse.ArgumentParser()
parser.add_argument('--bind', default='127.0.0.1')
parser.add_argument('--port', type=int, default=8011)
parser.add_argument('--hosts', default='localhost,127.0.0.1')
args = parser.parse_args()
if not 1024 <= args.port <= 65535:
    parser.error('Choose a non-privileged TCP port')
root = Path(__file__).resolve().parents[2] / '.ui-preview'
root.mkdir(mode=0o700, exist_ok=True)
root.chmod(0o700)
for key in ['db_password', 'db_root_password', 'django_secret', 'demo_password', 'preview_admin_password', 'recovery_cache_password']:
    target = root / key
    if not target.exists():
        with target.open('x') as out:
            out.write(secrets.token_urlsafe(64 if key == 'django_secret' else 36) + '\n')
        # Compose mounts individual files for the non-root web process. Parent is 0700.
        target.chmod(0o644)
smtp = root / 'smtp_password'
if not smtp.exists():
    smtp.write_text('')
    smtp.chmod(0o644)
env = root / 'compose.env'
if not env.exists():
    with socket.socket() as sock:
        sock.bind((args.bind, args.port))
    env.write_text(f'SNP_PREVIEW_BIND={args.bind}\nSNP_PREVIEW_PORT={args.port}\nSNP_PREVIEW_ALLOWED_HOSTS={args.hosts}\n')
    env.chmod(0o600)
print('Preview secrets ready; existing files preserved. Administrator and demo secrets are separate; values are never printed.')
