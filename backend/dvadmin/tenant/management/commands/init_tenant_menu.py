# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from dvadmin.system.models import Menu


class Command(BaseCommand):
    help = '初始化租户管理菜单(仅超级管理员可见, 普通角色默认不分配)'

    def handle(self, *args, **options):
        parent = Menu.objects.filter(name='系统管理', is_catalog=True).first()
        defaults = dict(
            parent=parent,
            icon='icon-company',
            name_en='Tenant',
            name_zh_tw='租戶管理',
            sort=10,
            is_catalog=False,
            web_path='/tenant',
            component='system/tenant/index',
            component_name='tenant',
            status=True,
            visible=True,
        )
        menu, created = Menu.objects.get_or_create(name='租户管理', defaults=defaults)
        if not created and parent:
            menu.parent = parent
            menu.save()
        self.stdout.write(self.style.SUCCESS(
            '租户管理菜单初始化完成' if created else '租户管理菜单已存在'))
