# -*- coding: utf-8 -*-
"""
忘记密码自助重置(免登录, AllowAny):
- POST /api/system/user_reset/send/   {email} → 发送含一次性链接的邮件(30分钟, 单次)
- POST /api/system/user_reset/confirm/ {token, password} → 校验并重设密码
对外统一返回"已发送", 避免账号枚举
"""
import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from dvadmin.system.models import PasswordResetToken, Users
from dvadmin.utils.json_response import ErrorResponse, SuccessResponse

logger = logging.getLogger(__name__)

TOKEN_TTL_MINUTES = 30


def _find_user(email: str):
    email = (email or "").strip().lower()
    if not email:
        return None
    return (Users.objects.filter(username__iexact=email).first()
            or Users.objects.filter(email__iexact=email).first())


class SendResetEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = str(request.data.get("email") or "").strip()
        user = _find_user(email)
        # 用户不存在也返回成功(防枚举); 存在但无可用邮箱则静默跳过
        if user is None or not (user.email or user.username):
            return SuccessResponse(data={}, msg=_("If this email exists, a reset link has been sent"))
        to_email = user.email or user.username
        # 作废旧令牌
        PasswordResetToken.objects.filter(user=user, used=False).update(used=True)
        token = secrets.token_urlsafe(32)
        PasswordResetToken.objects.create(
            user=user,
            token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
            expires_at=timezone.now() + timedelta(minutes=TOKEN_TTL_MINUTES),
        )
        link = f"{settings.FRONTEND_BASE}/#/login?token={token}"
        subject = _("Reset your password - proNotify")
        greeting = _("Hello,")
        body = _("Please click the link below to reset your password (valid for {} minutes):\n\n{}").format(
            TOKEN_TTL_MINUTES, link)
        footer = _("If you did not request this, please ignore this email.")
        text = f"{greeting}\n\n{body}\n\n{footer}"
        html_greeting = _("Hello,")
        html_body = _("Please click the link below to reset your password (<b>{} minutes</b>):").format(
            TOKEN_TTL_MINUTES)
        html = (f"<p>{html_greeting}</p>"
                f"<p>{html_body}</p>"
                f"<p><a href='{link}'>{link}</a></p>"
                f"<p>{footer}</p>")
        try:
            send_mail(subject, text, settings.DEFAULT_FROM_EMAIL, [to_email],
                      html_message=html, fail_silently=False)
        except Exception as e:  # 邮件失败不阻塞, 记录日志
            logger.error("发送重置邮件失败 to=%s: %s", to_email, e)
        return SuccessResponse(data={}, msg=_("If this email exists, a reset link has been sent"))


class ConfirmResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = str(request.data.get("token") or "").strip()
        if not token:
            return ErrorResponse(msg=_("Reset link is invalid or expired"))
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        obj = PasswordResetToken.objects.select_related("user").filter(token_hash=token_hash, used=False).first()
        if obj is None:
            return ErrorResponse(msg=_("Reset link is invalid or expired"))
        if timezone.now() > obj.expires_at:
            obj.used = True
            obj.save(update_fields=["used"])
            return ErrorResponse(msg=_("Reset link has expired, please request a new one"))
        password = str(request.data.get("password") or "")
        if len(password) < 8 or not (any(c.isalpha() for c in password) and any(c.isdigit() for c in password)):
            return ErrorResponse(msg=_("Password must be at least 8 characters and contain both letters and numbers"))
        user = obj.user
        user.set_password(password)
        user.login_error_count = 0
        user.save(update_fields=["password", "login_error_count"])
        obj.used = True
        obj.save(update_fields=["used"])
        return SuccessResponse(data={}, msg=_("Password reset, sign in with the new password"))