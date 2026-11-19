# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from dvadmin.system.models import Menu, Role, RoleMenuPermission


class Command(BaseCommand):
    help = '创建「续费支付」菜单(侧栏隐藏)并给所有租户的三职级角色授权(幂等)'

    def handle(self, *args, **options):
        menu, created = Menu.objects.get_or_create(
            web_path='/payment',
            defaults=dict(
                name='续费支付',
                name_en='Renew Payment',
                name_zh_tw='續費支付',
                icon='ele-Wallet',
                sort=9,
                is_link=False,
                is_catalog=False,
                component='system/payment/index',
                component_name='payment',
                status=True,
                visible=False,  # 不在侧栏显示, 从「已到期」标签进入
                is_iframe=False,
                is_affix=False,
            ),
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'已创建菜单 /payment (id={menu.id})'))
        else:
            self.stdout.write(f'菜单 /payment 已存在 (id={menu.id})')

        granted = 0
        for role in Role.objects.filter(key__in=['tenant_manager', 'tenant_supervisor', 'tenant_emp'],
                                        tenant_id__isnull=False):
            _, created_perm = RoleMenuPermission.objects.get_or_create(role=role, menu=menu)
            if created_perm:
                granted += 1
        self.stdout.write(self.style.SUCCESS(f'菜单授权完成, 新增 {granted} 条'))
