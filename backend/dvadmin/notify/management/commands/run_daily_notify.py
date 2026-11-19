# -*- coding: utf-8 -*-
"""
手动触发每日提醒扫描
用法:
  python manage.py run_daily_notify                 # 扫描今天
  python manage.py run_daily_notify --date 2026-02-28  # 指定日期(测试闰年)
  python manage.py run_daily_notify --tenant 1      # 仅指定租户
  python manage.py run_daily_notify --dry-run       # 只打印, 不发送
"""
from datetime import datetime

from django.core.management.base import BaseCommand

from dvadmin.notify.services import push_to_group


class Command(BaseCommand):
    help = "手动触发每日提醒扫描"

    def add_arguments(self, parser):
        parser.add_argument("--date", type=str, default=None, help="指定日期 YYYY-MM-DD(测试用)")
        parser.add_argument("--tenant", type=int, default=None, help="仅指定租户ID")
        parser.add_argument("--dry-run", action="store_true", help="只打印不发送")

    def handle(self, *args, **options):
        target_date = options.get("date")
        tenant_id = options.get("tenant")
        dry_run = options.get("dry_run")

        if dry_run:
            self._dry_run(target_date, tenant_id)
            return

        from dvadmin.notify.tasks import daily_notify_task
        # 直接同步执行(不通过celery, 便于看日志)
        from dvadmin.notify.tasks import scan_and_notify
        tenant_ids = [tenant_id] if tenant_id else None
        # --date 传入的是字符串, 统一转成 date, 否则 scan_and_notify 里 combine 会崩
        if target_date:
            from datetime import datetime
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        sent = scan_and_notify(tenant_ids=tenant_ids, target_date=target_date)
        self.stdout.write(self.style.SUCCESS(f"扫描完成, 发送 {sent} 条"))

    def _dry_run(self, target_date, tenant_id):
        from dvadmin.notify.tasks import (
            _within_rent_range,
            _is_pay_period_month,
            _pay_remind_day_hit,
            build_rent_message,
            build_maturity_message,
        )
        from dvadmin.property.models import Property
        from datetime import datetime

        now = datetime.strptime(target_date, "%Y-%m-%d") if target_date else datetime.now()
        qs = Property.objects.filter(group_id__isnull=False)
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        for prop in qs:
            if not _within_rent_range(prop, now):
                continue
            if prop.remind_day and _is_pay_period_month(now, prop) and _pay_remind_day_hit(now, prop):
                self.stdout.write(f"[RENT] {prop.name} -> {prop.group_id} (群人数{prop.group_size})")
                self.stdout.write(build_rent_message(prop) + "\n")
            if prop.rent_end:
                days_before = (prop.rent_end - now.date()).days
                if days_before in (30, 15):
                    self.stdout.write(f"[MATURITY] {prop.name} -> {prop.group_id} ({days_before}天前)")
                    self.stdout.write(build_maturity_message(prop, prop.rent_end) + "\n")
