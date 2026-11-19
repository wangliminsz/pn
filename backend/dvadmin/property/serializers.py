# -*- coding: utf-8 -*-
from django.conf import settings
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from dvadmin.notify.models import LineBot
from dvadmin.property.models import Property, PropertyAttachment, PropertyChangeLog, ReminderRule
from dvadmin.tenant.serializers import TenantModelSerializerMixin
from dvadmin.utils.serializers import CustomModelSerializer


class PropertySerializer(TenantModelSerializerMixin, CustomModelSerializer):
    """房源序列化器(强制租户隔离)"""
    pay_period_value = serializers.CharField(source="pay_period", read_only=True)
    pay_period_display = serializers.CharField(source="get_pay_period_display", read_only=True)
    owner_name = serializers.CharField(source="owner.name", read_only=True, default=None)
    creator_name = serializers.CharField(source="creator.name", read_only=True, default=None)
    tenant_name = serializers.CharField(source="tenant.name", read_only=True, default=None)
    line_bot_name = serializers.CharField(source="line_bot.name", read_only=True, default=None)
    google_calendar_id = serializers.CharField(source="tenant.google_calendar_id", read_only=True, default=None)
    attachments_count = serializers.IntegerField(read_only=True, default=0)
    reminder_rules_count = serializers.IntegerField(read_only=True, default=0)
    # 起租/结束必填(租期判定/季度付租基准依赖, 不填会误发提醒)
    rent_start = serializers.DateField(required=True, allow_null=False)
    rent_end = serializers.DateField(required=True, allow_null=False)

    class Meta:
        model = Property
        fields = "__all__"
        read_only_fields = ["id", "event_id_01", "event_id_02", "creator_name"]
    def create(self, validated_data):
        # owner 缺省 = 创建人(该房源负责人); 注意必须传 Users 实例, 不能传 id
        request = self.context.get('request')
        if 'owner' not in validated_data and request and getattr(request, 'user', None):
            validated_data['owner'] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # 负责人变更时记录日志(同一租户, 通过房源归属隔离)
        if 'owner' in validated_data:
            old_owner = instance.owner
            new_owner = validated_data.get('owner')
            if (old_owner or None) != (new_owner or None):
                from dvadmin.property.models import PropertyChangeLog
                request = self.context.get('request')
                PropertyChangeLog.objects.create(
                    tenant=instance.tenant,
                    property=instance,
                    user=getattr(request, 'user', None) if request else None,
                    field='owner',
                    from_value=old_owner.name if old_owner else '',
                    to_value=new_owner.name if new_owner else '',
                )
        return super().update(instance, validated_data)

    def validate_line_bot(self, value):
        """串台硬校验: 绑定的 bot 必须归属本房源租户(或为平台默认bot), 否则拒绝"""
        if value is None:
            return value
        tenant = getattr(self.instance, 'tenant', None)
        if tenant is None:
            # create 场景: 取请求用户所属租户
            request = self.context.get('request')
            tenant = getattr(getattr(request, 'user', None), 'tenant', None)
        # 平台默认 bot(tenant=null)可通用; 归属租户的 bot 必须与房源租户一致
        if value.tenant_id is not None and tenant is not None and value.tenant_id != tenant.id:
            raise serializers.ValidationError(_("该Bot归属其他租户, 禁止串台使用"))
        return value


def attachment_storage_rel_url(tenant_id, property_id, filename):
    """附件落盘的相对路径(相对 MEDIA_ROOT)"""
    import os
    return os.path.join(str(tenant_id), "property_files", str(property_id), os.path.basename(filename)).replace(os.sep, "/")


class PropertyAttachmentSerializer(TenantModelSerializerMixin, CustomModelSerializer):
    """房源附件(列表/上传/删除; 下载用 url)"""
    url = serializers.SerializerMethodField(read_only=True)
    size_label = serializers.SerializerMethodField(read_only=True)
    creator_name = serializers.CharField(source="creator.name", read_only=True, default=None)
    property_name = serializers.CharField(source="property.name", read_only=True, default=None)

    class Meta:
        model = PropertyAttachment
        fields = ["id", "property", "property_name", "name", "path", "size", "size_label",
                  "mime", "url", "creator_name", "create_datetime"]
        read_only_fields = ["id", "path", "size", "mime", "create_datetime"]

    def get_url(self, obj):
        from dvadmin.utils.cos_storage import file_url
        return file_url(obj.path)

    def get_size_label(self, obj):
        size = obj.size
        if size >= 1024 * 1024:
            return f"{size / 1024 / 1024:.1f} MB"
        if size >= 1024:
            return f"{size / 1024:.0f} KB"
        return f"{size} B"


class PropertyChangeLogSerializer(CustomModelSerializer):
    """房源变更记录(负责人变更)"""
    user_name = serializers.CharField(source="user.name", read_only=True, default=None)
    property_name = serializers.CharField(source="property.name", read_only=True, default=None)
    owner_name = serializers.CharField(source="property.owner.name", read_only=True, default=None)
    tenant_name = serializers.CharField(source="property.tenant.name", read_only=True, default=None)

    class Meta:
        model = PropertyChangeLog
        fields = ["id", "property", "property_name", "owner_name", "tenant_name",
                  "user", "user_name", "field",
                  "from_value", "to_value", "create_datetime"]
        read_only_fields = ["id", "create_datetime"]


class ReminderRuleSerializer(CustomModelSerializer):
    """自定义提醒规则序列化器(租户隔离: 归属房源同租户)"""
    property_name = serializers.CharField(source="property.name", read_only=True, default=None)
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    period_display = serializers.CharField(source="get_period_display", read_only=True)
    # 供前端预览: 最近一次提醒日期 + 渲染好的示例消息(无需真实发送)
    next_date = serializers.SerializerMethodField(read_only=True)
    preview = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ReminderRule
        fields = ["id", "property", "property_name", "type", "type_display", "period", "period_display",
                  "day", "template", "extra_vars", "enabled",
                  "next_date", "preview",
                  "creator_name", "create_datetime", "update_datetime"]
        read_only_fields = ["id", "tenant"]

    def get_next_date(self, obj):
        from dvadmin.notify.tasks import _rule_next_date
        d = _rule_next_date(obj.property, obj)
        return d.isoformat() if d else None

    def get_preview(self, obj):
        from dvadmin.notify.tasks import build_rule_message
        try:
            return build_rule_message(obj.property, obj)
        except Exception:
            return ""

    def create(self, validated_data):
        # tenant 从归属房源注入, 不用请求用户上下文(超管无租户, 也需落房源租户)
        prop = validated_data.get("property")
        if prop is not None:
            validated_data["tenant"] = prop.tenant
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "tenant" in validated_data:
            validated_data.pop("tenant", None)
        return super().update(instance, validated_data)
