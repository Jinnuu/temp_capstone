# Reuse the tested AI/Python dependency environment without changing its tag.
ARG SNP_PREVIEW_BASE=capstone-web:sprint7
FROM ${SNP_PREVIEW_BASE} AS clean_runtime
USER root
# Build-stage filesystem only: never mounts or edits any host checkout/container.
# Final FROM scratch does not retain the original image layers or legacy app/.env.
RUN rm -rf /app /root /home /tmp /var/tmp \
    && mkdir -p /app /root /home /tmp /var/tmp \
    && chmod 1777 /tmp /var/tmp

FROM scratch AS app
COPY --from=clean_runtime / /
ENV PATH=/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin LANG=C.UTF-8
USER root
WORKDIR /srv/snp
RUN python -m pip install --no-cache-dir --no-deps gunicorn==26.2.0 xlrd==2.0.2 xlwt==1.3.0 redis==8.1.0
COPY accounts accounts
COPY config config
COPY forecasting forecasting
COPY inventory inventory
COPY meals meals
COPY procurement procurement
COPY templates templates
COPY static static
COPY ml_models ml_models
COPY deploy/ui-preview/ai_data data
COPY manage.py manage.py
COPY deploy/ui-preview/entrypoint.sh /usr/local/bin/snp-preview-entrypoint
COPY deploy/ui-preview/seed_preview.py /srv/snp/seed_preview.py
RUN python -B manage.py collectstatic --noinput --settings=config.preview_build_settings \
    && chmod 755 /usr/local/bin/snp-preview-entrypoint \
    && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin snp-preview
ENV DJANGO_SETTINGS_MODULE=config.preview_settings PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
USER 10001:10001
ENTRYPOINT ["snp-preview-entrypoint"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--no-control-socket", "--timeout", "180", "--access-logfile", "-", "--access-logformat", "%(h)s %(m)s %({x-snp-log-path}i)s %(s)s", "--error-logfile", "-", "--worker-tmp-dir", "/tmp"]

FROM nginx:alpine AS proxy
COPY deploy/ui-preview/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=app /srv/static /srv/static
