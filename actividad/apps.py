from django.apps import AppConfig


class ActividadConfig(AppConfig):
    name = 'actividad'
    verbose_name = 'Registro de actividad'

    def ready(self):
        from . import signals  # noqa: F401  (conecta las señales de login)
