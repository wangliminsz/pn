# -*- coding: utf-8 -*-
"""
初始化 LINE Bot 凭证
用法: python manage.py init_line_bots
从 conf/line_bots.json 或 conf/env.py 读取 4 个 bot 的凭证写入 LineBot 表
"""
from django.core.management.base import BaseCommand

from dvadmin.notify.models import LineBot


class Command(BaseCommand):
    help = "初始化/导入 LINE Bot 凭证到 LineBot 表"

    def handle(self, *args, **options):
        # 从 conf/line_bots.json 读取(推荐) —— 见 conf/line_bots.example.json
        import json
        import os
        from application.settings import BASE_DIR

        bot_file = os.path.join(BASE_DIR, "conf", "line_bots.json")
        if not os.path.exists(bot_file):
            self.stderr.write(f"未找到配置文件: {bot_file}, 跳过")
            return

        with open(bot_file, "r", encoding="utf-8") as f:
            bots = json.load(f)

        created = 0
        updated = 0
        for i, item in enumerate(bots):
            name = item.get("name")
            bot_code = item.get("bot_code") or f"pro_bot_{i+1:02d}"
            obj, is_created = LineBot.objects.update_or_create(
                bot_code=bot_code,
                defaults={
                    "name": name,
                    "channel_id": item.get("channel_id", ""),
                    "basic_id": item.get("basic_id", ""),
                    "bot_user_id": item.get("bot_user_id", ""),
                    "channel_access_token": item.get("channel_access_token", ""),
                    "channel_secret": item.get("channel_secret", ""),
                    "is_default": item.get("is_default", False),
                    "is_active": item.get("is_active", True),
                },
            )
            if is_created:
                created += 1
                self.stdout.write(f"创建 Bot: {name} ({bot_code})")
            else:
                updated += 1
                self.stdout.write(f"更新 Bot: {name} ({bot_code})")

        self.stdout.write(self.style.SUCCESS(f"完成: 新增 {created}, 更新 {updated}"))
