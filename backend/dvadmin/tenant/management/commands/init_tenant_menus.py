# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from dvadmin.system.models import Menu, Role, RoleMenuPermission


class Command(BaseCommand):
    help = '为所有租户的三职级角色(经理/主管/员工)批量授权标准业务菜单(幂等, 参考租户9已手动授权的菜单集)'

    def handle(self, *args, **options):
        # 菜单以 web_path 定位(与租户9已验证的授权一致); 用 org_chart 常量避免两处维护
        from dvadmin.tenant.org_chart import MENU_BASE_PATHS, MENU_MANAGER_ONLY_PATHS
        BASE_PATHS = MENU_BASE_PATHS
        MANAGER_ONLY_PATHS = MENU_MANAGER_ONLY_PATHS

        menu_by_path = {}
        for m in Menu.objects.all():
            if m.web_path:
                menu_by_path[m.web_path] = m

        missing = [p for p in BASE_PATHS + MANAGER_ONLY_PATHS if p not in menu_by_path]
        if missing:
            self.stdout.write(self.style.WARNING(f'以下菜单 web_path 不存在, 跳过: {missing}'))

        granted = 0
        for role in Role.objects.filter(key__in=['tenant_manager', 'tenant_supervisor', 'tenant_emp'], tenant_id__isnull=False):
            paths = list(BASE_PATHS)
            if role.key == 'tenant_manager':
                paths += MANAGER_ONLY_PATHS
            for p in paths:
                menu = menu_by_path.get(p)
                if not menu:
                    continue
                if p == '/system':
                    # 业务工作台 是目录(id=1, is_catalog), 子菜单分属其下
                    pass
                _, created = RoleMenuPermission.objects.get_or_create(role=role, menu=menu)
                if created:
                    granted += 1
        self.stdout.write(self.style.SUCCESS(f'菜单授权完成, 新增 {granted} 条(已有授权的租户自动跳过)'))