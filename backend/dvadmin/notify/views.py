# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta

from django.conf import settings
from django.db import models
from django.http import HttpResponse
from django.utils.translation import gettext as _
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from dvadmin.notify.models import DeeplKey, LineBot, MessageLog
from dvadmin.notify.serializers import DeeplKeySerializer, LineBotSerializer, MessageLogSerializer
from dvadmin.notify.services import get_deepl_usage
from dvadmin.utils.json_response import DetailResponse, ErrorResponse, SuccessResponse
from dvadmin.utils.permission import SuperuserPermission
from dvadmin.utils.viewset import CustomModelViewSet


class NotifyScheduleView(APIView):
    """每日提醒发送时间 + 提醒消息模板(运行时配置, 超管可读改)
    - GET:  返回 {hour, minute, source('db'|'env'), tz, env_default, dedup, rent_template, maturity_template}
    - POST: 可按需保存任一:{hour, minute}/{dedup}/{rent_template, maturity_template}
    """

    permission_classes = [SuperuserPermission]

    def get(self, request):
        from django.conf import settings
        from dvadmin.notify.apps import NotifyConfig
        from dvadmin.system.models import SystemConfig
        hour = NotifyConfig._runtime_notify_hour()
        minute = NotifyConfig._runtime_notify_minute()
        row = SystemConfig.objects.filter(key="notify_send_hour").first()
        source = "db" if row is not None and row.value is not None else "env"
        tz = getattr(settings, "CELERY_TIMEZONE", "Asia/Bangkok") or "Asia/Bangkok"
        env_default = int(getattr(settings, "NOTIFY_SEND_HOUR", 9) or 9)
        dedup_row = SystemConfig.objects.filter(key="reminder_dedup").first()
        dedup = bool(dedup_row is not None and dedup_row.value is not None
                     and str(dedup_row.value).strip().lower() in ("1", "true", "on", "yes"))
        rent_row = SystemConfig.objects.filter(key="notify.rent_template").first()
        maturity_row = SystemConfig.objects.filter(key="notify.maturity_template").first()
        return SuccessResponse(data={
            "hour": hour,
            "minute": minute,
            "source": source,
            "env_default": env_default,
            "tz": tz,
            "dedup": dedup,
            "rent_template": rent_row.value if rent_row is not None and rent_row.value else "",
            "maturity_template": maturity_row.value if maturity_row is not None and maturity_row.value else "",
        })

    def post(self, request):
        from dvadmin.system.models import SystemConfig
        has_schedule = request.data.get("hour") not in (None, "")
        has_dedup = "dedup" in request.data
        has_templates = "rent_template" in request.data or "maturity_template" in request.data
        if not (has_schedule or has_dedup or has_templates):
            return SuccessResponse(data={"ok": False, "error": _("Parameters cannot be empty")})

        # 1. 提醒消息模板: 空串=删除配置, 恢复内置默认
        if "rent_template" in request.data:
            val = (request.data.get("rent_template") or "").strip()
            if val:
                SystemConfig.objects.update_or_create(key="notify.rent_template", defaults={"value": val})
            else:
                SystemConfig.objects.filter(key="notify.rent_template").delete()
        if "maturity_template" in request.data:
            val = (request.data.get("maturity_template") or "").strip()
            if val:
                SystemConfig.objects.update_or_create(key="notify.maturity_template", defaults={"value": val})
            else:
                SystemConfig.objects.filter(key="notify.maturity_template").delete()

        # 2. 发送时间(可选)
        hour = minute = None
        synced = False
        if has_schedule:
            hour = request.data.get("hour")
            minute = request.data.get("minute", 0)
            try:
                hour = int(hour)
                minute = int(minute)
            except (TypeError, ValueError):
                return SuccessResponse(data={"ok": False, "error": _("hour/minute 必须是整数")})
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                return SuccessResponse(data={"ok": False, "error": _("hour 0-23, minute 0-59")})
            SystemConfig.objects.update_or_create(
                key="notify_send_hour", defaults={"value": hour}
            )
            SystemConfig.objects.update_or_create(
                key="notify_send_minute", defaults={"value": minute}
            )
            # 改时间后, 若今天已经执行过(daily_mark), 清空"当天已执行"标记, 让新时间当天还能触发(便于测试)
            SystemConfig.objects.filter(key="notify_last_run_date").delete()
            # 同步到 django_celery_beat DB 仅作为兼容保留(内置调度器直接读 SystemConfig, 不依赖它)
            try:
                from dvadmin.notify.apps import NotifyConfig
                NotifyConfig._sync_daily_notify_beat()
                synced = True
            except Exception as e:
                logger = __import__("logging").getLogger(__name__)
                logger.exception("同步每日提醒定时任务失败: %s", e)
                return SuccessResponse(data={"ok": True, "hour": hour, "minute": minute, "synced": False,
                                             "error": _("Saved but sync failed: {}").format(e)})

        # 3. 可选: 一并设置「当日防重」开关(reminder_dedup)
        dedup = None
        if has_dedup:
            dedup = bool(request.data.get("dedup"))
            if dedup:
                SystemConfig.objects.update_or_create(key="reminder_dedup", defaults={"value": "on"})
            else:
                SystemConfig.objects.filter(key="reminder_dedup").delete()

        return SuccessResponse(
            data={"ok": True, "hour": hour, "minute": minute, "synced": synced, "dedup": dedup},
            msg=(_("Daily reminder time updated to Thailand time {:02d}:{:02d} and is now in effect").format(hour, minute)
                 if has_schedule else _("Save successful")),
        )


def _build_today_schedule(target_date=None):
    """超管「今日消息」监控: 计算指定日期(默认今天)全部租户【应发】的提醒清单(只读, 不发送)
    - 触发判定与 scan_and_notify 完全一致(付租/到期30·15天/自定义规则 + 起租范围内)
    - 状态来自当日 MessageLog: sent(有成功) / failed(有失败) / pending(未发)
    - 发不出去的标的 blocked, 附原因: no_group / no_bot / bot_inactive
    """
    from django.db.models import Q
    from dvadmin.notify.models import MessageLog
    from dvadmin.notify.services import get_cached_group_name
    from dvadmin.notify.tasks import (_is_pay_period_month, _pay_remind_day_hit,
                                      _rule_hit, _within_rent_range)
    from dvadmin.property.models import Property, ReminderRule

    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date() if target_date else None
    now = target_date or datetime.now().date()
    now_dt = datetime.combine(now, datetime.min.time())
    day_end = now_dt + timedelta(days=1)

    props = list(Property.objects.filter(tenant__isnull=False)
                 .select_related("tenant", "line_bot")
                 .order_by("tenant_id", "id"))
    rules = list(ReminderRule.objects.filter(enabled=True).select_related("property"))
    rules_by_prop = {}
    for r in rules:
        rules_by_prop.setdefault(r.property_id, []).append(r)

    # 当日 MessageLog 状态索引: (property_id, msg_type, rule_id) -> {sent, failed}
    log_idx = {}
    for lg in MessageLog.objects.filter(create_datetime__gte=now_dt, create_datetime__lt=day_end):
        if not lg.property_id:
            continue
        key = (lg.property_id, lg.msg_type, lg.rule_id or None)
        st = log_idx.setdefault(key, {"sent": False, "failed": False})
        if lg.result == "success":
            st["sent"] = True
        else:
            st["failed"] = True

    items = []
    for prop in props:
        if not _within_rent_range(prop, now_dt):
            continue
        prop_rules = rules_by_prop.get(prop.id, [])
        pay_hit = bool(prop.remind_day) and _is_pay_period_month(now_dt, prop) and _pay_remind_day_hit(now_dt, prop)
        maturity_hit = bool(prop.rent_end) and ((prop.rent_end - now_dt.date()).days in (30, 15))
        rules_hit = [r for r in prop_rules if _rule_hit(now_dt, prop, r)]
        if not (pay_hit or maturity_hit or rules_hit):
            continue

        tenant = prop.tenant
        group_id = prop.group_id
        bot = None
        if group_id:
            from dvadmin.notify.models import get_bot_for_property
            bot = get_bot_for_property(prop)
        blocked_reason = None
        if not group_id:
            blocked_reason = "no_group"
        elif bot is None:
            has_bot = LineBot.objects.filter(tenant=tenant).exists()
            blocked_reason = "bot_inactive" if has_bot else "no_bot"

        common = {
            "tenant_id": tenant.id if tenant else None,
            "tenant_name": tenant.name if tenant else "",
            "prop_id": prop.id,
            "name": prop.name or "",
            "rent_amount": str(prop.rent_amount) if prop.rent_amount is not None else None,
            "pay_period": prop.pay_period or "Monthly",
            "remind_day": prop.remind_day,
            "rent_start": prop.rent_start.isoformat() if prop.rent_start else None,
            "rent_end": prop.rent_end.isoformat() if prop.rent_end else None,
            "bot_name": bot.name if bot else None,
            "group_id": group_id,
            "group_name": get_cached_group_name(bot, group_id),
        }

        def _status(prop_id, msg_type, rule_key=None):
            st = log_idx.get((prop_id, msg_type, rule_key), None)
            if st is None:
                return "pending"
            if st["sent"]:
                return "sent"
            if st["failed"]:
                return "failed"
            return "pending"

        if pay_hit:
            items.append({**common, "kind": "rent", "rule_id": None, "rule_name": None,
                          "status": (_status(prop.id, "rent") if blocked_reason is None else "blocked"),
                          "blocked_reason": blocked_reason})
        if maturity_hit:
            items.append({**common, "kind": "maturity", "rule_id": None, "rule_name": None,
                          "status": (_status(prop.id, "maturity") if blocked_reason is None else "blocked"),
                          "blocked_reason": blocked_reason})
        for rule in rules_hit:
            rtype = rule.type if rule.type in ("utility", "custom") else "custom"
            items.append({**common, "kind": rtype, "rule_id": rule.id,
                          "rule_name": rule.get_type_display(),
                          "status": (_status(prop.id, rtype, str(rule.id)) if blocked_reason is None else "blocked"),
                          "blocked_reason": blocked_reason})

    items.sort(key=lambda x: (x["tenant_name"] or "", x["name"] or "", x["kind"]))
    stats = {"total": len(items), "pending": 0, "sent": 0, "failed": 0, "blocked": 0}
    for it in items:
        if it["status"] in stats:
            stats[it["status"]] += 1
    return {"date": now.isoformat(), "stats": stats, "items": items}


class TodayMessagesView(APIView):
    """超管「今日消息」监控页数据: 今天(或指定日期)全租户应发提醒 + 状态(只读)
    GET /api/notify/today/?date=YYYY-MM-DD  (默认今天)
    """

    permission_classes = [SuperuserPermission]

    def get(self, request):
        target = request.query_params.get("date") or None
        try:
            data = _build_today_schedule(target)
        except Exception as e:
            logger = __import__("logging").getLogger(__name__)
            logger.exception("构建今日消息清单失败: %s", e)
            return ErrorResponse(msg=_("Failed to build today's message list"))
        return SuccessResponse(data=data)


class DeeplKeyViewSet(CustomModelViewSet):
    """DeepL Key 管理接口(仅超级管理员)"""
    queryset = DeeplKey.objects.all()
    serializer_class = DeeplKeySerializer
    permission_classes = [SuperuserPermission]

    def destroy(self, request, *args, **kwargs):
        """删除默认 Key 时, 自动把默认标记转移给其它启用 Key"""
        instance = self.get_object()
        was_default = instance.is_default
        instance.delete()
        if was_default:
            fallback = DeeplKey.objects.filter(is_active=True).order_by("id").first()
            if fallback:
                fallback.is_default = True
                fallback.save(update_fields=["is_default"])
        return DetailResponse(data=[], msg=_("Delete successful"))

    @action(methods=["GET"], detail=True)
    def usage(self, request, pk):
        """查询该 Key 的 DeepL 真实额度"""
        instance = self.get_object()
        data = get_deepl_usage(instance.api_key)
        if not data:
            return DetailResponse(data=None, msg=_("Failed to query DeepL quota"))
        data["api_key"] = instance.api_key
        data["is_default"] = instance.is_default
        return DetailResponse(data=data)

    @action(methods=["GET"], detail=False)
    def usages(self, request):
        """批量查询所有启用 Key 的 DeepL 真实额度汇总"""
        data = []
        for key in self.get_queryset().filter(is_active=True):
            usage = get_deepl_usage(key.api_key) or {}
            data.append({
                "id": key.id,
                "name": key.name,
                "is_default": key.is_default,
                "usage": usage,
            })
        return SuccessResponse(data=data)


class LineBotViewSet(CustomModelViewSet):
    """LineBot 管理接口(超管管理; 租户只读: 仅看本租户/平台默认 bot, 凭据不返回明文)"""
    queryset = LineBot.objects.all()
    serializer_class = LineBotSerializer
    # 租户所见范围在 get_queryset 内处理, 不再叠加 dvadmin 默认的 dept/creator 数据权限过滤
    extra_filter_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if getattr(user, "is_superuser", False):
            return qs
        tenant = getattr(user, "tenant", None)
        if tenant is None:
            return qs.filter(tenant__isnull=True, is_default=True)
        # 本租户的 bot + 平台默认 bot; 不暴露其它租户/空闲未分配 bot
        return qs.filter(models.Q(tenant=tenant) | models.Q(tenant__isnull=True, is_default=True))

    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        # 租户只读(GET list/retrieve/usage/options), 写操作仍要求超管
        if self.action in ("list", "retrieve", "usage", "options"):
            return [IsAuthenticated()]
        return [SuperuserPermission()]

    @action(methods=["POST"], detail=False, permission_classes=[SuperuserPermission])
    def run_daily_notify(self, request):
        """超管手动触发: 立即执行每日提醒任务(不等待定时时间)
        POST /api/notify/linebot/run_daily_notify/
        body: {tenant_id?: int, target_date?: "YYYY-MM-DD"} 可选, 默认全部租户/今天
        同步执行, 返回本次实际发送条数
        """
        from dvadmin.notify.tasks import daily_notify_task

        tenant_id = request.data.get("tenant_id")
        target_date = request.data.get("target_date")
        tenant_ids = [tenant_id] if tenant_id else None
        try:
            sent = daily_notify_task(tenant_ids=tenant_ids, target_date=target_date)
        except Exception as e:
            logger = __import__("logging").getLogger(__name__)
            logger.exception("手动触发每日提醒失败: %s", e)
            return SuccessResponse(data={"ok": False, "sent": 0, "error": str(e)}, msg=_("Trigger failed"))
        return SuccessResponse(data={"ok": True, "sent": sent}, msg=_("Completed, {} reminders sent").format(sent))

    @action(methods=["GET"], detail=False, permission_classes=[IsAuthenticated])
    def options(self, request):
        """下拉选项(仅启用): 普通用户只看「本租户bot + 平台默认bot(is_default)」; 超管看全部"""
        qs = self.get_queryset().filter(is_active=True)
        user = request.user
        if not getattr(user, "is_superuser", False):
            tenant = getattr(user, "tenant", None)
            if tenant is not None:
                # 本租户的bot 或 平台默认bot(is_default), 不暴露空闲未分配bot
                qs = qs.filter(tenant=tenant) | qs.filter(tenant__isnull=True, is_default=True)
            else:
                # 无租户的普通用户: 仅平台默认bot
                qs = qs.filter(tenant__isnull=True, is_default=True)
        data = qs.values("id", "name", "bot_code", "is_default")
        return SuccessResponse(data=data)

    @action(methods=["GET"], detail=False)
    def quota_list(self, request):
        """全部启用 bot 的 LINE 真实配额(只展示 LINE 数据, 无数据返回 None, 不做本地估算)"""
        from dvadmin.notify.services import get_line_quota
        data = []
        for bot in self.get_queryset().filter(is_active=True):
            limit, used = get_line_quota(bot)
            if limit is None or used is None:
                data.append({"id": bot.id, "name": bot.name, "bot_code": bot.bot_code,
                             "used": None, "limit": None, "source": "line"})
                continue
            data.append({
                "id": bot.id,
                "name": bot.name,
                "bot_code": bot.bot_code,
                "used": used,
                "limit": limit,
                "local_used": used,
                "source": "line",
            })
        return SuccessResponse(data=data)

    @action(methods=["GET"], detail=True)
    def usage(self, request, pk):
        """当前 bot 真实 LINE 配额(仅展示 LINE 数据)
        ?force=1 时强制请求 LINE(跳过缓存), 用于刷新按钮;
        LINE 不可达/未拉取过时返回 None, 前端显示 '—' 不做本地估算"""
        bot = self.get_object()
        force = request.query_params.get("force") == "1"
        from dvadmin.notify.services import get_line_quota
        limit, used = get_line_quota(bot, force=force)
        if limit is None or used is None:
            return DetailResponse(data=None)
        return DetailResponse(data={
            "used": used,
            "limit": limit,
            "local_used": used,
            "source": "line",
        })

    @action(methods=["GET"], detail=False)
    def export_bots(self, request):
        """导出全部 LineBot(含 Channel Access Token / Channel Secret 明文, 供迁移/备份)
        GET /api/notify/linebot/export_bots/ → JSON 附件
        凭据含敏感信息, 仅超管可调用, 请妥善保管文件"""
        rows = []
        for bot in LineBot.objects.all().order_by("id"):
            rows.append({
                "id": bot.id,
                "name": bot.name,
                "bot_code": bot.bot_code,
                "channel_id": bot.channel_id or "",
                "basic_id": bot.basic_id or "",
                "bot_user_id": bot.bot_user_id or "",
                "channel_access_token": bot.channel_access_token,
                "channel_secret": bot.channel_secret,
                "tenant_name": bot.tenant.name if bot.tenant_id else "",
                "is_default": bot.is_default,
                "is_active": bot.is_active,
                "monthly_quota": bot.monthly_quota,
            })
        content = json.dumps({"bots": rows}, ensure_ascii=False, indent=2)
        filename = f"linebot_export_{datetime.now():%Y%m%d%H%M%S}.json"
        response = HttpResponse(content, content_type="application/json; charset=utf-8")
        response["Access-Control-Expose-Headers"] = "Content-Disposition"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(methods=["POST"], detail=False)
    def import_bots(self, request):
        """导入 LineBot(JSON, 与 export_bots 输出格式一致)
        POST /api/notify/linebot/import_bots/  body: {"bots": [...]} 或直接数组
        按 bot_code(唯一) upsert: 已存在则更新, 不存在则新建
        tenant_name 匹配租户 name/code; 找不到的租户行会跳过并记录"""
        from django.apps import apps
        Tenant = apps.get_model("tenant", "Tenant")
        payload = request.data
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                return ErrorResponse(msg=_("Invalid JSON payload"))
        if isinstance(payload, dict):
            payload = payload.get("bots") or payload.get("data") or [payload]
        if not isinstance(payload, list):
            return ErrorResponse(msg=_("Payload must be a list of bots"))
        created = updated = skipped = 0
        errors = []
        seen = set()
        for i, item in enumerate(payload, start=1):
            try:
                if not isinstance(item, dict):
                    errors.append({"row": i, "msg": _("Row is not an object")})
                    skipped += 1
                    continue
                bot_code = str(item.get("bot_code") or "").strip()
                if not bot_code:
                    errors.append({"row": i, "msg": _("bot_code is required")})
                    skipped += 1
                    continue
                if bot_code in seen:
                    errors.append({"row": i, "msg": _("Duplicate bot_code in file: {}").format(bot_code)})
                    skipped += 1
                    continue
                seen.add(bot_code)
                tenant = None
                tenant_ref = str(item.get("tenant_name") or item.get("tenant") or "").strip()
                if tenant_ref:
                    tenant = (Tenant.objects.filter(name=tenant_ref).first()
                              or Tenant.objects.filter(tenant_code=tenant_ref).first())
                    if tenant is None:
                        errors.append({"row": i, "msg": _("Tenant not found: {}").format(tenant_ref)})
                        skipped += 1
                        continue
                mq = item.get("monthly_quota")
                defaults = {
                    "name": str(item.get("name") or bot_code)[:64],
                    "channel_id": item.get("channel_id") or None,
                    "basic_id": item.get("basic_id") or None,
                    "bot_user_id": item.get("bot_user_id") or None,
                    "channel_access_token": str(item.get("channel_access_token") or ""),
                    "channel_secret": str(item.get("channel_secret") or ""),
                    "tenant": tenant,
                    "is_default": bool(item.get("is_default", False)),
                    "is_active": bool(item.get("is_active", True)),
                    "monthly_quota": mq if mq not in (None, "") else None,
                }
                obj, was_created = LineBot.objects.update_or_create(bot_code=bot_code, defaults=defaults)
                if was_created:
                    created += 1
                else:
                    updated += 1
            except Exception as e:
                errors.append({"row": i, "msg": str(e)})
                skipped += 1
        return SuccessResponse(data={
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "errors": errors[:50],
        }, msg=_("Import finished: {} created, {} updated, {} skipped").format(created, updated, skipped))


class MessageLogViewSet(CustomModelViewSet):
    """消息记录(租户只读: 看本租户消息; 写/导出仍超管)"""
    queryset = MessageLog.objects.all()
    serializer_class = MessageLogSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if getattr(user, "is_superuser", False):
            return qs
        tenant = getattr(user, "tenant", None)
        if tenant is None:
            return qs.none()
        return qs.filter(tenant=tenant)

    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        # 租户只能读(GET); 其它写操作仍要求超管
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [SuperuserPermission()]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data, msg=_("Fetched successfully"))


__all__ = ["LineBotViewSet", "MessageLogViewSet"]
