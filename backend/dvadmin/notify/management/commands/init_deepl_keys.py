# -*- coding: utf-8 -*-
"""
初始化 DeepL API Key 到 DB(解耦 .env 硬编码)
用法: python manage.py init_deepl_keys
首次从 conf/env.py 的 DEEPL_AUTH_KEY 读入作为默认 Key(仅当表为空时创建)
后续 API Key 全部在「DEEPL 管理」界面通过 DB 维护
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from dvadmin.notify.models import DeeplKey


class Command(BaseCommand):
    help = "初始化/导入 DeepL API Key 到 DeeplKey 表(解耦 env 硬编码)"

    def handle(self, *args, **options):
        if DeeplKey.objects.exists():
            self.stdout.write(self.style.WARNING("DeeplKey 表已有数据, 跳过初始化"))
            return

        api_key = getattr(settings, "DEEPL_AUTH_KEY", None)
        if not api_key:
            self.stderr.write("未找到 DEEPL_AUTH_KEY(env.py), 请先在 DEEPL 管理界面手动添加")
            return

        amount = int(getattr(settings, "DEEPL_KEY_CHAR_LIMIT", 0) or 0)
        name = getattr(settings, "DEEPL_KEY_NAME", "") or "默认 Key"
        remark = getattr(settings, "DEEPL_KEY_REMARK", "") or "由 env.py 导入(可删除/DEEPL管理界面维护)"

        DeeplKey.objects.create(
            name=name,
            api_key=api_key,
            is_default=True,
            is_active=True,
            remark=remark,
        )
        self.stdout.write(self.style.SUCCESS(f"已创建默认 DeepL Key: {name}"))
