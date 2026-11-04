#!/bin/sh
set -eu
python -B manage.py check
python -B manage.py migrate --noinput
python -B seed_preview.py
exec "$@"
