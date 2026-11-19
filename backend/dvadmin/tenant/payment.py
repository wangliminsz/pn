# -*- coding: utf-8 -*-
"""
租户续费支付(Omise PromptPay)
- 到期租户在前端「已到期」标签点击进入支付页
- 创建 Omise PromptPay charge 拿到二维码; 前端轮询状态
- Omise webhook(charge.complete) 回调成功后, 将租户到期时间 +1 年(PAYMENT_RENEW_DAYS)
- 开发模式(PAYMENT_DEV_SIMULATE=True 且未配 Omise 密钥): 生成测试二维码 + /simulate/ 模拟支付成功
"""
import base64
import hashlib
import hmac
import logging
import random
import time
import uuid

import requests
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext as _
from datetime import timedelta
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from dvadmin.tenant.models import Tenant, TenantPayment
from dvadmin.utils.json_response import ErrorResponse, SuccessResponse
from dvadmin.utils.permission import SuperuserPermission

logger = logging.getLogger(__name__)

OMISE_API_BASE = "https://api.omise.co"


def _payment_enabled():
    return bool(getattr(settings, "PAYMENT_PROVIDER", ""))


def _amount_satang():
    """支付金额(Omise 单位=泰铢*100)"""
    thb = int(getattr(settings, "PAYMENT_AMOUNT_THB", 0) or 0)
    return max(0, thb * 100)


def _renew_days():
    return int(getattr(settings, "PAYMENT_RENEW_DAYS", 365) or 365)


def _expire_seconds():
    """支付超时时间(秒), 默认 15 分钟(900), 超时后自动把 charge 标记为失败"""
    return int(getattr(settings, "PAYMENT_EXPIRE_SECONDS", 900) or 900)


def _is_dev_mode():
    """离线开发模式: 未启用支付 或 未配任何 Omise 密钥(此时生成本地伪二维码)"""
    if not _payment_enabled():
        return True
    if not getattr(settings, "OMISE_SECRET_KEY", ""):
        return True
    return False


def _is_test_mode():
    """测试模式: 使用 Omise test 密钥(可调用 /simulate/ 模拟支付成功)"""
    if not _payment_enabled():
        return False
    secret = getattr(settings, "OMISE_SECRET_KEY", "") or ""
    return bool(secret) and secret.startswith(("skey_test_", "skey_omise_test_", "skey_test"))


def _is_live_mode():
    """正式模式: 已启用支付 且 使用 live 密钥"""
    return _payment_enabled() and not _is_dev_mode() and not _is_test_mode()


def verify_webhook_signature(raw_body, signature_header, timestamp_header):
    """
    校验 Omise webhook 签名(HMAC-SHA256, 常量时间比较)。

    Omise 用 Base64 编码的 webhook secret 对 `{timestamp}.{raw_body}` 做 HMAC-SHA256,
    结果以 hex 字符串放在 `Omise-Signature` 头(轮换期间逗号分隔多个签名)。
    - raw_body: 原始请求体字节(bytes), 严禁用解析后的 JSON
    - signature_header: HTTP 头 `Omise-Signature` 的值
    - timestamp_header: HTTP 头 `Omise-Signature-Timestamp` 的值

    返回 (ok: bool, reason: str):
      ok=True  签名有效
      ok=False reason ∈ {"not_configured", "missing_headers", "bad_timestamp", "bad_signature"}
    """
    secret = getattr(settings, "OMISE_WEBHOOK_SECRET", "") or ""
    if not secret:
        # 未配置 secret: 返回 not_configured, 由调用方决定是否走「事件验证」兜底
        return False, "not_configured"
    if not signature_header or not timestamp_header:
        return False, "missing_headers"

    # 时间戳容差(防重放); 解析失败即拒绝
    try:
        ts = int(str(timestamp_header))
    except (TypeError, ValueError):
        return False, "bad_timestamp"
    tolerance = int(getattr(settings, "OMISE_WEBHOOK_TOLERANCE_SECONDS", 300) or 300)
    if abs(int(time.time()) - ts) > tolerance:
        return False, "bad_timestamp"

    # 解码 Base64 secret -> HMAC 密钥
    try:
        key = base64.b64decode(secret)
    except (ValueError, TypeError):
        logger.warning("[PAYMENT] OMISE_WEBHOOK_SECRET 不是合法的 Base64 字符串")
        return False, "not_configured"

    signed_payload = f"{timestamp_header}.{raw_body}".encode("utf-8") if isinstance(raw_body, str) \
        else b"%s.%s" % (str(timestamp_header).encode("utf-8"), raw_body)
    expected = hmac.new(key, signed_payload, hashlib.sha256).digest()

    # 轮换期间 header 含多个逗号分隔的签名, 任一匹配即通过(常量时间比较)
    for sig in str(signature_header).split(","):
        sig = sig.strip()
        if not sig:
            continue
        try:
            provided = bytes.fromhex(sig)
        except ValueError:
            continue
        if hmac.compare_digest(provided, expected):
            return True, "ok"
    return False, "bad_signature"


def _mark_paid(payment):
    """支付成功: 标记已支付; 幂等, 不会重复续期/建租户"""
    if payment.status == "paid":
        return payment, False

    now = timezone.now()

    # signup 订单: 付费成功 -> 创建租户 + 绑定注册用户为租户经理(只在首次建)
    if payment.purpose == "signup":
        changed = _create_tenant_from_signup(payment)
        payment.status = "paid"
        payment.paid_at = now
        payment.save(update_fields=["status", "paid_at"])
        return payment, changed

    tenant = payment.tenant
    if tenant is None:
        payment.status = "failed"
        payment.save(update_fields=["status"])
        return payment, False

    # 新到期时间 = max(当前到期时间, now) + 续费天数
    base = tenant.expire_time if tenant.expire_time and tenant.expire_time > now else now
    new_expire = base + timedelta(days=payment.extend_days or _renew_days())
    tenant.expire_time = new_expire
    tenant.is_active = True  # 续费即恢复启用(若是被停用)
    tenant.save(update_fields=["expire_time", "is_active"])

    payment.status = "paid"
    payment.paid_at = now
    payment.save(update_fields=["status", "paid_at"])
    logger.info("[PAYMENT] tenant=%s charge=%s 续费成功, 到期时间 -> %s", tenant.name, payment.charge_id, new_expire)
    return payment, True


def _gen_tenant_code():
    """生成唯一 4 位数字租户标识(0000-9999, 撞了重试)"""
    while True:
        code = f"{random.randint(0, 9999):04d}"
        if not Tenant.objects.filter(tenant_code=code).exists():
            return code


def _create_tenant_from_signup(payment):
    """signup 订单支付成功: 创建 Tenant + 绑定注册用户为 tenant_manager + 授全套权限(幂等)
    返回 True=本次创建; False=已存在租户(幂等, 不重复建)
    """
    from dvadmin.system.models import Users
    user = payment.signup_user
    if user is None:
        logger.warning("[PAYMENT] signup charge %s 无注册用户, 无法建租户", payment.charge_id)
        return False
    with transaction.atomic():
        refreshed = Users.objects.select_for_update().get(id=user.id)
        # 幂等: 用户已有租户则不再建
        if refreshed.tenant and Tenant.objects.filter(id=refreshed.tenant_id).exists():
            payment.tenant = refreshed.tenant
            payment.save(update_fields=["tenant"])
            return False
        activated = _activate_signup_user(refreshed, extend_days=payment.extend_days, paid=True)
        if activated is not None:
            payment.tenant = activated.tenant
            payment.save(update_fields=["tenant"])
            logger.info("[PAYMENT] signup 建租户成功 tenant=%s code=%s user=%s",
                        activated.tenant.name, activated.tenant.tenant_code, activated.username)
            return True
        return False


# 新建租户时的飞书群机器人通知(仅内部可见, 非业务数据)
FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/2cd9fdd0-0fea-42f9-86d2-e76d108ae132"


def send_tenant_created_notice(tenant, user, paid=False):
    """租户创建成功后向飞书群机器人推送通知(失败仅记日志, 不影响业务)"""
    try:
        text = (
            "🎉 新租户已开通\n"
            f"公司名称: {tenant.name}\n"
            f"租户标识: {tenant.tenant_code}\n"
            f"开通方式: {'付费' if paid else '免付费'}\n"
            f"经理账号: {user.username}\n"
            f"联系人: {user.name or tenant.contact_name or '-'}\n"
            f"联系电话: {user.mobile or '-'}\n"
        )
        requests.post(FEISHU_WEBHOOK_URL, json={"msg_type": "text", "content": {"text": text}}, timeout=8)
        logger.info("[FEISHU] 已通知新租户开通 tenant=%s user=%s", tenant.name, user.username)
    except Exception as e:
        logger.warning("[FEISHU] 推送租户开通通知失败 tenant=%s: %s", getattr(tenant, "name", "?"), e)


def _create_sample_property(tenant, user):
    """新租户开通后插入一条示例房源, 让用户有参考(可删除); 失败不影响建租户"""
    try:
        from dvadmin.property.models import Property
        from datetime import date
        from calendar import monthrange

        today = date.today()
        # 起租=今天, 结束=下月同一天(演示用), 到期后用户可改
        def _next_month(d):
            _, last = monthrange(d.year, d.month)
            y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
            day = min(d.day, last)
            return date(y, m, day)

        if Property.objects.filter(tenant=tenant).exists():
            return
        Property.objects.create(
            tenant=tenant,
            name=_("Sample Property (delete me)"),
            rent_amount=10000,
            remind_day=today.day,
            pay_period="Monthly",
            rent_start=today,
            rent_end=_next_month(today),
            owner=user,
            memo=_(
                "This is a sample property to help you learn how to add and configure properties. "
                "You can delete it after creating your own property."
            ),
        )
        logger.info("[SIGNUP] 已为新租户 %s 创建示例房源", tenant.name)
    except Exception as e:
        logger.warning("[SIGNUP] 创建示例房源失败 tenant=%s: %s", getattr(tenant, "name", "?"), e)


def _on_tenant_created(tenant, user, paid=False):
    """新租户开通后的善后: 飞书通知 + 示例房源(全部幂等, 失败仅记日志)"""
    send_tenant_created_notice(tenant, user, paid=paid)
    _create_sample_property(tenant, user)


def _activate_signup_user(user, extend_days=None, paid=False):
    """给已登记的注册用户创建租户并绑定 tenant_manager + 全套角色权限(幂等, 可复用)
    - 供 signup 付费成功(_create_tenant_from_signup) 与 超管关闭付费开关后的免付费开通共用
    - paid=True(付费开通)/False(免付费), 仅用于飞书通知文案
    返回: 更新后的 User 实例(带 tenant); 已存在租户也返回 User; 非法/未授权返回 None
    """
    from dvadmin.system.models import Users
    from dvadmin.tenant.org_chart import ensure_tenant_tier_roles

    if user is None:
        return None
    if not getattr(user, "is_active", False):
        logger.warning("[SIGNUP] 未验证邮箱的用户尝试开通租户 user=%s", getattr(user, "username", "?"))
        return None
    with transaction.atomic():
        user = Users.objects.select_for_update().get(id=user.id)
        if user.tenant and Tenant.objects.filter(id=user.tenant_id).exists():
            return user

        company = getattr(user, "name", "") or user.username
        tenant = Tenant.objects.create(
            name=company,
            tenant_code=_gen_tenant_code(),
            contact_name=company,
            contact_phone=user.mobile or "",
            plan_type="paid",
            is_active=True,
            expire_time=timezone.now() + timedelta(days=extend_days or _renew_days()),
            referral_code=Tenant.make_referral_code(),
            referrer_tenant=user.referrer_tenant,
        )
        # 创建/授权该租户三角色 + 按钮/菜单权限
        roles = ensure_tenant_tier_roles(tenant)
        user.tenant = tenant
        user.user_type = 0
        user.role.add(roles["manager"])
        user.current_role = roles["manager"]
        user.save()
        # 事务提交后发飞书通知(失败仅记日志, 不影响业务); 事务回滚则不会发送
        transaction.on_commit(lambda: _on_tenant_created(tenant, user, paid=paid))
    return user


def _mark_failed(payment, via_omise=True):
    """支付失败/超时: 将该 charge 在 Omise 标记为 failed + 本地记录失败(幂等)"""
    if payment.status == "failed":
        return payment, False
    if via_omise and not _is_dev_mode() and payment.status == "pending":
        secret = getattr(settings, "OMISE_SECRET_KEY", "")
        if secret:
            try:
                resp = requests.post(
                    f"{OMISE_API_BASE}/charges/{payment.charge_id}/mark_as_failed",
                    auth=(secret, ""),
                    timeout=15,
                )
                if resp.status_code == 200:
                    logger.info("[PAYMENT] 已将 charge 标记为失败: %s", payment.charge_id)
                else:
                    logger.warning("[PAYMENT] Omise 标记失败失败 %s: %s", resp.status_code, resp.text[:200])
            except requests.RequestException as e:
                logger.warning("[PAYMENT] Omise 标记失败请求出错: %s", e)
    payment.status = "failed"
    payment.save(update_fields=["status"])
    logger.info("[PAYMENT] tenant=%s charge=%s 支付失败/超时", payment.tenant.name if payment.tenant else "-", payment.charge_id)
    return payment, True


def _is_expired(payment):
    """该 pending charge 是否已超过超时时间"""
    if payment.status != "pending":
        return False
    if payment.create_datetime is None:
        return False
    now = timezone.now()
    return now - payment.create_datetime > timedelta(seconds=_expire_seconds())


def _create_omise_charge(amount_satang, metadata=None, expire_seconds=None):
    """调用 Omise REST API 创建 PromptPay charge, 返回 (ok, data|error)"""
    secret = getattr(settings, "OMISE_SECRET_KEY", "")
    if not secret:
        return False, {"error": "Omise 未配置密钥"}
    api_version = getattr(settings, "OMISE_API_VERSION", "2019-05-29")
    payload = {
        "amount": amount_satang,
        "currency": "thb",
        "source[type]": "promptpay",
        "metadata[charge_for]": "pronotify_renewal",
    }
    if expire_seconds:
        payload["expire"] = expire_seconds
    for k, v in (metadata or {}).items():
        payload[f"metadata[{k}]"] = v
    try:
        resp = requests.post(
            f"{OMISE_API_BASE}/charges",
            auth=(secret, ""),
            data=payload,
            headers={"Omise-Version": api_version},
            timeout=20,
        )
    except requests.RequestException as e:
        logger.warning("[PAYMENT] Omise 请求失败: %s", e)
        return False, {"error": "无法连接 Omise"}
    if resp.status_code not in (200, 201):
        logger.warning("[PAYMENT] Omise 创建 charge 失败 %s: %s", resp.status_code, resp.text[:300])
        return False, {"error": f"Omise 创建 charge 失败({resp.status_code})"}
    data = resp.json()
    return True, data


def _dev_qr_svg(amount_thb):
    """开发模式: 生成一个带金额信息的测试二维码(SVG data URI)"""
    text = f"pronotify renewal THB {amount_thb}"
    color = "#409EFF"
    grid = 5
    n = 12
    qr_rows = []
    for y in range(n):
        row = []
        for x in range(n):
            h = hashlib.md5(f"{text}:{x}:{y}".encode()).hexdigest()
            row.append("1" if int(h[0], 16) % 2 == 0 else "0")
        qr_rows.append(row)
    rects = []
    for y in range(n):
        for x in range(n):
            if qr_rows[y][x] == "1":
                rects.append(f'<rect x="{x*grid}" y="{y*grid}" width="{grid}" height="{grid}" fill="{color}"/>')
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{n*grid}" height="{n*grid}" viewBox="0 0 {n*grid} {n*grid}">'
        f'<rect width="100%" height="100%" fill="white"/>{"".join(rects)}</svg>'
    )
    return "data:image/svg+xml;base64," + __import__("base64").b64encode(svg.encode("utf-8")).decode("utf-8")


class PaymentConfigView(APIView):
    """支付配置(租户端支付页 / 超管端展示金额均可用)
    返回: { enabled, amount_thb, amount_satang, currency, renew_days, dev_mode, qr_available }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from dvadmin.tenant.signup import signup_requires_payment
        return SuccessResponse(data={
            "enabled": _payment_enabled(),
            "amount_thb": int(getattr(settings, "PAYMENT_AMOUNT_THB", 0) or 0),
            "amount_satang": _amount_satang(),
            "currency": "thb",
            "renew_days": _renew_days(),
            "expire_seconds": _expire_seconds(),
            "dev_mode": _is_dev_mode(),
            "test_mode": _is_test_mode(),
            "qr_available": True,
            "signup_require_payment": signup_requires_payment(),
        })


class CreatePromptPayView(APIView):
    """发起一笔 PromptPay 续费 charge(当前登录用户所属租户)"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _payment_enabled():
            return ErrorResponse(msg=_("Payment gateway is not enabled"))
        tenant = getattr(request.user, "tenant", None)
        if tenant is None:
            return ErrorResponse(msg=_("Your account has no tenant, cannot renew"))
        if not request.user.is_superuser and not request.user.role.filter(key="tenant_manager").exists():
            return ErrorResponse(msg=_("Only tenant managers can renew"))

        amount_satang = _amount_satang()
        if amount_satang <= 0:
            return ErrorResponse(msg=_("Renewal amount is not configured"))

        # 取消该租户仍在等待中的 charge(避免重复二维码)
        for p in TenantPayment.objects.filter(tenant=tenant, status="pending"):
            p.status = "failed"
            p.save(update_fields=["status"])

        if _is_dev_mode():
            charge_id = f"dev_{uuid.uuid4().hex[:12]}"
            qr_url = _dev_qr_svg(int(amount_satang / 100))
        else:
            ok, data = _create_omise_charge(amount_satang, metadata={"tenant_id": tenant.id}, expire_seconds=_expire_seconds())
            if not ok:
                return ErrorResponse(msg=data.get("error", _("Failed to create charge")))
            charge_id = data.get("id")
            qr_url = (data.get("source") or {}).get("scannable_code", {}).get("image", {}).get("download_uri")
            if not qr_url:
                return ErrorResponse(msg=_("Omise did not return a QR code"))

        payment = TenantPayment.objects.create(
            tenant=tenant,
            charge_id=charge_id,
            amount=amount_satang,
            currency="thb",
            status="pending",
            extend_days=_renew_days(),
        )
        logger.info("[PAYMENT] 创建续费 charge tenant=%s charge=%s dev=%s", tenant.name, charge_id, _is_dev_mode())
        return SuccessResponse(data={
            "payment_id": payment.id,
            "charge_id": charge_id,
            "qr_code_url": qr_url,
            "amount_thb": int(amount_satang / 100),
            "amount_satang": amount_satang,
            "currency": "thb",
            "renew_days": _renew_days(),
            "dev_mode": _is_dev_mode(),
            "expire_seconds": _expire_seconds(),
        })


class CreateSignupPromptPayView(APIView):
    """新注册用户发起第一笔 PromptPay 付费订单(signup, 未建租户)
    - 仅限已激活邮箱验证但未建租户的注册用户(登录账号即注册邮箱)
    - 一个注册用户最多一笔成功 signup 订单(key), 已建租户则拒绝
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _payment_enabled():
            return ErrorResponse(msg=_("Payment gateway is not enabled"))
        user = request.user
        if user.is_superuser or user.tenant is not None:
            return ErrorResponse(msg=_("This account already has a tenant, no need to sign up"))
        company = user.name or user.username
        if not company:
            return ErrorResponse(msg=_("Company name is missing"))
        again, ok_data = _has_activated_signup(user)
        if again:
            return ErrorResponse(msg=_("Already paid and activated, please sign in"))

        amount_satang = _amount_satang()
        if amount_satang <= 0:
            return ErrorResponse(msg=_("Renewal amount is not configured"))

        # 取消该用户仍在等待中的 signup charge(避免重复二维码)
        for p in TenantPayment.objects.filter(signup_user=user, status="pending"):
            p.status = "failed"
            p.save(update_fields=["status"])

        if _is_dev_mode():
            charge_id = f"dev_{uuid.uuid4().hex[:12]}"
            qr_url = _dev_qr_svg(int(amount_satang / 100))
        else:
            ok, data = _create_omise_charge(amount_satang, metadata={"signup_user": user.id}, expire_seconds=_expire_seconds())
            if not ok:
                return ErrorResponse(msg=data.get("error", _("Failed to create charge")))
            charge_id = data.get("id")
            qr_url = (data.get("source") or {}).get("scannable_code", {}).get("image", {}).get("download_uri")
            if not qr_url:
                return ErrorResponse(msg=_("Omise did not return a QR code"))

        payment = TenantPayment.objects.create(
            purpose="signup",
            signup_user=user,
            tenant=None,
            charge_id=charge_id,
            amount=amount_satang,
            currency="thb",
            status="pending",
            extend_days=_renew_days(),
        )
        logger.info("[PAYMENT] 创建 signup charge user=%s charge=%s dev=%s", user.username, charge_id, _is_dev_mode())
        return SuccessResponse(data={
            "payment_id": payment.id,
            "charge_id": charge_id,
            "qr_code_url": qr_url,
            "amount_thb": int(amount_satang / 100),
            "amount_satang": amount_satang,
            "currency": "thb",
            "renew_days": _renew_days(),
            "dev_mode": _is_dev_mode(),
            "expire_seconds": _expire_seconds(),
        })


def _has_activated_signup(user):
    """该注册用户是否已有一笔成功的 signup 订单(或已建租户)"""
    if user.tenant is not None:
        return True, None
    return TenantPayment.objects.filter(signup_user=user, purpose="signup", status="paid").exists(), None


class PaymentStatusView(APIView):
    """查询续费支付状态(按 charge_id)"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        charge_id = request.query_params.get("charge_id")
        if not charge_id:
            return ErrorResponse(msg=_("Missing charge_id"))
        payment = TenantPayment.objects.filter(charge_id=charge_id).first()
        if payment is None:
            return ErrorResponse(msg=_("Payment record does not exist"))
        user = request.user
        # 权限: 超管全过; renewal 订单须为本租户经理; signup 订单须为注册用户本人
        if not user.is_superuser:
            if payment.purpose == "signup":
                if payment.signup_user_id != user.id:
                    return ErrorResponse(msg=_("No permission to view this payment record"))
            else:
                tenant = getattr(user, "tenant", None)
                if tenant is None or payment.tenant_id != tenant.id:
                    return ErrorResponse(msg=_("No permission to view this payment record"))

        # 非 dev 模式: 主动向 Omise 查询一次最新状态
        if not _is_dev_mode() and payment.status == "pending":
            try:
                secret = getattr(settings, "OMISE_SECRET_KEY", "")
                resp = requests.get(
                    f"{OMISE_API_BASE}/charges/{charge_id}",
                    auth=(secret, ""),
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "successful":
                        _mark_paid(payment)
            except requests.RequestException as e:
                logger.warning("[PAYMENT] 查询 Omise charge 失败: %s", e)

        now = timezone.now()
        expired = _is_expired(payment)
        if expired:
            # 超时未支付: 自动在 Omise 标记失败 + 本地记录失败(幂等, 只做一次)
            _mark_failed(payment)
        return SuccessResponse(data={
            "payment_id": payment.id,
            "charge_id": payment.charge_id,
            "status": payment.status,
            "paid": payment.status == "paid",
            "failed": payment.status == "failed",
            "expired": bool(expired),
            "amount_thb": int(payment.amount / 100),
            "extend_days": payment.extend_days,
            "expire_seconds": _expire_seconds(),
            "new_expire_time": payment.tenant.expire_time.strftime("%Y-%m-%d %H:%M:%S") if payment.tenant and payment.tenant.expire_time else None,
        })


class PaymentWebhookView(APIView):
    """Omise webhook 回调: charge.complete -> 支付成功续期
    URL: POST /api/tenant/payment/webhook/

    安全: 优先校验 `Omise-Signature`(HMAC-SHA256)。若未配置 OMISE_WEBHOOK_SECRET,
    则退回「事件验证」——回查 Omise 该 charge 的真实状态, 仅 successful 才续期,
    杜绝伪造 body 直接续期/建租户。
    """

    permission_classes = []  # 无鉴权, 由 Omise 带签名回调(签名校验见 post)

    def post(self, request):
        signature = request.META.get("HTTP_OMISE_SIGNATURE", "")
        timestamp = request.META.get("HTTP_OMISE_SIGNATURE_TIMESTAMP", "")
        ok, reason = verify_webhook_signature(request.body, signature, timestamp)

        if not ok:
            # 已配置 secret 但签名不合法 -> 直接拒绝(401)
            if reason not in ("not_configured",):
                logger.warning("[PAYMENT] webhook 签名校验失败 reason=%s", reason)
                return HttpResponse(status=401)
            # 未配置 secret -> 事件验证兜底(见下), 绝不直接信任 body
            if not self._verify_with_omise(request.data):
                logger.warning("[PAYMENT] webhook 未配置签名密钥且事件验证未通过, 拒绝")
                return HttpResponse(status=401)

        event = request.data
        if not isinstance(event, dict):
            return SuccessResponse(data={"ok": False})
        key = event.get("key")
        data = event.get("data") or {}
        charge_id = data.get("id") or ""
        logger.info("[PAYMENT] webhook event=%s charge=%s", key, charge_id)
        if key == "charge.complete":
            payment = TenantPayment.objects.filter(charge_id=charge_id).first()
            if payment is None:
                logger.warning("[PAYMENT] webhook 找不到 charge %s", charge_id)
                return SuccessResponse(data={"ok": False, "error": "charge not found"})
            if data.get("status") == "successful":
                _mark_paid(payment)
            else:
                _mark_failed(payment, via_omise=False)
        elif key == "charge.failed":
            payment = TenantPayment.objects.filter(charge_id=charge_id).first()
            if payment is not None:
                _mark_failed(payment, via_omise=False)
        return SuccessResponse(data={"ok": True})

    def _verify_with_omise(self, event):
        """
        事件验证兜底(未配置 OMISE_WEBHOOK_SECRET 时): 拿 body 里的 charge_id 回查 Omise,
        仅当该 charge 在 Omise 侧确认为 successful 才信任, 否则拒绝。防止伪造 body 直接续期/建租户。
        """
        if not isinstance(event, dict):
            return False
        data = event.get("data") or {}
        charge_id = data.get("id") or ""
        if not charge_id:
            return False
        secret = getattr(settings, "OMISE_SECRET_KEY", "") or ""
        if not secret:
            return False
        try:
            resp = requests.get(
                f"{OMISE_API_BASE}/charges/{charge_id}",
                auth=(secret, ""),
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json().get("status") == "successful"
        except requests.RequestException as e:
            logger.warning("[PAYMENT] webhook 事件验证回查失败: %s", e)
        return False


class SimulatePayView(APIView):
    """开发/测试模式专用: 模拟某笔 charge 支付成功(等价于触发 webhook)
    - dev 模式(无密钥)或 test 模式(Omise test 密钥)可用; live 模式禁用"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not (_is_dev_mode() or _is_test_mode()):
            return ErrorResponse(msg=_("Not in dev/test mode, cannot simulate"))
        charge_id = request.data.get("charge_id")
        if not charge_id:
            return ErrorResponse(msg=_("Missing charge_id"))
        payment = TenantPayment.objects.filter(charge_id=charge_id).first()
        if payment is None:
            return ErrorResponse(msg=_("Payment record does not exist"))
        # 权限: 超管全过; renewal 订单须为本租户; signup 订单须为注册用户本人
        if not request.user.is_superuser:
            if payment.purpose == "signup":
                if payment.signup_user_id != request.user.id:
                    return ErrorResponse(msg=_("No permission to operate this payment record"))
            else:
                tenant = getattr(request.user, "tenant", None)
                if tenant is None or payment.tenant_id != tenant.id:
                    return ErrorResponse(msg=_("No permission to operate this payment record"))
        payment, changed = _mark_paid(payment)
        return SuccessResponse(data={
            "ok": True,
            "paid": payment.status == "paid",
            "changed": changed,
            "new_expire_time": payment.tenant.expire_time.strftime("%Y-%m-%d %H:%M:%S") if payment.tenant and payment.tenant.expire_time else None,
        })
