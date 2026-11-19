# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from dvadmin.system.models import Menu, Role, RoleMenuPermission


class Command(BaseCommand):
    help = '创建「房源变更记录」菜单并给所有租户的三职级角色授权(幂等)'

    def handle(self, *args, **options):
        menu, created = Menu.objects.get_or_create(
            web_path='/changelog',
            defaults=dict(
                name='房源变更记录',
                name_en='Change Log',
                name_zh_tw='房源變更記錄',
                icon='ele-Finished',
                sort=8,
                is_link=False,
                is_catalog=False,
                component='system/changelog/index',
                component_name='changelog',
                status=True,
                visible=True,
                is_iframe=False,
                is_affix=False,
            ),
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'已创建菜单 /changelog (id={menu.id})'))
        else:
            self.stdout.write(f'菜单 /changelog 已存在 (id={menu.id})')

        # 授权给所有租户的三职级角色(全员可见, 因被改派的原负责人也需要看自己的记录)
        granted = 0
        for role in Role.objects.filter(key__in=['tenant_manager', 'tenant_supervisor', 'tenant_emp'],
                                        tenant_id__isnull=False):
            _, created_perm = RoleMenuPermission.objects.get_or_create(role=role, menu=menu)
            if created_perm:
                granted += 1
        self.stdout.write(self.style.SUCCESS(f'菜单授权完成, 新增 {granted} 条'))
