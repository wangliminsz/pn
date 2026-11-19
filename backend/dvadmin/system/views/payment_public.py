# -*- coding: utf-8 -*-
"""公开支付配置(前端落地页/结算页读取价格用, 无需登录)。

用途: 服务器后端若尚未安装 `dvadmin.tenant` 分支, 由 `application/urls.py`
兜底注册本视图, 使 `GET /api/tenant/payment/public_config/` 可正常返回,
避免前端控制台出现 404。数值取自 settings, 未配置时回退 2000 THB / 365 天
(与前端 `PLAN` 默认值一致), 因此无需新增环境变量。

只读接口, 不涉及任何业务写入, 不影响既有功能。
"""
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from dvadmin.utils.json_response import SuccessResponse

DEFAULT_AMOUNT_THB = 2000
DEFAULT_RENEW_DAYS = 365


def _positive_int(name, default):
    try:
        value = int(getattr(settings, name, 0) or 0)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


class PublicPaymentConfigView(APIView):
    """只读: 返回年付计划金额与周期, 供未登录页面展示。"""

    permission_classes = [AllowAny]

    def get(self, request):
        return SuccessResponse(data={
            "enabled": bool(getattr(settings, "PAYMENT_PROVIDER", "")),
            "amount_thb": _positive_int("PAYMENT_AMOUNT_THB", DEFAULT_AMOUNT_THB),
            "currency": "THB",
            "renew_days": _positive_int("PAYMENT_RENEW_DAYS", DEFAULT_RENEW_DAYS),
            "auto_renew": False,
            "payment_method": "PromptPay QR via Omise",
        })
