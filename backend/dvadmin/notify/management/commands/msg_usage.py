# -*- coding: utf-8 -*-
"""
查看消息配额使用情况
用法: python manage.py msg_usage
"""
from django.core.management.base import BaseCommand

from dvadmin.notify.models import LineBot
from dvadmin.notify.services import get_current_month_usage, _bot_quota


class Command(BaseCommand):
    help = "查看各 Bot 当月消息配额使用情况"

    def handle(self, *args, **options):
        self.stdout.write("==== 按 Bot ====")
        for bot in LineBot.objects.filter(is_active=True):
            used = get_current_month_usage(bot)
            limit = _bot_quota(bot, None)
            self.stdout.write(f"{bot.name:<16} used={used:<6} limit={limit}")
