#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
wheel_dir="${SPRINT7_WHEEL_DIR:-/tmp/sprint7-test-wheels}"
settings="${1:-config.test_settings}"
image="${SPRINT7_TEST_IMAGE:-capstone-web:sprint7}"
mounts=()
if [[ "$settings" == "config.test_mysql_settings" ]]; then
  mounts=(-v "${SPRINT7_DB_SOCKET_DIR:-/tmp/sprint7-integration-db-socket}:/integration-db:ro")
elif [[ "$settings" != "config.test_settings" ]]; then
  echo 'Only isolated integration settings are allowed.' >&2
  exit 2
fi
docker run --rm --network none --read-only --tmpfs /tmp \
  -e PYTHONDONTWRITEBYTECODE=1 -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
  -e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 -e PYTHONPATH=/tmp/deps \
  -v "$wheel_dir:/wheels:ro" -v "$repo_dir:/workspace:ro" "${mounts[@]}" \
  -w /workspace --entrypoint sh "$image" -c '
    set -eu
    python -m pip install --no-index --no-deps --target /tmp/deps /wheels/xlrd-2.0.2-py2.py3-none-any.whl /wheels/xlwt-1.3.0-py2.py3-none-any.whl
    python -B manage.py check --settings="$1"
    python -B manage.py makemigrations --check --dry-run --settings="$1"
    python -B manage.py migrate --noinput --settings="$1"
    python -B manage.py migrate --check --settings="$1"
    python -B manage.py showmigrations --settings="$1"
    python -B manage.py test --settings="$1" --verbosity=2
  ' verify "$settings"
