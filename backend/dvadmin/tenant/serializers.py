# -*- coding: utf-8 -*-
from django.utils import timezone
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from dvadmin.tenant.models import Tenant
from dvadmin.utils.serializers import CustomModelSerializer


def _tenant_expired(obj):
    """是否已到期/停用(与 notify.services._trial_active 一致)"""
    if not getattr(obj, "is_active", True):
        return True
    expire_time = getattr(obj, "expire_time", None)
    if expire_time and expire_time < timezone.now():
        return True
    return False


class TenantSerializer(CustomModelSerializer):
    """租户序列化器
    plan_type 可写(试用户/正式客户: trial/paid); plan_type_label 只读展示用
    line_bot_ids 只写: 在"租户管理"里把 LINE Bot 分配给该租户(清空未选中的本租户bot)
    is_expired 只读: 已到期/停用(expire_time < now 或 is_active=False)
    """
    plan_type_label = serializers.CharField(source="get_plan_type_display", read_only=True)
    is_expired = serializers.SerializerMethodField(read_only=True)
    line_bot_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, write_only=True)
    line_bots = serializers.SerializerMethodField(read_only=True)
    referrer_tenant_info = serializers.SerializerMethodField(read_only=True)
    manager_accounts = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Tenant
        fields = "__all__"
        read_only_fields = ["id"]

    def get_is_expired(self, obj):
        return _tenant_expired(obj)

    def get_line_bots(self, obj):
        # 卡片展示: 该租户已分配的启用 Line Bot
        return [{"id": b.id, "name": b.name, "bot_code": b.bot_code}
                for b in obj.linebot_set.filter(is_active=True)]

    def get_manager_accounts(self, obj):
        # 该租户的经理登录账号(role.key='tenant_manager'), 卡片上直接展示, 免去进组织架构查看
        from dvadmin.system.models import Users
        managers = (
            Users.objects.filter(tenant=obj, role__key="tenant_manager", is_active=True)
            .values_list("username", flat=True)
            .distinct()
        )
        return list(managers)

    def get_referrer_tenant_info(self, obj):
        # 卡片展示: 该租户是通过哪个租户的推荐码注册的
        referrer = getattr(obj, "referrer_tenant", None)
        if referrer is None:
            return None
        return {"id": referrer.id, "name": referrer.name, "referral_code": referrer.referral_code}

    def validate_google_calendar_id(self, value):
        # Google ID 唯一性校验: 非空且已被其它租户使用则报错; 编辑时排除自身
        value = (value or "").strip()
        if value:
            qs = Tenant.objects.filter(google_calendar_id=value)
            instance = getattr(self, "instance", None)
            if instance is not None:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise serializers.ValidationError(_("Google ID 已占用"))
        return value

    def _sync_line_bots(self, tenant, bot_ids):
        if bot_ids is None:
            return
        from dvadmin.notify.models import LineBot
        # 先清空本租户已分配的, 再按选中重新分配
        LineBot.objects.filter(tenant=tenant).update(tenant=None)
        if bot_ids:
            LineBot.objects.filter(id__in=bot_ids).update(tenant=tenant)

    def create(self, validated_data):
        bot_ids = validated_data.pop("line_bot_ids", None)
        if not validated_data.get("referral_code"):
            validated_data["referral_code"] = Tenant.make_referral_code()
        instance = super().create(validated_data)
        self._sync_line_bots(instance, bot_ids)
        return instance

    def update(self, instance, validated_data):
        bot_ids = validated_data.pop("line_bot_ids", None)
        instance = super().update(instance, validated_data)
        self._sync_line_bots(instance, bot_ids)
        return instance


class TenantModelSerializerMixin:
    """
    业务模型序列化器基类: 强制租户隔离
    - tenant 字段只读, 禁止前端传入
    - create 时由后端从请求用户上下文注入 tenant
    """
    tenant = serializers.PrimaryKeyRelatedField(read_only=True)
    tenant_info = TenantSerializer(source="tenant", read_only=True)

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request.user, 'tenant'):
            tenant = getattr(request.user, 'tenant', None)
            if tenant is not None:
                validated_data['tenant'] = tenant
        return super().create(validated_data)
