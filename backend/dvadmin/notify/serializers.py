# -*- coding: utf-8 -*-
from rest_framework import serializers

from dvadmin.notify.models import DeeplKey, LineBot, MessageLog
from dvadmin.utils.serializers import CustomModelSerializer


class DeeplKeySerializer(CustomModelSerializer):
    """DeepL Key 序列化器(仅超管管理)
    api_key 只写不读 (列表不返明文), 列表返回脱敏掩码 api_key_mask
    """
    api_key_mask = serializers.SerializerMethodField(read_only=True)
    key_status = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DeeplKey
        fields = ["id", "name", "api_key", "api_key_mask", "is_default", "is_active",
                  "remark", "key_status", "creator_name", "create_datetime", "update_datetime"]
        read_only_fields = ["id"]

    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def get_api_key_mask(self, obj):
        key = obj.api_key
        if not key:
            return ""
        if len(key) <= 8:
            return key[:2] + "****"
        return f"{key[:4]}****{key[-4:]}"

    def get_key_status(self, obj):
        return "default" if obj.is_default else ("active" if obj.is_active else "disabled")

    def update(self, instance, validated_data):
        # write_only 留空(空串)则不覆盖已有 Key
        if "api_key" in validated_data and not validated_data["api_key"]:
            validated_data.pop("api_key")
        return super().update(instance, validated_data)


class LineBotSerializer(CustomModelSerializer):
    """LineBot 序列化器(仅超管管理)
    token/secret 只写不读 (列表不返明文), 编辑留空则不覆盖
    has_channel_secret/has_channel_access_token 只读: 告知前端是否已设置(用于编辑界面提示"已设置/留空不修改")
    """
    tenant_info = serializers.CharField(source="tenant.name", read_only=True, default=None)
    has_channel_secret = serializers.SerializerMethodField(read_only=True)
    has_channel_access_token = serializers.SerializerMethodField(read_only=True)
    channel_secret_tail = serializers.SerializerMethodField(read_only=True)
    channel_access_token_tail = serializers.SerializerMethodField(read_only=True)
    quota = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = LineBot
        fields = "__all__"
        read_only_fields = ["id"]

    channel_access_token = serializers.CharField(
        write_only=True, required=False, allow_blank=True)
    channel_secret = serializers.CharField(
        write_only=True, required=False, allow_blank=True)

    def get_quota(self, obj):
        """卡片配额: 只读 LINE 缓存; 无缓存返回 None(前端显示 '—', 不做本地估算)
        只展示 LINE 真实数据(source="line"); 未拉取过/超时一律 None"""
        from dvadmin.notify.services import get_cached_line_quota
        limit, used = get_cached_line_quota(obj)
        if limit is None or used is None:
            return None
        return {"used": used, "limit": limit, "local_used": used, "source": "line"}

    def get_has_channel_secret(self, obj):
        return bool(obj.channel_secret)

    def get_has_channel_access_token(self, obj):
        return bool(obj.channel_access_token)

    def get_channel_secret_tail(self, obj):
        # 末4位, 供前端展示"已设置(末4位xxxx)"而不暴露明文
        return str(obj.channel_secret)[-4:] if obj.channel_secret else ""

    def get_channel_access_token_tail(self, obj):
        return str(obj.channel_access_token)[-4:] if obj.channel_access_token else ""

    def update(self, instance, validated_data):
        # write_only 留空(空串)则不覆盖已有凭据
        for f in ('channel_access_token', 'channel_secret'):
            if f in validated_data and not validated_data[f]:
                validated_data.pop(f)
        return super().update(instance, validated_data)


class MessageLogSerializer(CustomModelSerializer):
    """消息记录序列化器(只读)"""
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    bot_name = serializers.CharField(source="line_bot.name", read_only=True, default=None)
    property_name = serializers.CharField(source="property.name", read_only=True, default=None)

    class Meta:
        model = MessageLog
        fields = ["id", "tenant", "tenant_name", "line_bot", "bot_name", "property", "property_name",
                  "group_id", "group_size", "msg_type", "content", "result", "error_msg", "count",
                  "create_datetime"]
