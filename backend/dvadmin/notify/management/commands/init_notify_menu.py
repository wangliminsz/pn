# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from dvadmin.system.models import Menu, MenuButton, Role, RoleMenuPermission, RoleMenuButtonPermission


class Command(BaseCommand):
    help = '初始化 LineBot管理 + 消息记录 菜单与按钮'

    def handle(self, *args, **options):
        parent = Menu.objects.filter(name='系统管理', is_catalog=True).first()

        # ---------- LineBot 管理 ----------
        menu, created = Menu.objects.get_or_create(
            name='LineBot管理',
            defaults=dict(
                parent=parent,
                icon='icon-xitong',
                name_en='LineBot',
                name_zh_tw='LineBot管理',
                sort=4,
                is_catalog=False,
                web_path='/linebot',
                component='system/linebot/index',
                component_name='linebot',
                status=True,
                visible=True,
            ),
        )
        if not created and parent:
            menu.parent = parent
            menu.save()
        MenuButton.objects.filter(menu=menu).delete()
        buttons = [
            ('查看列表', 'linebot:List', '/api/notify/linebot/', 0),
            ('查看详情', 'linebot:Retrieve', '/api/notify/linebot/{id}/', 0),
            ('新增', 'linebot:Add', '/api/notify/linebot/', 1),
            ('修改', 'linebot:Update', '/api/notify/linebot/{id}/', 2),
            ('删除', 'linebot:Delete', '/api/notify/linebot/{id}/', 3),
        ]
        btn_map = {}
        for name, value, api, method in buttons:
            b, _ = MenuButton.objects.get_or_create(
                value=value,
                defaults=dict(menu=menu, name=name, name_en=name, name_zh_tw=name, api=api, method=method),
            )
            btn_map[value] = b

        # ---------- 消息记录 ----------
        menu2, created2 = Menu.objects.get_or_create(
            name='消息记录',
            defaults=dict(
                parent=parent,
                icon='icon-xitong',
                name_en='MessageLog',
                name_zh_tw='消息记录',
                sort=5,
                is_catalog=False,
                web_path='/messagelog',
                component='system/messagelog/index',
                component_name='messagelog',
                status=True,
                visible=True,
            ),
        )
        if not created2 and parent:
            menu2.parent = parent
            menu2.save()
        MenuButton.objects.filter(menu=menu2).delete()
        buttons2 = [
            ('查看列表', 'messagelog:List', '/api/notify/messagelog/', 0),
            ('查看详情', 'messagelog:Retrieve', '/api/notify/messagelog/{id}/', 0),
        ]
        btn_map2 = {}
        for name, value, api, method in buttons2:
            b, _ = MenuButton.objects.get_or_create(
                value=value,
                defaults=dict(menu=menu2, name=name, name_en=name, name_zh_tw=name, api=api, method=method),
            )
            btn_map2[value] = b

        # ---------- 群文档 ----------
        menu3, created3 = Menu.objects.get_or_create(
            name='群文档',
            defaults=dict(
                parent=parent,
                icon='icon-xitong',
                name_en='GroupDoc',
                name_zh_tw='群文档',
                sort=6,
                is_catalog=False,
                web_path='/groupdoc',
                component='system/groupdoc/index',
                component_name='groupdoc',
                status=True,
                visible=True,
            ),
        )
        if not created3 and parent:
            menu3.parent = parent
            menu3.save()
        MenuButton.objects.filter(menu=menu3).delete()
        buttons3 = [
            ('查看列表', 'groupdoc:List', '/api/notify/groupdoc/', 0),
        ]
        for name, value, api, method in buttons3:
            MenuButton.objects.get_or_create(
                value=value,
                defaults=dict(menu=menu3, name=name, name_en=name, name_zh_tw=name, api=api, method=method),
            )

        self.stdout.write(self.style.SUCCESS('LineBot管理 + 消息记录 + 群文档 菜单/权限初始化完成'))
