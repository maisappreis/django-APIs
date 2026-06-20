from django.apps import AppConfig


class AiContentAgentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai_content_agent'

    def ready(self):
        from . import signals  # noqa: F401
