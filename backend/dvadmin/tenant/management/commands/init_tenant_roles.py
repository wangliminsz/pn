# -*- coding: utf-8 -*-
"""
给每个租户预设 经理/主管/员工 三档角色(数据范围不同, 接口按钮权限相同)
用法: python manage.py init_tenant_roles
逻辑复用 org_chart.ensure_tenant_tier_roles(幂等), 与主动导入 org-chart 自动授权保持一致
"""
from django.core.management.base import BaseCommand

from dvadmin.system.models import MenuButton
from dvadmin.tenant.models import Tenant
from dvadmin.tenant.org_chart import ensure_tenant_tier_roles


class Command(BaseCommand):
    help = "为每个租户预设 经理/主管/员工 三角色, 并授予全部业务接口按钮权限"

    def handle(self, *args, **options):
        if not MenuButton.objects.exists():
            self.stdout.write(self.style.WARNING("未发现任何菜单按钮, 请先 init 菜单"))
            return

        for tenant in Tenant.objects.all():
            ensure_tenant_tier_roles(tenant)
            self.stdout.write(f"租户[{tenant.name}] 三角色已就绪(按钮授权+数据范围)")

        self.stdout.write(self.style.SUCCESS("所有租户的三档角色初始化完成"))
