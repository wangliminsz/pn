# -*- coding: utf-8 -*-
"""
群文档(media/{tenant_id}/group_files/{group_id}) 列表接口
按租户+群 权限列出/预览群文档文件
"""
import os
from urllib.parse import quote

from django.conf import settings
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from dvadmin.notify.models import LineBot
from dvadmin.notify.services import get_cached_group_name, get_group_name
from dvadmin.tenant.models import Tenant
from dvadmin.utils.cos_storage import COS_ENABLED, cos_list_objects, file_url
from dvadmin.utils.json_response import SuccessResponse
from dvadmin.utils.viewset import CustomModelViewSet


def _group_files_root(tenant_id):
    return os.path.join(settings.MEDIA_ROOT, str(tenant_id), 'group_files')


def _pick_bot_for_group(tenant_id, group_id):
    """为该租户的群选一个可用的 Line Bot(优先缓存/关联, 无则第一个启用 bot)
    返回 LineBot|None
    """
    bots = list(LineBot.objects.filter(tenant_id=tenant_id, is_active=True).order_by('id'))
    if not bots:
        # 平台默认/演示 bot 兜底
        bots = list(LineBot.objects.filter(tenant_id__isnull=True, is_active=True).order_by('id'))
    return bots[0] if bots else None


class GroupDocSerializer(serializers.Serializer):
    tenant_id = serializers.IntegerField(read_only=True)
    group_id = serializers.CharField(read_only=True)
    group_name = serializers.CharField(read_only=True, required=False, allow_null=True)
    name = serializers.CharField(read_only=True)
    path = serializers.CharField(read_only=True)
    size = serializers.IntegerField(read_only=True)
    mtime = serializers.IntegerField(read_only=True)
    url = serializers.CharField(read_only=True)
    bot_name = serializers.CharField(read_only=True, required=False, allow_null=True)
    store_time = serializers.CharField(read_only=True, required=False, allow_null=True)
    message_time = serializers.CharField(read_only=True, required=False, allow_null=True)


class GroupDocViewSet(CustomModelViewSet):
    """群文档列表(只读, 按租户+群) - 仅租户经理(tenant_manager)可访问"""
    permission_classes = [IsAuthenticated]
    serializer_class = GroupDocSerializer

    def _manager_only(self, user, tenant_id):
        """仅允许: 超管 或 本租户的租户经理(tenant_manager)"""
        if getattr(user, "is_superuser", False):
            return True
        tenant = getattr(user, "tenant", None)
        if tenant is None or tenant.id != tenant_id:
            return False
        return user.role.filter(key="tenant_manager").exists()

    def _scan_cos(self, tenant_id, group_id_filter):
        file_list = []
        for obj in cos_list_objects(f"{tenant_id}/group_files/"):
            rel = obj["rel"]
            parts = rel.split("/")
            # 结构: {tenant}/group_files/{group_id}/{filename}
            if len(parts) < 4 or not parts[-1]:
                continue
            gid = parts[2]
            if group_id_filter and group_id_filter != gid:
                continue
            file_list.append({
                'tenant_id': tenant_id,
                'group_id': gid,
                'name': parts[-1],
                'path': rel,
                'size': obj['size'],
                'mtime': obj['mtime'],
                'url': file_url(rel),
            })
        return file_list

    def _scan_local(self, tenant_id, group_id_filter):
        file_list = []
        root = _group_files_root(tenant_id)
        if not os.path.isdir(root):
            return file_list
        # 遍历 {tenant_id}/group_files/{group_id}/* 两层
        for gid in os.listdir(root):
            gdir = os.path.join(root, gid)
            if not os.path.isdir(gdir):
                continue
            if group_id_filter and group_id_filter != gid:
                continue
            for fname in os.listdir(gdir):
                full = os.path.join(gdir, fname)
                if not os.path.isfile(full):
                    continue
                rel = os.path.relpath(full, settings.MEDIA_ROOT).replace(os.sep, '/')
                st = os.stat(full)
                file_list.append({
                    'tenant_id': tenant_id,
                    'group_id': gid,
                    'name': fname,
                    'path': rel,
                    'size': st.st_size,
                    'mtime': int(st.st_mtime),
                    'url': f"{settings.MEDIA_URL}{quote(rel)}",
                })
        return file_list

    def list(self, request, *args, **kwargs):
        user = request.user
        if getattr(user, "is_superuser", False):
            tenant_ids = list(Tenant.objects.values_list("id", flat=True))
        else:
            tenant = getattr(user, "tenant", None)
            if tenant is None or not self._manager_only(user, tenant.id):
                return SuccessResponse(data=[])
            tenant_ids = [tenant.id]

        group_id_filter = request.query_params.get("group_id", None)

        file_list = []
        for tenant_id in tenant_ids:
            if COS_ENABLED:
                file_list.extend(self._scan_cos(tenant_id, group_id_filter))
            else:
                file_list.extend(self._scan_local(tenant_id, group_id_filter))

        file_list.sort(key=lambda x: x['mtime'], reverse=True)

        # 附上群名称(缓存命中即返回, 不打 LINE): 同 tenant+group 共享同一个
        bots_by_tenant = {}
        group_name_cache = {}
        # 附上存储记录(GroupDocRecord): bot 名 / 存储时间 / 消息时间
        from dvadmin.notify.models import GroupDocRecord
        rec_map = {}
        for rec in GroupDocRecord.objects.filter(tenant_id__in=tenant_ids).order_by('-store_time'):
            rec_map[(rec.tenant_id, rec.group_id, rec.file_name)] = rec
        for f in file_list:
            bot = bots_by_tenant.get(f['tenant_id'])
            if bot is None:
                bot = _pick_bot_for_group(f['tenant_id'], f['group_id'])
                bots_by_tenant[f['tenant_id']] = bot
            ckey = (f['tenant_id'], f['group_id'])
            gname = group_name_cache.get(ckey)
            if gname is None and bot is not None:
                gname = get_cached_group_name(bot, f['group_id'])
                group_name_cache[ckey] = gname
            f['group_name'] = gname
            rec = rec_map.get((f['tenant_id'], f['group_id'], f['name']))
            f['bot_name'] = rec.bot_name if rec else None
            f['store_time'] = rec.store_time.strftime('%Y-%m-%d %H:%M:%S') if rec and rec.store_time else None
            f['message_time'] = rec.message_time.strftime('%Y-%m-%d %H:%M:%S') if rec and rec.message_time else None
        return SuccessResponse(data=file_list)

    @action(methods=['GET'], detail=False)
    def refresh_group_name(self, request):
        """精确刷新某群名称(调 LINE API, force=True), 前端点击小刷新图标时调用
        GET /api/notify/groupdoc/refresh_group_name/?group_id=xxx
        """
        group_id = request.query_params.get("group_id") or (request.data or {}).get("group_id")
        if not group_id:
            return SuccessResponse(data={"ok": False, "group_name": None, "error": "缺少 group_id"})
        user = request.user
        if getattr(user, "is_superuser", False):
            tenant_ids = list(Tenant.objects.values_list("id", flat=True))
        else:
            tenant = getattr(user, "tenant", None)
            if tenant is None or not self._manager_only(user, tenant.id):
                return SuccessResponse(data={"ok": False, "group_name": None, "error": "permission denied"})
            tenant_ids = [tenant.id]

        name, err = None, None
        for tenant_id in tenant_ids:
            bot = _pick_bot_for_group(tenant_id, group_id)
            if bot is None:
                continue
            name, err = get_group_name(bot, group_id, force=True)
            if name:
                break
        if not name and err is None:
            err = "denied"
        return SuccessResponse(data={"ok": name is not None, "group_name": name, "error": err})

    @action(methods=['GET'], detail=False)
    def options(self, request):
        return SuccessResponse(data=[])


__all__ = ["GroupDocViewSet"]
