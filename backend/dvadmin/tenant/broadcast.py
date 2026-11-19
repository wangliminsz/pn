# -*- coding: utf-8 -*-
"""
群发信息(租户经理专属)
- 预览: 统计本租户所有带 group_id 的房源群, 按 bot 拆分估算
- 发送: 创建 BroadcastTask + 触发 Celery 后台任务(broadcast_task)
- 状态: 轮询任务进度(sent/failed/skipped)
- 清理: 撤销排队中的后台任务并删除记录(测试/误发后清理用)
"""
import logging

from django.utils.translation import gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from dvadmin.notify.models import BroadcastTask, get_bot_for_property
from dvadmin.notify.tasks import broadcast_task
from dvadmin.property.models import Property
from dvadmin.utils.json_response import SuccessResponse

logger = logging.getLogger(__name__)


def _manager_only(user):
    """群发权限: 超管 或 本租户的租户经理"""
    if getattr(user, "is_superuser", False):
        return True
    tenant = getattr(user, "tenant", None)
    if tenant is None:
        return False
    return user.role.filter(key="tenant_manager").exists()


def _tenant_blocked(tenant):
    """租户不可用(停用/已到期) → 群发不允许排队, 直接提示续费"""
    if tenant is None:
        return False
    from dvadmin.tenant.serializers import _tenant_expired
    return _tenant_expired(tenant)


def _target_groups(tenant, property_ids=None):
    """本租户带 group_id 的房源(群); property_ids 指定则只发选中的(仍需在租户内)
    property_ids is None = 全部; [] = 显式选中0个(返回空)"""
    qs = (Property.objects.filter(tenant=tenant, group_id__isnull=False)
          .exclude(group_id="")
          .select_related("line_bot", "tenant"))
    if property_ids is not None:
        qs = qs.filter(id__in=property_ids)
    return qs


def _safe_property_ids(data, max_count=200):
    """从请求数据解析 property_ids(整数列表, 去重, 限长)
    返回 None=未指定(全部群); [] = 显式选中0个(不发)"""
    raw = data.get("property_ids")
    if raw is None:
        return None
    if isinstance(raw, str):
        if raw.strip() in ("", "all"):
            return None
        raw = raw.split(",")
    elif raw == "all":
        return None
    if isinstance(raw, (list, tuple)):
        if len(raw) == 0:
            return []
    ids = []
    for x in (raw or []):
        try:
            ids.append(int(x))
        except (TypeError, ValueError):
            continue
    return list(dict.fromkeys(ids))[:max_count]


class BroadcastPreviewView(APIView):
    """群发预览: 目标群数 / 估算人数 / 按 bot 拆分(只读, 不发送)"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return self._preview(request)

    def post(self, request):
        return self._preview(request)

    def _preview(self, request):
        user = request.user
        if not _manager_only(user):
            return SuccessResponse(data={"ok": False, "error": _("Only tenant managers can broadcast")})
        tenant = getattr(user, "tenant", None)
        if tenant is None:
            return SuccessResponse(data={"ok": False, "error": _("No tenant")})
        if _tenant_blocked(tenant):
            return SuccessResponse(data={"ok": False, "error": _("Tenant is expired or inactive, please renew your plan")})

        # GET: ?property_ids=1,2,3 ; POST: JSON body {"property_ids": [...]}
        property_ids = _safe_property_ids(request.GET)
        if property_ids is None:
            property_ids = _safe_property_ids(request.data)
        props = _target_groups(tenant, property_ids)
        bot_agg = {}
        for p in props:
            bot = get_bot_for_property(p)
            key = bot.id if bot else None
            agg = bot_agg.setdefault(key, {"bot_id": key, "bot_name": bot.name if bot else "未分配Bot",
                                           "groups": 0, "est_used": 0})
            agg["groups"] += 1
            agg["est_used"] += p.group_size or 1

        return SuccessResponse(data={
            "ok": True,
            "group_count": len(props),
            "est_recipients": sum((p.group_size or 1) for p in props),
            "selected_count": len(props) if property_ids is not None else None,
            "bots": list(bot_agg.values()),
        })


class BroadcastSendView(APIView):
    """发起群发: 创建任务并触发 Celery 后台发送"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not _manager_only(user):
            return SuccessResponse(data={"ok": False, "error": _("Only tenant managers can broadcast")})
        tenant = getattr(user, "tenant", None)
        if tenant is None:
            return SuccessResponse(data={"ok": False, "error": _("No tenant")})
        if _tenant_blocked(tenant):
            return SuccessResponse(data={"ok": False, "error": _("Tenant is expired or inactive, please renew your plan")})

        message = (request.data.get("message") or "").strip()
        if not message:
            return SuccessResponse(data={"ok": False, "error": _("Message content is empty")})
        if len(message) > 800:
            return SuccessResponse(data={"ok": False, "error": _("Message content cannot exceed 800 characters")})

        property_ids = _safe_property_ids(request.data)
        props = list(_target_groups(tenant, property_ids))
        if not props:
            return SuccessResponse(data={"ok": False, "error": _("No sendable property groups (none have a group ID set)")})

        task = BroadcastTask.objects.create(
            tenant=tenant, message=message,
            total=len(props),
            est_recipients=sum((p.group_size or 1) for p in props),
            property_ids=property_ids,
            status="pending",
        )
        try:
            result = broadcast_task.delay(task.id)
            task.celery_task_id = str(result.id)
            task.save(update_fields=["celery_task_id"])
        except Exception as e:
            logger.warning("群发任务 trigger 失败 task=%s: %s", task.id, e)
            task.status = "failed"
            task.error_msg = f"触发失败: {e}"
            task.save(update_fields=["status", "error_msg"])
            return SuccessResponse(data={"ok": False, "error": _("Failed to trigger the background task, please retry later")})
        return SuccessResponse(data={"ok": True, "task_id": task.id})


class BroadcastStatusView(APIView):
    """群发进度查询"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not _manager_only(user):
            return SuccessResponse(data={"ok": False, "error": _("Only tenant managers can view")})
        task_id = request.query_params.get("task_id")
        if not task_id:
            return SuccessResponse(data={"ok": False, "error": _("Missing task_id")})

        task = BroadcastTask.objects.filter(pk=task_id).first()
        if task is None:
            return SuccessResponse(data={"ok": False, "error": _("Task does not exist")})
        tenant = getattr(user, "tenant", None)
        if not getattr(user, "is_superuser", False) and (tenant is None or task.tenant_id != tenant.id):
            return SuccessResponse(data={"ok": False, "error": _("No permission to view this task")})

        return SuccessResponse(data={
            "ok": True,
            "task": {
                "id": task.id,
                "status": task.status,
                "total": task.total,
                "est_recipients": task.est_recipients,
                "sent": task.sent,
                "failed": task.failed,
                "skipped": task.skipped,
                "message": task.message,
                "error_msg": task.error_msg,
                "create_datetime": task.create_datetime.strftime("%Y-%m-%d %H:%M:%S") if task.create_datetime else None,
            },
        })


class BroadcastCleanView(APIView):
    """清理群发记录: 撤销排队中的后台任务, 并删除本租户全部 BroadcastTask 记录"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not _manager_only(user):
            return SuccessResponse(data={"ok": False, "error": _("Only tenant managers can clean up")})
        tenant = getattr(user, "tenant", None)

        qs = BroadcastTask.objects.all()
        if not getattr(user, "is_superuser", False):
            if tenant is None:
                return SuccessResponse(data={"ok": False, "error": _("No tenant")})
            qs = qs.filter(tenant=tenant)

        # 撤销排队/执行中的 Celery 任务(已完成的撤销无效, 忽略)
        revoked = 0
        for t in qs.filter(status__in=["pending", "running"]):
            if t.celery_task_id:
                try:
                    from application.celery import app as celery_app
                    celery_app.control.revoke(t.celery_task_id, terminate=False)
                    revoked += 1
                except Exception as e:
                    logger.warning("撤销任务失败 task=%s: %s", t.id, e)

        deleted = qs.delete()[0]
        return SuccessResponse(data={
            "ok": True,
            "revoked": revoked,
            "deleted": deleted,
        })