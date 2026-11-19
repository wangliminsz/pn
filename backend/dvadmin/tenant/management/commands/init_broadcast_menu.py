# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from dvadmin.system.models import Menu, Role, RoleMenuPermission


class Command(BaseCommand):
    help = '初始化「群发信息」菜单, 仅授权给租户经理(tenant_manager)'

    def handle(self, *args, **options):
        menu, created = Menu.objects.get_or_create(
            name='群发信息',
            defaults=dict(
                parent=None,
                icon='ele-ChatDotRound',
                name_en='Broadcast',
                name_zh_tw='群發訊息',
                sort=7,
                is_catalog=False,
                web_path='/broadcast',
                component='system/broadcast/index',
                component_name='broadcast',
                status=True,
                visible=True,
            ),
        )
        if not created:
            menu.web_path = '/broadcast'
            menu.component = 'system/broadcast/index'
            menu.component_name = 'broadcast'
            menu.save()

        role = Role.objects.filter(key='tenant_manager').first()
        granted = 0
        # 给所有租户自己的 tenant_manager 角色授权(平台模板角色 tenant 为空也纳入, 不取"第一个")
        for role in Role.objects.filter(key='tenant_manager'):
            _, created_perm = RoleMenuPermission.objects.get_or_create(role=role, menu=menu)
            if created_perm:
                granted += 1
        if not granted:
            self.stdout.write(self.style.WARNING('未找到 tenant_manager 角色, 跳过授权'))
        else:
            self.stdout.write(self.style.SUCCESS(f'群发信息菜单已授权给 {granted} 个 tenant_manager 角色'))

        self.stdout.write(self.style.SUCCESS('返回信息菜单初始化完成'))