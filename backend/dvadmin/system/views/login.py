import base64
import hashlib
from datetime import datetime, timedelta
from captcha.views import CaptchaStore, captcha_image
from django.contrib import auth
from dvadmin.system.utils.svg_captcha import generate_svg, svg_to_data_uri
from django.contrib.auth import login
from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Q
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from django.conf import settings
from application import dispatch
from dvadmin.system.models import Users, SignupToken
from dvadmin.utils.json_response import ErrorResponse, DetailResponse
from dvadmin.utils.request_util import save_login_log
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.validator import CustomValidationError

# 连续输错多少次的账号临时锁定阈值(默认值, 可由 system_config: login.* 覆盖)
LOGIN_MAX_ATTEMPTS = 5
# 临时锁定时长(分钟), 到期自动解锁
LOGIN_LOCK_MINUTES = 60
# 接口限流(同一 IP+账号): 60 秒窗口内失败次数与拦截时长
RATE_WINDOW_SECONDS = 60
RATE_MAX_FAILS = 10
RATE_BLOCK_SECONDS = 300

# 登录安全设置的 system_config 键位(父级 login): (配置键, 标题, 默认值)
APPCONF_LOGIN_SETTINGS = [
    ("login.max_attempts", "连续输错锁定阈值(次数)", LOGIN_MAX_ATTEMPTS),
    ("login.lock_minutes", "临时锁定时长(分钟)", LOGIN_LOCK_MINUTES),
    ("login.rate_window_seconds", "限流窗口(秒)", RATE_WINDOW_SECONDS),
    ("login.rate_max_fails", "窗口内最大失败次数", RATE_MAX_FAILS),
    ("login.rate_block_seconds", "限流拦截时长(秒)", RATE_BLOCK_SECONDS),
]


def _login_setting(config_key, default):
    """读取单个登录安全配置(带正数校验与默认值兜底)"""
    try:
        val = dispatch.get_system_config_values(config_key)
        if val is None or str(val).strip() == "":
            return default
        iv = int(val)
        return iv if iv > 0 else default
    except (TypeError, ValueError):
        return default


def login_settings():
    """返回当前生效的登录安全设置(全配置键 → 值)"""
    return {ck: _login_setting(ck, default) for ck, _title, default in APPCONF_LOGIN_SETTINGS}


def ensure_login_config_row(config_key, title, default):
    """确保 system_config 中存在对应配置行(父级 login / 子级即可), 返回该行"""
    from dvadmin.system.models import SystemConfig

    parent_key, _, child_key = config_key.rpartition(".")
    parent, _ = SystemConfig.objects.get_or_create(
        key=parent_key, parent_id=None,
        defaults={"title": "登录配置", "form_item_type": 0, "sort": 2, "status": True, "value": ""},
    )
    obj, _ = SystemConfig.objects.get_or_create(
        key=child_key, parent=parent,
        defaults={"title": title, "form_item_type": 10, "sort": 20, "status": True, "value": default},
    )
    return obj

_redis_client = None


def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or ""


def _get_redis():
    """懒加载 redis 客户端(限流用), 不可用返回 None(降级只靠账号级临时锁定)"""
    global _redis_client
    if _redis_client is None:
        try:
            from conf.env import REDIS_URL
            import redis
            _redis_client = redis.Redis.from_url(
                REDIS_URL, socket_timeout=1, socket_connect_timeout=1, decode_responses=True
            )
        except Exception:
            _redis_client = False
    return _redis_client or None


def _fail_key(request, username):
    return f"dvadmin:login_fail:{_client_ip(request)}|{str(username).lower()}"


def _block_key(request, username):
    return f"dvadmin:login_block:{_client_ip(request)}|{str(username).lower()}"


def _rate_blocked(request, username):
    rc = _get_redis()
    if not rc:
        return False
    try:
        return bool(rc.exists(_block_key(request, username)))
    except Exception:
        return False


def _record_login_failure(request, username, cfg):
    rc = _get_redis()
    if not rc:
        return
    try:
        key = _fail_key(request, username)
        n = rc.incr(key)
        if n == 1:
            rc.expire(key, cfg["login.rate_window_seconds"])
        if n >= cfg["login.rate_max_fails"]:
            rc.set(_block_key(request, username), "1", ex=cfg["login.rate_block_seconds"])
            rc.delete(key)
    except Exception:
        pass


class CaptchaView(APIView):
    authentication_classes = []
    permission_classes = []

    @swagger_auto_schema(
        responses={"200": openapi.Response("获取成功")},
        security=[],
        operation_id="captcha-get",
        operation_description="验证码获取",
    )
    def get(self, request):
        data = {}
        if dispatch.get_system_config_values("base.captcha_state"):
            # 深色 SVG 验证码: 答案存 CaptchaStore(兼容 LoginSerializer 校验), 图片返回 data URI
            svg_str, answer = generate_svg()
            # 生成唯一 hashkey(避免 collide 导致 duplicate key 错误)
            import uuid
            hashkey = ""
            while not hashkey or CaptchaStore.objects.filter(hashkey=hashkey).exists():
                hashkey = uuid.uuid4().hex
            store = CaptchaStore.objects.create(
                hashkey=hashkey,
                challenge=answer,
                response=answer,
                expiration=datetime.now() + timedelta(minutes=1),
            )
            data = {
                "key": store.id,  # 前端以 captchaKey 传回, 校验按 id 查
                "image_base": svg_to_data_uri(svg_str),
            }
        return DetailResponse(data=data)


class LoginSerializer(TokenObtainPairSerializer):
    """
    登录的序列化器:
    重写djangorestframework-simplejwt的序列化器
    """
    captcha = serializers.CharField(
        max_length=6, required=False, allow_null=True, allow_blank=True
    )

    class Meta:
        model = Users
        fields = "__all__"
        read_only_fields = ["id"]

    default_error_messages = {"no_active_account": _("Username/password incorrect")}

    def validate(self, attrs):
        request = self.context.get("request")
        captcha = self.initial_data.get("captcha", None)
        if dispatch.get_system_config_values("base.captcha_state"):
            if captcha is None:
                raise CustomValidationError(_("Verification code is required"))
            self.image_code = CaptchaStore.objects.filter(
                id=self.initial_data["captchaKey"]
            ).first()
            five_minute_ago = datetime.now() - timedelta(hours=0, minutes=5, seconds=0)
            if self.image_code and five_minute_ago > self.image_code.expiration:
                self.image_code and self.image_code.delete()
                raise CustomValidationError(_("Verification code has expired"))
            else:
                if self.image_code and (
                    self.image_code.response == captcha
                    or self.image_code.challenge == captcha
                ):
                    self.image_code and self.image_code.delete()
                else:
                    self.image_code and self.image_code.delete()
                    raise CustomValidationError(_("Image verification code is incorrect"))
        cfg = login_settings()
        # 接口限流: 同一 IP+账号 失败过多 -> 短时拦截
        if _rate_blocked(request, attrs.get("username", "")):
            raise CustomValidationError(_("Too many attempts. Try again later"))
        try:
            user = Users.objects.get(
                Q(username=attrs['username']) | Q(email=attrs['username']) | Q(mobile=attrs['username']))
        except Users.DoesNotExist:
            _record_login_failure(request, attrs['username'], cfg)
            raise CustomValidationError(_("Username/password incorrect"))
        except Users.MultipleObjectsReturned:
            raise CustomValidationError(_("Multiple matching accounts found. Contact admin"))

        # 分情况提示: 未验证邮箱 / 被停用 / 临时锁定
        if not user.is_active:
            verified = SignupToken.objects.filter(user=user, used=True).exists()
            if user.is_superuser or verified:
                raise CustomValidationError(_("This account has been disabled. Contact an administrator to unlock it."))
            raise CustomValidationError(_("Email not verified yet"))

        now = datetime.now()
        if user.login_locked_until and user.login_locked_until > now:
            minutes_left = int((user.login_locked_until - now).total_seconds() // 60) + 1
            raise CustomValidationError(_("Too many attempts. Retry in about {} min").format(minutes_left))
        elif user.login_locked_until:
            # 锁定已过期: 自动解锁, 清零计数
            user.login_locked_until = None
            user.login_error_count = 0
            user.save(update_fields=["login_locked_until", "login_error_count"])

        try:
            # 必须重置用户名为username,否则使用邮箱手机号登录会提示密码错误
            attrs['username'] = user.username
            data = super().validate(attrs)
            data["username"] = self.user.username
            data["name"] = self.user.name
            data["userId"] = self.user.id
            data["avatar"] = self.user.avatar
            data['user_type'] = self.user.user_type
            data['pwd_change_count'] = self.user.pwd_change_count
            data["language"] = getattr(self.user, 'language', 'zh-cn') or 'zh-cn'
            dept = getattr(self.user, 'dept', None)
            if dept:
                data['dept_info'] = {
                    'dept_id': dept.id,
                    'dept_name': dept.name,
                }
            role = getattr(self.user, 'role', None)
            if role:
                data['role_info'] = role.values('id', 'name', 'key')
            request.user = self.user
            # 记录登录日志
            save_login_log(request=request)
            user.login_error_count = 0
            user.login_locked_until = None
            user.save(update_fields=["login_error_count", "login_locked_until"])
            return {"code": 2000, "msg": _("Request successful"), "data": data}
        except Exception as e:
            _record_login_failure(request, user.username, cfg)
            user.login_error_count += 1
            if user.login_error_count >= cfg["login.max_attempts"]:
                # 达到阈值 -> 临时锁定(不修改 is_active, 保留已停用/未激活的区别)
                user.login_locked_until = now + timedelta(minutes=cfg["login.lock_minutes"])
                user.login_error_count = 0
                user.save(update_fields=["login_locked_until", "login_error_count"])
                raise CustomValidationError(_("Too many attempts. Retry in about {} min").format(cfg["login.lock_minutes"]))
            user.save(update_fields=["login_error_count"])
            remaining = cfg["login.max_attempts"] - user.login_error_count
            raise CustomValidationError(_("Wrong username or password. {} tries left, then locked for {} min").format(remaining, cfg["login.lock_minutes"]))


class LoginView(TokenObtainPairView):
    """
    登录接口
    """
    serializer_class = LoginSerializer
    permission_classes = []

    # def post(self, request, *args, **kwargs):
    #     # username可能携带的不止是用户名，可能还是用户的其它唯一标识 手机号 邮箱
    #     username = request.data.get('username',None)
    #     if username is None:
    #         return ErrorResponse(msg="参数错误")
    #     password = request.data.get('password',None)
    #     if password is None:
    #         return ErrorResponse(msg="参数错误")
    #     captcha = request.data.get('captcha',None)
    #     if captcha is None:
    #         return ErrorResponse(msg="参数错误")
    #     captchaKey = request.data.get('captchaKey',None)
    #     if captchaKey is None:
    #         return ErrorResponse(msg="参数错误")
    #     if dispatch.get_system_config_values("base.captcha_state"):
    #         if captcha is None:
    #             raise CustomValidationError("验证码不能为空")
    #         self.image_code = CaptchaStore.objects.filter(
    #             id=captchaKey
    #         ).first()
    #         five_minute_ago = datetime.now() - timedelta(hours=0, minutes=5, seconds=0)
    #         if self.image_code and five_minute_ago > self.image_code.expiration:
    #             self.image_code and self.image_code.delete()
    #             raise CustomValidationError("验证码过期")
    #         else:
    #             if self.image_code and (
    #                     self.image_code.response == captcha
    #                     or self.image_code.challenge == captcha
    #             ):
    #                 self.image_code and self.image_code.delete()
    #             else:
    #                 self.image_code and self.image_code.delete()
    #                 raise CustomValidationError("图片验证码错误")
    #     try:
    #         # 手动通过 user 签发 jwt-token
    #         user = Users.objects.get(username=username)
    #     except:
    #         return DetailResponse(msg='该账号未注册')
    #     # 获得用户后，校验密码并签发token
    #     print(make_password(password),user.password)
    #     if check_password(make_password(password),user.password):
    #         return DetailResponse(msg='密码错误')
    #     result = {
    #        "name":user.name,
    #         "userId":user.id,
    #         "avatar":user.avatar,
    #     }
    #     dept = getattr(user, 'dept', None)
    #     if dept:
    #         result['dept_info'] = {
    #             'dept_id': dept.id,
    #             'dept_name': dept.name,
    #             'dept_key': dept.key
    #         }
    #     role = getattr(user, 'role', None)
    #     if role:
    #         result['role_info'] = role.values('id', 'name', 'key')
    #     refresh = LoginSerializer.get_token(user)
    #     result["refresh"] = str(refresh)
    #     result["access"] = str(refresh.access_token)
    #     # 记录登录日志
    #     request.user = user
    #     save_login_log(request=request)
    #     return DetailResponse(data=result,msg="获取成功")


class LoginTokenSerializer(TokenObtainPairSerializer):
    """
    登录的序列化器:
    """

    class Meta:
        model = Users
        fields = "__all__"
        read_only_fields = ["id"]

    default_error_messages = {"no_active_account": _("账号/密码不正确")}

    def validate(self, attrs):
        if not getattr(settings, "LOGIN_NO_CAPTCHA_AUTH", False):
            return {"code": 4000, "msg": _("This interface is not yet available"), "data": None}
        data = super().validate(attrs)
        data["name"] = self.user.name
        data["userId"] = self.user.id
        return {"code": 2000, "msg": _("Request successful"), "data": data}


class LoginTokenView(TokenObtainPairView):
    """
    登录获取token接口
    """

    serializer_class = LoginTokenSerializer
    permission_classes = []


class LogoutView(APIView):
    def post(self, request):
        return DetailResponse(msg=_("Logout successful"))


class ApiLoginSerializer(CustomModelSerializer):
    """接口文档登录-序列化器"""

    username = serializers.CharField()
    password = serializers.CharField()

    class Meta:
        model = Users
        fields = ["username", "password"]


class ApiLogin(APIView):
    """接口文档的登录接口"""

    serializer_class = ApiLoginSerializer
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user_obj = auth.authenticate(
            request,
            username=username,
            password=hashlib.md5(password.encode(encoding="UTF-8")).hexdigest(),
        )
        if user_obj:
            login(request, user_obj)
            return redirect("/")
        else:
            return ErrorResponse(msg=_("Username/password incorrect"))
