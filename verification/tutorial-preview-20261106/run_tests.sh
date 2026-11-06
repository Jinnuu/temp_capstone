#!/usr/bin/env bash
set -euo pipefail
cd /home/woohyeak/sprint7-integration
settings=${1:-config.test_settings}
case "$settings" in
 config.test_settings) env_args=(); redis_db=15 ;;
 config.auth_mysql_test_settings) env_args=(--env-file .ui-preview/audit/tutorial-preview-20261106/test-db.env); redis_db=14 ;;
 *) exit 2 ;;
esac
docker run --rm --user "$(id -u):$(id -g)" \
 --label snp.task=tutorial-preview-20261106 --label com.docker.compose.project=snp-tutorial-tests-20261106 \
 --network snp-tutorial-tests-20261106 --read-only --tmpfs /tmp "${env_args[@]}" \
 -e DJANGO_SETTINGS_MODULE="$settings" -e ACCOUNT_RECOVERY_REDIS_URL="redis://auth-cache:6379/$redis_db" \
 -e PYTHONDONTWRITEBYTECODE=1 -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
 -e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 \
 -v "$PWD:/workspace:ro" -w /workspace --entrypoint sh snp-ui-preview-web:tutorial-20261106 -ec '
 python -B manage.py check
 python -B manage.py makemigrations --check --dry-run
 python -B manage.py migrate --noinput
 python -B manage.py migrate --check
 python -B manage.py test --verbosity=2
 '
