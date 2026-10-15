from django.apps import AppConfig


class ProcurementConfig(AppConfig):
    name = "procurement"

    def ready(self):
        from . import signals  # noqa: F401
