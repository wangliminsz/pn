import hashlib
import logging

from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from django.utils.translation import gettext as _
from django_restql.fields import DynamicSerializerMethodField
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db import connection
from django.db.models import Q
from application import dispatch
from dvadmin.tenant.models import Tenant
from dvadmin.system.models import Users, Role, Dept
from dvadmin.system.views.role import RoleSerializer
from dvadmin.utils.json_response import ErrorResponse, DetailResponse, SuccessResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.validator import CustomUniqueValidator
from dvadmin.utils.permission import SuperuserPermission
from dvadmin.utils.viewset import CustomModelViewSet

logger = logging.getLogger(__name__)


def recursion(instance, parent, result):
    new_instance = getattr(instance, parent, None)
    res = []
    data = getattr(instance, result, None)
    if data:
        res.append(data)
    if new_instance:
        array = recursion(new_instance, parent, result)
        res += array
    return res


class UserSerializer(CustomModelSerializer):
    """
    用户管理-序列化器
    """
    dept_name = serializers.CharField(source='dept.name', read_only=True)
    role_info = DynamicSerializerMethodField()
    dept_name_all = serializers.SerializerMethodField()
    tenant_name = serializers.CharField(source='tenant.name', read_only=True, default=None)

    class Meta:
        model = Users
        read_only_fields = ["id"]
        exclude = ["password"]
        extra_kwargs = {
            "post": {"required": False},
            "mobile": {"required": False},
        }

    def get_dept_name_all(self, instance):
        dept_name_all = recursion(instance.dept, "parent", "name")
        dept_name_all.reverse()
        return "/".join(dept_name_all)

    def get_role_info(self, instance, parsed_query):
        roles = instance.role.all()
        # You can do what ever you want in here
        # `parsed_query` param is passed to BookSerializer to allow further querying
        serializer = RoleSerializer(
            roles,
            many=True,
            parsed_query=parsed_query
        )
        return serializer.data


class UserCreateSerializer(CustomModelSerializer):
    """
    用户新增-序列化器
    """

    username = serializers.CharField(
        max_length=50,
        validators=[
            CustomUniqueValidator(queryset=Users.objects.all(), message=_("Username must be unique"))
        ],
    )
    password = serializers.CharField(
        required=False,
    )
    tenant = serializers.PrimaryKeyRelatedField(
        queryset=Tenant.objects.all(), required=False, allow_null=True, default=None
    )

    def validate_tenant(self, value):
        # 仅超级管理员允许绑定租户
        request = self.context.get('request')
        if request and not getattr(request.user, 'is_superuser', False):
            return None
        return value

    def validate_password(self, value):
        """
        对密码进行验证
        """
        md5 = hashlib.md5()
        md5.update(value.encode('utf-8'))
        md5_password = md5.hexdigest()
        return make_password(md5_password)

    def save(self, **kwargs):
        data = super().save(**kwargs)
        data.dept_belong_id = data.dept_id
        data.save()
        if not self.validated_data.get('manage_dept', None):
            data.manage_dept.add(data.dept_id)
        data.post.set(self.initial_data.get("post", []))
        return data

    class Meta:
        model = Users
        fields = "__all__"
        read_only_fields = ["id"]
        extra_kwargs = {
            "post": {"required": False},
            "mobile": {"required": False},
        }


class UserUpdateSerializer(CustomModelSerializer):
    """
    用户修改-序列化器
    """

    username = serializers.CharField(
        max_length=50,
        validators=[
            CustomUniqueValidator(queryset=Users.objects.all(), message=_("Username must be unique"))
        ],
    )
    tenant = serializers.PrimaryKeyRelatedField(
        queryset=Tenant.objects.all(), required=False, allow_null=True, default=None
    )

    def validate_tenant(self, value):
        # 仅超级管理员允许绑定租户
        request = self.context.get('request')
        if request and not getattr(request.user, 'is_superuser', False):
            return None
        return value

    def validate_is_active(self, value):
        """
        更改激活状态
        """
        if value:
            self.initial_data["login_error_count"] = 0
        return value

    def save(self, **kwargs):
        data = super().save(**kwargs)
        data.dept_belong_id = data.dept_id
        data.save()
        if not self.validated_data.get('manage_dept', None):
            data.manage_dept.add(data.dept_id)
        data.post.set(self.initial_data.get("post", []))
        return data

    class Meta:
        model = Users
        read_only_fields = ["id", "password"]
        fields = "__all__"
        extra_kwargs = {
            "post": {"required": False, "read_only": True},
            "mobile": {"required": False},
        }


class UserInfoUpdateSerializer(CustomModelSerializer):
    """
    用户修改-序列化器
    """
    mobile = serializers.CharField(
        max_length=50,
        validators=[
            CustomUniqueValidator(queryset=Users.objects.all(), message=_("Mobile number must be unique"))
        ],
        allow_blank=True
    )

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)

    class Meta:
        model = Users
        fields = ['email', 'mobile', 'avatar', 'name', 'gender']
        extra_kwargs = {
            "post": {"required": False, "read_only": True},
            "mobile": {"required": False},
        }


class ExportUserProfileSerializer(CustomModelSerializer):
    """
    用户导出 序列化器
    """

    last_login = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S", required=False, read_only=True
    )
    is_active = serializers.SerializerMethodField(read_only=True)
    dept_name = serializers.CharField(source="dept.name", default="")
    dept_owner = serializers.CharField(source="dept.owner", default="")
    gender = serializers.CharField(source="get_gender_display", read_only=True)

    def get_is_active(self, instance):
        return _("Enabled") if instance.is_active else _("Disabled")

    class Meta:
        model = Users
        fields = (
            "username",
            "name",
            "email",
            "mobile",
            "gender",
            "is_active",
            "last_login",
            "dept_name",
            "dept_owner",
        )


class UserProfileImportSerializer(CustomModelSerializer):
    password = serializers.CharField(read_only=True, required=False)

    def save(self, **kwargs):
        data = super().save(**kwargs)
        password = hashlib.new(
            "md5", str(self.initial_data.get("password", "admin123456")).encode(encoding="UTF-8")
        ).hexdigest()
        data.set_password(password)
        data.save()
        return data

    class Meta:
        model = Users
        exclude = (
            "post",
            "user_permissions",
            "groups",
            "is_superuser",
            "date_joined",
        )


class UserViewSet(CustomModelViewSet):
    """
    用户接口
    list:查询
    create:新增
    update:修改
    retrieve:单例
    destroy:删除
    """

    queryset = Users.objects.exclude(is_superuser=1).all()
    serializer_class = UserSerializer
    create_serializer_class = UserCreateSerializer
    update_serializer_class = UserUpdateSerializer
    filter_fields = ["name", "username", "gender", "is_active", "dept", "user_type"]
    search_fields = ["username", "name", "dept__name", "role__name"]
    # 导出
    export_field_label = {
        "username": _("Username"),
        "name": _("Full name"),
        "email": _("Email"),
        "mobile": _("Mobile"),
        "gender": _("Gender"),
        "is_active": _("Account status"),
        "last_login": _("Last login time"),
        "dept_name": _("Department name"),
        "dept_owner": _("Department head"),
    }
    export_serializer_class = ExportUserProfileSerializer
    # 导入
    import_serializer_class = UserProfileImportSerializer
    import_field_dict = {
        "username": _("Login username"),
        "name": _("Full name"),
        "email": _("Email"),
        "mobile": _("Mobile"),
        "gender": {
            "title": _("Gender"),
            "choices": {
                "data": {"未知": 2, "男": 1, "女": 0},
            }
        },
        "is_active": {
            "title": _("Account status"),
            "choices": {
                "data": {"启用": True, "禁用": False},
            }
        },
        "dept": {"title": _("Department"), "choices": {"queryset": Dept.objects.filter(status=True), "values_name": "name"}},
        "role": {"title": _("Role"), "choices": {"queryset": Role.objects.filter(status=True), "values_name": "name"}},
    }

    @action(methods=["GET"], detail=False, permission_classes=[IsAuthenticated])
    def user_info(self, request):
        """获取当前用户信息"""
        user = request.user
        result = {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "mobile": user.mobile,
            "user_type": user.user_type,
            "gender": user.gender,
            "email": user.email,
            "avatar": user.avatar,
            "dept": user.dept_id,
            "is_superuser": user.is_superuser,
            "role": user.role.values_list('id', flat=True),
            "pwd_change_count":user.pwd_change_count,
            "language": getattr(user, 'language', 'zh-cn') or 'zh-cn',
        }
        rt = getattr(user, 'tenant', None)
        result['tenant_id'] = rt.id if rt else None
        result['tenant_name'] = rt.name if rt else None
        dept = getattr(user, 'dept', None)
        if dept:
            result['dept_info'] = {
                'dept_id': dept.id,
                'dept_name': dept.name
            }
        else:
            result['dept_info'] = {
                'dept_id': None,
                'dept_name': _("No department")
            }
        role = getattr(user, 'role', None)
        if role:
            result['role_info'] = role.values('id', 'name', 'key')
        return DetailResponse(data=result, msg=_("Query successful"))

    @action(methods=["PUT"], detail=False, permission_classes=[IsAuthenticated])
    def update_user_info(self, request):
        """修改当前用户信息"""
        serializer = UserInfoUpdateSerializer(request.user, data=request.data, request=request)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return DetailResponse(data=None, msg=_("Update successful"))

    @action(methods=["PUT"], detail=False, permission_classes=[IsAuthenticated])
    def change_password(self, request, *args, **kwargs):
        """密码修改"""
        data = request.data
        old_pwd = data.get("oldPassword")
        new_pwd = data.get("newPassword")
        new_pwd2 = data.get("newPassword2")
        if old_pwd is None or new_pwd is None or new_pwd2 is None:
            return ErrorResponse(msg=_("Parameters cannot be empty"))
        if new_pwd != new_pwd2:
            return ErrorResponse(msg=_("Passwords do not match"))
        verify_password = check_password(old_pwd, request.user.password)
        if not verify_password:
            old_pwd_md5 = hashlib.md5(old_pwd.encode(encoding='UTF-8')).hexdigest()
            verify_password = check_password(str(old_pwd_md5), request.user.password)
            # 创建用户时、自定义密码无法修改问题
            if not verify_password:
                old_pwd_md5 = hashlib.md5(old_pwd_md5.encode(encoding='UTF-8')).hexdigest()
                verify_password = check_password(str(old_pwd_md5), request.user.password)
        if verify_password:
            # request.user.password = make_password(hashlib.md5(new_pwd.encode(encoding='UTF-8')).hexdigest())
            request.user.password = make_password(hashlib.md5(new_pwd.encode(encoding='UTF-8')).hexdigest())
            request.user.pwd_change_count += 1
            request.user.save()
            return DetailResponse(data=None, msg=_("Update successful"))
        else:
            return ErrorResponse(msg=_("Old password is incorrect"))

    @action(methods=["post"], detail=False, permission_classes=[IsAuthenticated])
    def login_change_password(self, request, *args, **kwargs):
        """初次登录进行密码修改"""
        data = request.data
        new_pwd = data.get("password")
        new_pwd2 = data.get("password_regain")
        if new_pwd != new_pwd2:
            return ErrorResponse(msg=_("Passwords do not match"))
        else:
            request.user.password = make_password(new_pwd)
            request.user.pwd_change_count += 1
            request.user.save()
            return DetailResponse(data=None, msg=_("Update successful"))

    @action(methods=["PUT"], detail=False, permission_classes=[IsAuthenticated])
    def update_language(self, request, *args, **kwargs):
        """更新当前用户语言偏好 (FNT-05, INT-01)"""
        lang = request.data.get("language", "zh-cn")
        valid_locales = ["zh-cn", "en", "zh-tw"]
        if lang not in valid_locales:
            return ErrorResponse(msg=_("Invalid language code"))
        user = request.user
        user.language = lang
        user.save(update_fields=["language", "modifier", "modifier_time"])
        return DetailResponse(data={"language": lang}, msg=_("Language updated successfully"))

    @action(methods=["PUT"], detail=True, permission_classes=[IsAuthenticated])
    def reset_to_default_password(self, request,pk):
        """恢复默认密码"""
        if not self.request.user.is_superuser:
            return ErrorResponse(msg=_("Only super administrators can reset passwords"))
        instance = Users.objects.filter(id=pk).first()
        if instance:
            default_password = dispatch.get_system_config_values("base.default_password")
            md5_pwd = hashlib.md5(default_password.encode(encoding='UTF-8')).hexdigest()
            instance.password = make_password(md5_pwd)
            instance.save()
            return DetailResponse(data=None, msg=_("Password reset successful"))
        else:
            return ErrorResponse(msg=_("User not found"))

    @action(methods=["PUT"], detail=True)
    def reset_password(self, request, pk):
        """
        密码重置
        """
        if not self.request.user.is_superuser:
            return ErrorResponse(msg=_("Only super administrators can reset passwords"))
        instance = Users.objects.filter(id=pk).first()
        data = request.data
        new_pwd = data.get("newPassword")
        new_pwd2 = data.get("newPassword2")
        if instance:
            if new_pwd != new_pwd2:
                return ErrorResponse(msg=_("Passwords do not match"))
            else:
                instance.password = make_password(new_pwd)
                instance.save()
                return DetailResponse(data=None, msg=_("Update successful"))
        else:
            return ErrorResponse(msg=_("User not found"))

    def list(self, request, *args, **kwargs):
        dept_id = request.query_params.get('dept')
        show_all = request.query_params.get('show_all')
        if not dept_id:
            dept_id = ''
        if not show_all:
            show_all = 0
        if int(show_all):
            all_did = [dept_id]
            def inner(did):
                sub = Dept.objects.filter(parent_id=did)
                if not sub.exists():
                    return
                for i in sub:
                    all_did.append(i.pk)
                    inner(i)
            if dept_id != '':
                inner(dept_id)
                searchs = [
                    Q(**{f+'__icontains':i})
                    for f in self.search_fields
                ] if (i:=request.query_params.get('search')) else []
                q_obj = []
                if searchs:
                    q = searchs[0]
                    for i in searchs[1:]:
                        q |= i
                    q_obj.append(Q(q))
                queryset = Users.objects.filter(*q_obj, dept_id__in=all_did)
            else:
                queryset = self.filter_queryset(self.get_queryset())
        else:
            queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, request=request)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True, request=request)
        return SuccessResponse(data=serializer.data, msg=_("Query successful"))

    @action(methods=["GET"], detail=False, permission_classes=[IsAuthenticated])
    def options(self, request):
        """用户下拉(启用): 非超管只看本租户用户; 超管全部"""
        qs = Users.objects.filter(is_active=True).exclude(is_superuser=True)
        if not getattr(request.user, "is_superuser", False):
            tenant = getattr(request.user, "tenant", None)
            if tenant is None:
                return SuccessResponse(data=[])
            qs = qs.filter(tenant=tenant)
        data = qs.values("id", "name", "username")
        return SuccessResponse(data=data)

    @action(methods=["POST"], detail=True, url_path="reset_password", permission_classes=[IsAuthenticated])
    def reset_password(self, request, pk=None):
        """重置普通用户(租户成员)的密码: 新密码+解锁+可选首登强制改密
        权限: 超管可重置任意用户; 租户经理可重置本租户成员"""
        if not pk:
            return ErrorResponse(msg=_("Missing user ID"))
        instance = self.get_queryset().filter(pk=pk).first()
        if instance is None:
            return ErrorResponse(msg=_("User does not exist"))
        if instance.id == request.user.id:
            return ErrorResponse(msg=_("Cannot reset your own password here (use personal center)"))
        # 权限校验: 超管 或 本租户的租户经理(仅限操作本租户成员)
        if not getattr(request.user, "is_superuser", False):
            tenant = getattr(request.user, "tenant", None)
            is_tm = tenant is not None and request.user.role.filter(key="tenant_manager").exists()
            if not is_tm or instance.tenant_id != tenant.id:
                return ErrorResponse(msg=_("Only superuser or this tenant manager can reset password"))
        password = str(request.data.get("password") or "")
        if len(password) < 8 or not (any(c.isalpha() for c in password) and any(c.isdigit() for c in password)):
            return ErrorResponse(msg=_("Password must be at least 8 characters and contain both letters and numbers"))
        force = request.data.get("force_change", True)
        instance.set_password(password)
        instance.login_error_count = 0
        instance.pwd_change_count = 0 if force else 1
        instance.save(update_fields=["password", "login_error_count", "pwd_change_count"])
        return DetailResponse(data={"id": instance.id, "username": instance.username}, msg=_("Password has been reset"))


# ==================== 超管账号管理（专属，仅超管） ====================


class SuperadminCreateSerializer(CustomModelSerializer):
    """新建超管账号: 仅超管可用; 账号=邮箱逻辑; 首登强制改密(pwd_change_count=0)"""
    username = serializers.CharField(
        max_length=50,
        validators=[
            CustomUniqueValidator(queryset=Users.objects.all(), message=_("Username must be unique"))
        ],
        help_text="登录账号(建议用邮箱)",
    )
    password = serializers.CharField(write_only=True, required=True)
    email = serializers.CharField(required=False, allow_blank=True)

    def validate_password(self, value):
        if not value:
            raise serializers.ValidationError(_("Password cannot be empty"))
        if len(value) < 8:
            raise serializers.ValidationError(_("Password must be at least 8 characters"))
        # 与前端认证约定一致: set_password 会再 md5 -> 存 pbkdf2(md5(明文))
        return value

    def validate(self, attrs):
        # 登录账号必须为邮箱
        username = str(attrs.get("username", "") or "")
        if "@" not in username or "." not in username.split("@")[-1]:
            raise serializers.ValidationError(_("Login account must be an email, e.g. name@example.com"))
        attrs.setdefault("email", username)
        return attrs

    def create(self, validated_data):
        username = validated_data.get("username")
        email = validated_data.get("email") or username
        # 校验邮箱唯一(若作为登录名)
        if Users.objects.filter(email=email).exists():
            raise serializers.ValidationError(_("This email is already in use"))
        user = Users(username=username)
        user.email = email
        user.name = validated_data.get("name") or username
        user.mobile = validated_data.get("mobile", "")
        user.user_type = validated_data.get("user_type", 1)
        user.is_active = True
        user.is_superuser = True
        user.is_staff = True
        user.pwd_change_count = 0  # 首登强制改密
        user.set_password(validated_data["password"])
        user.save()
        return user

    class Meta:
        model = Users
        fields = ["id", "username", "email", "name", "mobile", "password", "is_active", "create_datetime", "last_login"]
        read_only_fields = ["id", "create_datetime", "last_login"]
        extra_kwargs = {
            "password": {"write_only": True, "required": True},
            "is_active": {"read_only": True},
        }


class SuperadminListSerializer(CustomModelSerializer):
    """超管账号列表(脱敏): 不含明文/不含密码字段"""

    class Meta:
        model = Users
        fields = ["id", "username", "email", "name", "mobile", "is_active",
                  "last_login", "create_datetime", "pwd_change_count"]
        read_only_fields = fields


class SuperadminViewSet(CustomModelViewSet):
    """
    超管账号管理(仅超级管理员)
    list: 所有超管账号
    create: 新建超管账号(首登强制改密)
    """
    permission_classes = [SuperuserPermission]
    queryset = Users.objects.filter(is_superuser=True).order_by("-id")
    serializer_class = SuperadminListSerializer
    create_serializer_class = SuperadminCreateSerializer

    def get_queryset(self):
        # 仅超管可访问(双保险)
        return super().get_queryset().filter(is_superuser=True)

    @action(methods=["GET"], detail=False, url_path="lookup")
    def lookup(self, request):
        """按邮箱/用户名/手机号搜索账号(跨租户, 超管专用)"""
        q = str(request.query_params.get("q") or "").strip()
        if not q:
            return SuccessResponse(data=[])
        users = (
            Users.objects.filter(Q(username__icontains=q) | Q(email__icontains=q) | Q(mobile__icontains=q))
            .order_by("-id")[:30]
        )
        data = [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email or "",
                "name": u.name or "",
                "mobile": u.mobile or "",
                "is_active": u.is_active,
                "login_error_count": u.login_error_count,
                "login_locked_until": u.login_locked_until.strftime("%Y-%m-%d %H:%M:%S") if u.login_locked_until else None,
                "is_locked": bool(u.login_locked_until and u.login_locked_until > timezone.now()),
                "user_type": u.user_type,
                "tenant_code": u.tenant.tenant_code if u.tenant_id else None,
                "last_login": u.last_login,
                "create_datetime": u.create_datetime,
            }
            for u in users
        ]
        return SuccessResponse(data=data)

    @action(methods=["POST"], detail=False, url_path="unlock_user")
    def unlock_user(self, request):
        """解锁被锁/未激活的账号: is_active=True + 清零登录错误次数"""
        key = str(request.data.get("email") or request.data.get("username") or "").strip()
        if not key:
            return ErrorResponse(msg=_("Please enter the email or username to unlock"))
        user = (
            Users.objects.filter(Q(username__iexact=key) | Q(email__iexact=key) | Q(mobile__iexact=key))
            .first()
        )
        if user is None:
            return ErrorResponse(msg=_("Account not found"))
        user.is_active = True
        user.login_error_count = 0
        user.login_locked_until = None
        user.save(update_fields=["is_active", "login_error_count", "login_locked_until"])
        logger.info("[SUPERADMIN] %s 解锁账号 %s", request.user.username, user.username)
        return DetailResponse(data={"id": user.id, "username": user.username}, msg=_("Account unlocked"))

    @action(methods=["GET"], detail=False, url_path="login_settings")
    def login_settings(self, request):
        """读取登录安全设置(读写 system_config: login.*, 未配置时用内置默认值)"""
        from dvadmin.system.views.login import APPCONF_LOGIN_SETTINGS, login_settings as _login_settings
        values = _login_settings()
        meta = {ck: {"title": title, "default": default} for ck, title, default in APPCONF_LOGIN_SETTINGS}
        return DetailResponse(data={"values": values, "meta": meta})

    @action(methods=["POST"], detail=False, url_path="login_settings/save")
    def login_settings_save(self, request):
        """保存登录安全设置(正整数校验, 逐一写入 system_config 并刷新生效)"""
        from dvadmin.system.models import SystemConfig
        from dvadmin.system.views.login import APPCONF_LOGIN_SETTINGS, ensure_login_config_row, login_settings as _login_settings

        payload = request.data or {}
        result = {}
        for ck, title, default in APPCONF_LOGIN_SETTINGS:
            if ck not in payload:
                continue
            try:
                value = int(payload[ck])
                if value < 1:
                    raise ValueError
            except (TypeError, ValueError):
                return ErrorResponse(msg=_("{} must be a positive integer").format(title))
            ensure_login_config_row(ck, title, default)
            parent_key, _seg, child_key = ck.rpartition(".")
            parent = SystemConfig.objects.get(key=parent_key, parent_id=None)
            obj = SystemConfig.objects.get(key=child_key, parent=parent)
            obj.value = value
            obj.save()  # save() 内会自动 dispatch.refresh_system_config()
            result[ck] = value
        logger.info("[SUPERADMIN] %s 修改登录安全设置 %s", request.user.username, result)
        return DetailResponse(data={"values": _login_settings()}, msg=_("Login security settings saved"))

    @action(methods=["GET"], detail=False, url_path="signup_settings")
    def signup_settings(self, request):
        """读取自助注册模式: require_payment(是否必须付费后建租户)"""
        from dvadmin.tenant.signup import signup_requires_payment
        return DetailResponse(data={"require_payment": signup_requires_payment()})

    @action(methods=["POST"], detail=False, url_path="signup_settings/save")
    def signup_settings_save(self, request):
        """保存自助注册模式(system_config: signup.require_payment)"""
        from dvadmin.system.models import SystemConfig

        require_payment = bool(request.data.get("require_payment", True))
        SystemConfig.objects.update_or_create(
            key="signup.require_payment",
            defaults={"title": "自助注册需付费开通", "value": require_payment,
                      "form_item_type": 0, "status": True},
        )
        # 再次 save 触发 dispatch 刷新
        row = SystemConfig.objects.filter(key="signup.require_payment").first()
        row.save(update_fields=["value"])
        logger.info("[SUPERADMIN] %s 设置自助注册付费开关 = %s", request.user.username, require_payment)
        return DetailResponse(data={"require_payment": require_payment}, msg=_("Self-service signup mode saved"))

    @action(methods=["GET"], detail=False, url_path="default_password_settings")
    def default_password_settings(self, request):
        """读取新建账号默认密码(system_config: base.default_password)"""
        default_password = dispatch.get_system_config_values("base.default_password") or ""
        return DetailResponse(data={"default_password": default_password})

    @action(methods=["POST"], detail=False, url_path="default_password_settings/save")
    def default_password_settings_save(self, request):
        """保存新建账号默认密码(system_config: base.default_password)"""
        from dvadmin.system.models import SystemConfig

        password = str(request.data.get("default_password") or "").strip()
        if len(password) < 8 or not (any(c.isalpha() for c in password) and any(c.isdigit() for c in password)):
            return ErrorResponse(msg=_("Password must be at least 8 characters and contain both letters and numbers"))
        parent = SystemConfig.objects.filter(key="base", parent_id=None).first()
        if parent is None:
            return ErrorResponse(msg=_("base config item not found"))
        row = SystemConfig.objects.filter(key="default_password", parent=parent).first()
        if row is None:
            row = SystemConfig(key="default_password", parent=parent, title="创建用户默认密码",
                               form_item_type=0, status=True)
        row.value = password
        row.save()  # save() 内会自动 dispatch.refresh_system_config()
        logger.info("[SUPERADMIN] %s 修改默认密码为 %s", request.user.username, password)
        return DetailResponse(data={"default_password": password}, msg=_("Default password saved"))

    @action(methods=["POST"], detail=True, url_path="toggle_active")
    def toggle_active(self, request, pk=None):
        """启用/停用超管账号"""
        instance = self.get_object()
        # 不允许停用自己(避免把自己锁在门外)
        if instance.id == request.user.id:
            return ErrorResponse(msg=_("Cannot disable the currently logged-in superuser account"))
        is_active = bool(request.data.get("is_active", True))
        instance.is_active = is_active
        instance.login_error_count = 0  # 停用后启用时清零错误次数
        instance.login_locked_until = None  # 启用时一并清除临时锁定
        instance.save(update_fields=["is_active", "login_error_count", "login_locked_until"])
        msg = _("Enabled") if is_active else _("Disabled")
        return DetailResponse(data={"id": instance.id, "is_active": instance.is_active}, msg=msg)

    @action(methods=["POST"], detail=True, url_path="reset_password")
    def reset_password(self, request, pk=None):
        """超管之间重置密码: 新密码+解锁+可选首登强制改密(不能重置自己)"""
        instance = self.get_object()
        if instance.id == request.user.id:
            return ErrorResponse(msg=_("Cannot reset your own password here (use personal center)"))
        password = str(request.data.get("password") or "")
        if len(password) < 8 or not (any(c.isalpha() for c in password) and any(c.isdigit() for c in password)):
            return ErrorResponse(msg=_("Password must be at least 8 characters and contain both letters and numbers"))
        force = request.data.get("force_change", True)
        instance.set_password(password)
        instance.login_error_count = 0
        instance.pwd_change_count = 0 if force else 1
        instance.save(update_fields=["password", "login_error_count", "pwd_change_count"])
        return DetailResponse(data={"id": instance.id, "username": instance.username}, msg=_("Password has been reset"))
