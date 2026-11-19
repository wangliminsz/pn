from django.apps import AppConfig


class PropertyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dvadmin.property'
    verbose_name = '房源管理'

    def ready(self):
        from . import signals  # noqa: F401
