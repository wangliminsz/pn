from django.apps import AppConfig


class TenantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dvadmin.tenant'
    verbose_name = '租户管理'
