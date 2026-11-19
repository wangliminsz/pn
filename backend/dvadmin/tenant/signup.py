# -*- coding: utf-8 -*-
"""
自助注册(邮箱验证 + 付费后建租户)
- POST /api/tenant/signup/send/    {email, company, contact_phone?, password} → 发送验证邮件
- POST /api/tenant/signup/verify/  {token} → 激活账号(24h 一次性)
- 付费成功由 payment._mark_paid 的 signup 分支完成建租户
"""
import hashlib
import logging
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from dvadmin.system.models import SignupToken, Users
from dvadmin.tenant.models import Tenant
from dvadmin.utils.json_response import ErrorResponse, SuccessResponse

logger = logging.getLogger(__name__)

SIGNUP_TOKEN_TTL_HOURS = 24
EMAIL_RE = re.compile(r"^[A-Za-z0-9@\._\-+]+$")


def signup_requires_payment():
    """自助注册是否需要付费后建租户(system_config: signup.require_payment)
    true=必须付费(默认); false=验证邮箱后可直接开通租户"""
    from dvadmin.system.models import SystemConfig
    row = SystemConfig.objects.filter(key="signup.require_payment").first()
    if row is None or row.value is None:
        return True
    # value 是 JSONField, 读回可能是 bool 或字符串
    if isinstance(row.value, bool):
        return row.value
    return str(row.value).strip().lower() not in ("", "0", "false", "no", "off", "none", "null")


def _resolve_referral(referral_code):
    """解析推荐码 → 存在且启用(非自身)的租户; 返回 Tenant|None"""
    code = (referral_code or "").strip().upper()
    if not code:
        return None
    return Tenant.objects.filter(referral_code__iexact=code, is_active=True).first()


class SendSignupView(APIView):
    """自助注册: 校验 → 建待激活用户 → 发验证邮件(24h 一次性链接)"""

    permission_classes = [AllowAny]

    def post(self, request):
        email = str(request.data.get("email") or "").strip().lower()
        company = str(request.data.get("company") or "").strip()
        password = str(request.data.get("password") or "")
        contact_phone = str(request.data.get("contact_phone") or "").strip()
        referral_code = str(request.data.get("referral_code") or "").strip()

        if not email or not re.fullmatch(EMAIL_RE, email) or "@" not in email or "." not in email.split("@")[-1]:
            return ErrorResponse(msg=_("Please enter a valid email address"))
        if not company:
            return ErrorResponse(msg=_("Company name is required"))
        if len(password) < 8 or not (any(c.isalpha() for c in password) and any(c.isdigit() for c in password)):
            return ErrorResponse(msg=_("Password must be at least 8 characters with letters and numbers"))
        # 登录账号强制邮箱: username = email(全项目约定)
        if Users.objects.filter(username__iexact=email).exists():
            return ErrorResponse(msg=_("This email is already registered. Please sign in"))

        # 推荐码: 解析(非法/不存在的码忽略, 不阻塞注册)
        referrer = _resolve_referral(referral_code) if referral_code else None

        # 已存在待激活记录则复用(重发邮件), 避免重复建用户
        user = Users.objects.filter(username__iexact=email).first()
        if user is None:
            user = Users(username=email)
            user.email = email
            user.name = company
            user.mobile = contact_phone or None
            user.tenant = None
            user.referrer_tenant = referrer
            user.is_active = False
            user.user_type = 1
            user.pwd_change_count = 1  # 自己设的密码, 无需首登强制改密
            user.set_password(password)  # 认证约定 set_password(明文), 登录时明文/md5 均可校验
            user.save()
        elif user.is_active:
            return ErrorResponse(msg=_("This email is already registered. Please sign in"))
        else:
            # 重发场景: 刷新密码与公司名, 推荐码以首次为准(不覆盖)
            user.name = company
            user.mobile = contact_phone or user.mobile
            if user.referrer_tenant is None:
                user.referrer_tenant = referrer
            user.pwd_change_count = 1
            user.set_password(password)
            user.save()

        # 作废旧令牌后再发
        SignupToken.objects.filter(user=user, used=False).update(used=True)
        token = secrets.token_urlsafe(32)
        SignupToken.objects.create(
            user=user,
            email=email,
            company=company,
            token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
            expires_at=timezone.now() + timedelta(hours=SIGNUP_TOKEN_TTL_HOURS),
        )
        link = f"{settings.FRONTEND_BASE}/#/signup/verify?token={token}"
        subject = _("Verify your email - proNotify")
        greeting = _("Hello,")
        body = _("Thank you for signing up for proNotify. Please click the link below to verify your email (valid for {} hours):\n\n{}").format(
            SIGNUP_TOKEN_TTL_HOURS, link)
        footer = _("After verification you can complete the payment and activate your account.")
        text = f"{greeting}\n\n{body}\n\n{footer}"
        html_body = _("Thank you for signing up for <b>proNotify</b>. Please click the link below to verify your email (<b>{} hours</b>):").format(
            SIGNUP_TOKEN_TTL_HOURS)
        html = (f"<p>{greeting}</p>"
                f"<p>{html_body}</p>"
                f"<p><a href='{link}'>{link}</a></p>"
                f"<p>{footer}</p>")
        try:
            send_mail(subject, text, settings.DEFAULT_FROM_EMAIL, [email],
                      html_message=html, fail_silently=False)
        except Exception as e:  # 邮件失败不阻塞, 记录日志
            logger.error("发送注册验证邮件失败 to=%s: %s", email, e)
        return SuccessResponse(data={"sent": True}, msg=_("Verification email sent, please check your inbox (valid for 24 hours)"))


class ActivateFreeView(APIView):
    """免付费直接开通租户(超管关闭"付费开通"开关后可用)
    已验证邮箱 + 未建租户的用户, 调用后直接创建租户并绑定 tenant_manager"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if signup_requires_payment():
            return ErrorResponse(msg=_("Please complete the payment activation first"))
        user = request.user
        # 复用 signup 付费成功后的同一套建租户逻辑(幂等)
        from dvadmin.tenant.payment import _activate_signup_user
        activated = _activate_signup_user(user)
        if activated is None:
            return ErrorResponse(msg=_("Activation failed, please retry later"))
        if activated.tenant is None:
            return ErrorResponse(msg=_("This account already has a tenant, please sign in directly"))
        user = activated
        company = getattr(user, "name", "") or user.username
        logger.info("[SIGNUP] 免付费开通租户 user=%s company=%s", user.username, company)
        return SuccessResponse(data={"tenant_id": user.tenant_id}, msg=_("Tenant activated, please sign in again"))


class VerifySignupView(APIView):
    """验证注册邮箱: token → 激活账号(24h 一次性, 防枚举)"""

    permission_classes = [AllowAny]

    def post(self, request):
        token = str(request.data.get("token") or "").strip()
        if not token:
            return ErrorResponse(msg=_("Invalid or expired verification link"))
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        obj = SignupToken.objects.select_related("user").filter(token_hash=token_hash, used=False).first()
        if obj is None:
            return ErrorResponse(msg=_("Invalid or expired verification link"))
        if timezone.now() > obj.expires_at:
            obj.used = True
            obj.save(update_fields=["used"])
            return ErrorResponse(msg=_("Verification link has expired. Please sign up again"))
        user = obj.user
        if user.is_active:
            return SuccessResponse(data={"email": obj.email, "company": obj.company},
                                   msg=_("This email is already verified, please complete the payment to activate your account"))
        user.is_active = True
        user.save(update_fields=["is_active"])
        obj.used = True
        obj.save(update_fields=["used"])
        logger.info("[SIGNUP] 邮箱验证成功 email=%s company=%s", obj.email, obj.company)
        return SuccessResponse(data={"email": obj.email, "company": obj.company}, msg=_("Email verified successfully"))