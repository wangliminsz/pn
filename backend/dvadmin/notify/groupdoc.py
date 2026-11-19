# -*- coding: utf-8 -*-
"""
群文档(media/{tenant_id}/group_files/{group_id}) 列表接口
按租户+群 权限列出/预览群文档文件
"""
import os

from django.conf import settings
from django.core.cache import cache
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from dvadmin.notify.models import LineBot
from dvadmin.notify.services import get_cached_group_name, get_group_name
from dvadmin.tenant.models import Tenant
from dvadmin.utils.cos_storage import COS_ENABLED, cos_list_objects, file_url
from dvadmin.utils.json_response import SuccessResponse
from dvadmin.utils.viewset import CustomModelViewSet


GROUP_DOC_CACHE_TTL = 60
GROUP_DOC_MAX_PAGE_SIZE = 200


def _group_files_root(tenant_id):
    return os.path.join(settings.MEDIA_ROOT, str(tenant_id), 'group_files')


def _group_doc_cache_key(tenant_id):
    return f"groupdoc:files:{tenant_id}"


def invalidate_group_doc_cache(tenant_id):
    """群文档有新增文件时删除租户列表缓存, 下次请求重新扫描"""
    if tenant_id is None:
        return
    try:
        cache.delete(_group_doc_cache_key(tenant_id))
    except Exception:
        pass


def _tenant_files(viewset, tenant_id):
    """读取某租户群文档元数据(不含预签名 URL), 短时缓存避免每次扫描 COS"""
    key = _group_doc_cache_key(tenant_id)
    try:
        cached = cache.get(key)
    except Exception:
        cached = None
    if cached is not None:
        return cached
    files = viewset._scan_cos(tenant_id) if COS_ENABLED else viewset._scan_local(tenant_id)
    try:
        cache.set(key, files, GROUP_DOC_CACHE_TTL)
    except Exception:
        pass
    return files


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

    def _scan_cos(self, tenant_id):
        file_list = []
        for obj in cos_list_objects(f"{tenant_id}/group_files/"):
            rel = obj["rel"]
            parts = rel.split("/")
            # 结构: {tenant}/group_files/{group_id}/{filename}
            if len(parts) < 4 or not parts[-1]:
                continue
            file_list.append({
                'tenant_id': tenant_id,
                'group_id': parts[2],
                'name': parts[-1],
                'path': rel,
                'size': obj['size'],
                'mtime': obj['mtime'],
            })
        return file_list

    def _scan_local(self, tenant_id):
        file_list = []
        root = _group_files_root(tenant_id)
        if not os.path.isdir(root):
            return file_list
        # 遍历 {tenant_id}/group_files/{group_id}/* 两层
        for gid in os.listdir(root):
            gdir = os.path.join(root, gid)
            if not os.path.isdir(gdir):
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
                })
        return file_list

    def list(self, request, *args, **kwargs):
        user = request.user
        if getattr(user, "is_superuser", False):
            tenant_ids = list(Tenant.objects.values_list("id", flat=True))
        else:
            tenant = getattr(user, "tenant", None)
            if tenant is None or not self._manager_only(user, tenant.id):
                return SuccessResponse(data=[], page=1, limit=12, total=0)
            tenant_ids = [tenant.id]

        try:
            page = max(1, int(request.query_params.get("page") or 1))
        except (TypeError, ValueError):
            page = 1
        try:
            limit = int(request.query_params.get("limit") or 12)
        except (TypeError, ValueError):
            limit = 12
        limit = max(1, min(limit, GROUP_DOC_MAX_PAGE_SIZE))
        keyword = (request.query_params.get("keyword") or "").strip().lower()
        group_id_filter = request.query_params.get("group_id", None)

        file_list = []
        for tenant_id in tenant_ids:
            file_list.extend(_tenant_files(self, tenant_id))

        if group_id_filter:
            file_list = [f for f in file_list if f['group_id'] == group_id_filter]
        if keyword:
            file_list = [
                f for f in file_list
                if keyword in (f.get('name') or '').lower() or keyword in (f.get('group_id') or '').lower()
            ]

        # mtime 倒序; 同一时间按文件名保证分页稳定
        file_list.sort(key=lambda x: (x.get('mtime') or 0, x.get('name') or ''), reverse=True)
        total = len(file_list)
        total_pages = max(1, (total + limit - 1) // limit)
        page = min(page, total_pages)
        start = (page - 1) * limit
        page_files = [dict(f) for f in file_list[start:start + limit]]

        # 仅当前页生成预签名 URL, 并附加存储记录(GroupDocRecord)
        from dvadmin.notify.models import GroupDocRecord
        rec_map = {}
        if page_files:
            recs = GroupDocRecord.objects.filter(
                tenant_id__in={f['tenant_id'] for f in page_files},
                group_id__in={f['group_id'] for f in page_files},
                file_name__in={f['name'] for f in page_files},
            ).order_by('-store_time')
            rec_map = {(r.tenant_id, r.group_id, r.file_name): r for r in recs}

        bots_by_tenant = {}
        group_name_cache = {}
        for f in page_files:
            f['url'] = file_url(f['path'])
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
        return SuccessResponse(data=page_files, page=page, limit=limit, total=total)

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
