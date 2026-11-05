from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"

    def ready(self):
        import logging
        from .logging_filters import RecoveryRedactionFilter
        for name in ['django.request','django.server','django.security.csrf','accounts.recovery']:
            logging.getLogger(name).addFilter(RecoveryRedactionFilter())
