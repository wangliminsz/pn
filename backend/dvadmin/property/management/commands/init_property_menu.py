# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from dvadmin.system.models import Menu, MenuButton, Role, RoleMenuPermission, RoleMenuButtonPermission


class Command(BaseCommand):
    help = '初始化房源管理菜单 + 按钮, 并授权给测试角色(中介经理)'

    def handle(self, *args, **options):
        parent = Menu.objects.filter(name='系统管理', is_catalog=True).first()
        menu, created = Menu.objects.get_or_create(
            name='房源管理',
            defaults=dict(
                parent=parent,
                icon='icon-xitong',
                name_en='Property',
                name_zh_tw='房源管理',
                sort=3,
                is_catalog=False,
                web_path='/property',
                component='system/property/index',
                component_name='property',
                status=True,
                visible=True,
            ),
        )
        if not created and parent:
            menu.parent = parent
            menu.save()

        # 按钮权限(api 需要带前导 /, {id} 为详情)
        MenuButton.objects.filter(menu=menu).delete()
        buttons = [
            ('查看列表', 'property:List', '/api/property/property/', 0),
            ('查看详情', 'property:Retrieve', '/api/property/property/{id}/', 0),
            ('新增', 'property:Add', '/api/property/property/', 1),
            ('修改', 'property:Update', '/api/property/property/{id}/', 2),
            ('删除', 'property:Delete', '/api/property/property/{id}/', 3),
            ('自定义提醒-列表', 'reminder_rule:List', '/api/property/reminder_rule/', 0),
            ('自定义提醒-新增', 'reminder_rule:Add', '/api/property/reminder_rule/', 1),
            ('自定义提醒-修改', 'reminder_rule:Update', '/api/property/reminder_rule/{id}/', 2),
            ('自定义提醒-删除', 'reminder_rule:Delete', '/api/property/reminder_rule/{id}/', 3),
        ]
        btn_map = {}
        for name, value, api, method in buttons:
            b, _ = MenuButton.objects.get_or_create(
                value=value,
                defaults=dict(menu=menu, name=name, name_en=name, name_zh_tw=name, api=api, method=method),
            )
            btn_map[value] = b

        # 角色: 中介经理
        role, _ = Role.objects.get_or_create(key='agent_manager', defaults=dict(name='中介经理', sort=2, status=True))

        RoleMenuPermission.objects.get_or_create(role=role, menu=menu)
        # data_range: 0=仅本人 1=本部门及以下 2=本部门 3=全部数据权限(经理) 4=自定义
        for value, b in btn_map.items():
            RoleMenuButtonPermission.objects.update_or_create(
                role=role, menu_button=b, defaults={'data_range': 3},
            )

        # 把角色分配给测试用户
        from dvadmin.system.models import Users
        for uname in ['agent1', 'agent2', 'agent_b']:
            u = Users.objects.filter(username=uname).first()
            if u:
                u.role.add(role)
        self.stdout.write(self.style.SUCCESS('房源菜单/权限初始化完成, 角色[中介经理]已授权'))
