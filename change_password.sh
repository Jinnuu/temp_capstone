cd ~/sprint7-integration

docker compose -p snp-ui-preview \
  --env-file .ui-preview/compose.env \
  -f compose.ui-preview.yml \
  exec web python manage.py changepassword verify-admin
