# -*- coding: utf-8 -*-
"""
超级管理员控制台 - 概览聚合接口
聚合租户 / LineBot / 消息记录的统计数据, 仅超级管理员可访问
"""
from datetime import datetime

from django.conf import settings
from rest_framework.views import APIView

from dvadmin.notify.models import LineBot, MessageLog
from dvadmin.tenant.models import Tenant
from dvadmin.utils.json_response import SuccessResponse
from dvadmin.utils.permission import SuperuserPermission


class DashboardStatView(APIView):
    """概览统计: 租户 / Bot / 消息量"""

    permission_classes = [SuperuserPermission]

    def get(self, request):
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        data = {
            "tenant_total": Tenant.objects.count(),
            "tenant_trial": Tenant.objects.filter(plan_type="trial").count(),
            "tenant_paid": Tenant.objects.filter(plan_type="paid").count(),
            "tenant_active": Tenant.objects.filter(is_active=True).count(),
            "bot_total": LineBot.objects.count(),
            "bot_active": LineBot.objects.filter(is_active=True).count(),
            "msg_total": MessageLog.objects.filter(create_datetime__gte=month_start).count(),
        }
        return SuccessResponse(data=data)


class EnvConfigView(APIView):
    """环境配置概览(仅超管): 展示常用 .env 值, 便于判断是否需要改/重启
    敏感值(密钥/token)一律脱敏, 仅显示前缀+后缀
    """

    permission_classes = [SuperuserPermission]

    def _mask(self, val, keep=4):
        """脱敏: 保留前keep位+后keep位, 中间打码"""
        if not val:
            return ""
        s = str(val)
        if len(s) <= keep * 2:
            return s[:keep] + "****" + (s[-keep:] if len(s) > keep else "")
        return f"{s[:keep]}****{s[-keep:]}"

    def get(self, request):
        def g(k, default=""):
            return getattr(settings, k, default)

        # (key, label, 是否脱敏, 运行时可读)
        items = [
            ("数据库", "DATABASE_HOST", "host", False),
            ("数据库", "DATABASE_PORT", "port", False),
            ("数据库", "DATABASE_NAME", "库名", False),
            ("数据库", "DEBUG", "DEBUG", False),
            ("代理", "LINE_API_PROXY", "LINE 代理", False),
            ("代理", "GOOGLE_API_PROXY", "Google 代理", False),
            ("翻译", "GOOGLE_TRANSLATE_API_KEY", "Google key", True),
            ("翻译", "DEEPL_API_URL", "Deepl URL", False),
            ("翻译", "BAIDU_APPID", "百度 appid", False),
            ("翻译", "BAIDU_APPKEY", "百度 key", True),
            ("翻译", "LINE_BOT_TRANSLATE_ENABLED", "群翻译", False),
            ("翻译", "LINE_BOT_VERIFY", "回调校验", False),
            ("Line / 配额", "BOT_MSG_LIMIT", "Bot 硬上限", False),
            ("Line / 配额", "MSG_ALERT_RATIO", "告警阈值", False),
            ("Line / 配额", "MSG_ALERT_WEBHOOK_URL", "告警 webhook", False),
            ("Line / 配额", "LINE_SIGNATURE", "落款签名", False),
            ("Line / 配额", "NOTIFY_SEND_HOUR", "每日提醒时间(泰国)", False),
            ("支付", "PAYMENT_PROVIDER", "支付网关", False),
            ("支付", "PAYMENT_AMOUNT_THB", "续费金额(THB)", False),
            ("支付", "PAYMENT_RENEW_DAYS", "续费天数", False),
            ("支付", "PAYMENT_DEV_SIMULATE", "开发模拟模式", False),
            ("支付", "OMISE_SECRET_KEY", "Omise Secret Key", True),
            ("支付", "OMISE_PUBLIC_KEY", "Omise Public Key", True),
            ("对象存储 (COS)", "COS_ENABLED", "启用", False),
            ("对象存储 (COS)", "COS_REGION", "Region", False),
            ("对象存储 (COS)", "COS_BUCKET", "Bucket", False),
            ("对象存储 (COS)", "COS_SECRET_ID", "SecretId", True),
            ("对象存储 (COS)", "COS_SECRET_KEY", "SecretKey", True),
            # 邮件(SMTP) —— 忘记密码自助重置用
            ("邮件 (SMTP)", "EMAIL_HOST", "SMTP 主机", False),
            ("邮件 (SMTP)", "EMAIL_PORT", "SMTP 端口", False),
            ("邮件 (SMTP)", "EMAIL_HOST_USER", "发件账号", False),
            ("邮件 (SMTP)", "EMAIL_HOST_PASSWORD", "SMTP 密码", True),
            ("邮件 (SMTP)", "EMAIL_USE_SSL", "SSL", False),
            # 前端
            ("前端", "FRONTEND_BASE", "前端地址", False),
        ]
        groups = {}
        for group, key, label, secret in items:
            val = g(key, "")
            if secret and val:
                val = self._mask(val)
            groups.setdefault(group, []).append({"key": key, "label": label, "value": val})
        # 保持分组顺序
        ordered = []
        for group in ["数据库", "代理", "翻译", "Line / 配额", "支付", "对象存储 (COS)", "邮件 (SMTP)", "前端"]:
            if group in groups:
                ordered.append({"group": group, "items": groups[group]})
        return SuccessResponse(data=ordered)
