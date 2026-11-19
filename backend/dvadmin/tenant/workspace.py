# -*- coding: utf-8 -*-
"""
租户端工作台数据(非超管自用)
- 未来 3 天将要发送提醒的房源 (next_remind_date: 付租周期提醒日)
- 房源快检(总数/临近到期/最近更新)
"""
import calendar
from datetime import date, datetime, timedelta

from django.utils.translation import gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from dvadmin.notify.models import get_bot_for_property
from dvadmin.notify.services import (get_cached_group_name, get_group_name,
                                     push_to_group)
from dvadmin.notify.tasks import (_within_rent_range, _is_pay_period_month, _pay_remind_day_hit,
                                  build_rent_message, build_maturity_message, _already_sent_today,
                                  _rule_hit, _rule_next_date, build_rule_message, _remind_day_hit)
from dvadmin.property.models import Property, ReminderRule
from dvadmin.utils.filters import apply_owner_data_scope
from dvadmin.utils.json_response import SuccessResponse


def _effective_remind_day(year, month, remind_day):
    """提醒日超过当月天数(如 30/31 在 2 月)时取当月末, 与 tasks.py 语义一致"""
    return min(remind_day, calendar.monthrange(year, month)[1])


def _next_proper_month(y, m):
    if m == 13:
        return y + 1, 1
    return y, m


def _next_remind_date(prop, from_date):
    """
    未来最近一次付租提醒日期(>= from_date)
    - Monthly: 每月 remind_day
    - Quarterly/HalfYear/Yearly: 以 rent_start 月份为基准, 每 N 个月
    返回 date 或 None
    """
    from dvadmin.notify.tasks import _period_months
    remind = prop.remind_day
    if not remind:
        return None
    interval = _period_months(prop.pay_period)
    if interval > 1:
        base_month = (prop.rent_start.month if prop.rent_start else from_date.month) % 12 or 12
        y, m = from_date.year, from_date.month
        for _ in range(12):
            if (m - base_month) % interval == 0:
                day = _effective_remind_day(y, m, remind)
                cand = date(y, m, day)
                if cand >= from_date:
                    return cand
            y, m = _next_proper_month(y, m + 1)
        return None
    # Monthly
    day = _effective_remind_day(from_date.year, from_date.month, remind)
    cand = date(from_date.year, from_date.month, day)
    if cand >= from_date:
        return cand
    y, m = _next_proper_month(from_date.year, from_date.month + 1)
    return date(y, m, _effective_remind_day(y, m, remind))


class TenantHomeView(APIView):
    """租户工作台(仅租户普通用户; 超管请用 /api/tenant/admin/dashboard/)"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if getattr(user, "is_superuser", False):
            return SuccessResponse(data={})
        tenant = getattr(user, "tenant", None)
        if tenant is None:
            return SuccessResponse(data=self._empty())

        today = date.today()
        week_end = today + timedelta(days=3)  # 未来 3 天(实际会发)
        # 租户硬隔离 之后, 再叠加 owner 数据范围(经理=全部, 主管=本部门及以下, 员工=仅本人)
        # 复用房源列表的数据范围配置(GET /api/property/property/)
        properties = list(apply_owner_data_scope(
            request, Property.objects.filter(tenant=tenant).select_related("line_bot", "owner"),
            api="/api/property/property/", method="GET"))

        # 未来 3 天【实际会发】的提醒
        upcoming = []
        # 到期提醒提前天数: 30 天与 15 天两个节点(与 send 逻辑一致)
        END_AHEAD = [30, 15]
        for p in properties:
            if p.rent_end and p.rent_end < today:
                continue
            if p.rent_start and p.rent_start > week_end:
                continue
            # 1) 到期提醒: 只在 30/15 天前这两个触发点落在未来 3 天内时列出
            if p.rent_end:
                for ahead in END_AHEAD:
                    trigger = p.rent_end - timedelta(days=ahead)
                    if today <= trigger <= week_end:
                        upcoming.append({
                            "id": p.id,
                            "name": p.name,
                            "rent_amount": str(p.rent_amount) if p.rent_amount is not None else None,
                            "pay_period": p.pay_period,
                            "remind_day": p.remind_day,
                            "rent_start": p.rent_start.isoformat() if p.rent_start else None,
                            "rent_end": p.rent_end.isoformat() if p.rent_end else None,
                            "next_remind": trigger.isoformat(),
                            "days": (trigger - today).days,
                            "ahead": ahead,
                            "kind": "end",
                            "sent_today": _already_sent_today(p, "maturity", datetime.combine(today, datetime.min.time())),
                            "line_bot_name": p.line_bot.name if p.line_bot_id else None,
                            "group_id": p.group_id,
                            "group_name": get_cached_group_name(p.line_bot, p.group_id),
                        })
            # 2) 付租提醒: 未来 3 天内实际要付租
            nd = _next_remind_date(p, today)
            if nd and nd <= week_end:
                upcoming.append({
                    "id": p.id,
                    "name": p.name,
                    "rent_amount": str(p.rent_amount) if p.rent_amount is not None else None,
                    "pay_period": p.pay_period,
                    "remind_day": p.remind_day,
                    "rent_start": p.rent_start.isoformat() if p.rent_start else None,
                    "rent_end": p.rent_end.isoformat() if p.rent_end else None,
                    "next_remind": nd.isoformat(),
                    "days": (nd - today).days,
                    "kind": "rent",
                    "sent_today": _already_sent_today(p, "rent", datetime.combine(today, datetime.min.time())),
                    "line_bot_name": p.line_bot.name if p.line_bot_id else None,
                    "group_id": p.group_id,
                    "group_name": get_cached_group_name(p.line_bot, p.group_id),
                })
            # 3) 自定义规则(水电/自定义): 未来 3 天内要触发
            for rule in ReminderRule.objects.filter(property=p, enabled=True):
                rd = _rule_next_date(p, rule, today)
                if rd and rd <= week_end:
                    rtype = rule.type if rule.type in ("utility", "custom") else "custom"
                    upcoming.append({
                        "id": p.id,
                        "name": p.name,
                        "rent_amount": str(p.rent_amount) if p.rent_amount is not None else None,
                        "pay_period": p.pay_period,
                        "remind_day": p.remind_day,
                        "rent_start": p.rent_start.isoformat() if p.rent_start else None,
                        "rent_end": p.rent_end.isoformat() if p.rent_end else None,
                        "next_remind": rd.isoformat(),
                        "days": (rd - today).days,
                        "kind": rtype,
                        "rule_id": rule.id,
                        "rule_type": rule.type,
                        "rule_name": rule.get_type_display(),
                        "rule_day": rule.day,
                        "rule_period": rule.period,
                        "sent_today": _already_sent_today(p, rtype, datetime.combine(today, datetime.min.time()), rule_id=rule.id),
                        "line_bot_name": p.line_bot.name if p.line_bot_id else None,
                        "group_id": p.group_id,
                        "group_name": get_cached_group_name(p.line_bot, p.group_id),
                    })
        upcoming.sort(key=lambda x: x["days"])

        # 快检
        ending_soon = [p for p in properties if p.rent_end and today <= p.rent_end <= today + timedelta(days=30)]
        recent = sorted(properties, key=lambda p: p.update_datetime or p.create_datetime, reverse=True)[:5]

        from dvadmin.tenant.serializers import _tenant_expired
        return SuccessResponse(data={
            "tenant": {"id": tenant.id, "name": tenant.name, "tenant_code": tenant.tenant_code,
                       "sign_name": tenant.sign_name or "", "google_calendar_id": tenant.google_calendar_id or "",
                       "referral_code": tenant.referral_code or "",
                       "is_expired": _tenant_expired(tenant),
                       "expire_time": tenant.expire_time.strftime("%Y-%m-%d %H:%M:%S") if tenant.expire_time else None},
            "stats": {
                "total": len(properties),
                "active": sum(1 for p in properties if p.rent_end is None or p.rent_end >= today),
                "ending_soon": len(ending_soon),
                "upcoming_7d": len(upcoming),
            },
            "upcoming": upcoming[:10],
            "recent": [{
                "id": r.id,
                "name": r.name,
                "rent_amount": str(r.rent_amount) if r.rent_amount is not None else None,
                "rent_start": r.rent_start.isoformat() if r.rent_start else None,
                "rent_end": r.rent_end.isoformat() if r.rent_end else None,
                "pay_period": r.pay_period or "Monthly",
                "owner_name": r.owner.name if r.owner_id else None,
                "update_datetime": (r.update_datetime or r.create_datetime).strftime("%Y-%m-%d %H:%M"),
            } for r in recent],
        })

    def _empty(self):
        return {
            "tenant": None,
            "stats": {"total": 0, "active": 0, "ending_soon": 0, "upcoming_7d": 0},
            "upcoming": [],
            "recent": [],
        }


class GroupNameRefreshView(APIView):
    """刷新某房源的 Line 群名称(绕过缓存强制重新拉取)"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        prop_id = request.data.get("property_id")
        if not prop_id:
            return SuccessResponse(data={"ok": False, "group_name": None, "error": "缺少 property_id"})
        user = request.user
        tenant = getattr(user, "tenant", None)
        qs = Property.objects.filter(pk=prop_id)
        if not getattr(user, "is_superuser", False) and tenant is not None:
            qs = qs.filter(tenant=tenant)
        prop = qs.select_related("line_bot").first()
        if prop is None:
            return SuccessResponse(data={"ok": False, "group_name": None, "error": "房源不存在或无权访问"})
        name, err = get_group_name(prop.line_bot, prop.group_id, force=True)
        return SuccessResponse(data={"ok": name is not None, "group_name": name, "error": err})


class SendReminderNowView(APIView):
    """手动立即发送某房源的今日提醒(只发这一条, 不走定时任务)"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        prop_id = request.data.get("property_id")
        kind = request.data.get("kind") or "rent"
        rule_id = request.data.get("rule_id")
        # 前端工作台用 kind="end" 表示租期到期; 后端内部统一用 "maturity"
        if kind == "end":
            kind = "maturity"
        if not prop_id:
            return SuccessResponse(data={"ok": False, "message": _("Missing property_id")})

        user = request.user
        tenant = getattr(user, "tenant", None)
        # 租户已到期/停用时如实告知, 以免用户误以为是网络/群权限问题
        from dvadmin.tenant.serializers import _tenant_expired
        if tenant is not None and _tenant_expired(tenant):
            return SuccessResponse(data={"ok": False, "message": _("Tenant is expired or inactive, please renew your plan")})
        # 数据范围: 复用房源列表配置(经理=全部, 主管=本部门及以下, 员工=仅本人)
        visible = apply_owner_data_scope(
            request, Property.objects.filter(tenant=tenant) if tenant else Property.objects.none(),
            api="/api/property/property/", method="GET")
        prop = visible.select_related("line_bot", "tenant").filter(pk=prop_id).first()
        if prop is None:
            return SuccessResponse(data={"ok": False, "message": _("Property does not exist or no access permission")})

        # 今日是否确有提醒命中(与 scan_and_notify 一致)
        today = datetime.combine(date.today(), datetime.min.time())
        if not _within_rent_range(prop, today):
            return SuccessResponse(data={"ok": False, "message": _("Not within the rent start ~ end period")})
        if not prop.group_id:
            return SuccessResponse(data={"ok": False, "message": _("This property has no LINE group ID set")})

        # 自定义规则: 按 rule_id 直接定位(校验归属房源与数据范围)
        rule = None
        if rule_id:
            rule = ReminderRule.objects.filter(pk=rule_id, property=prop).first()
            if rule is None:
                return SuccessResponse(data={"ok": False, "message": _("Rule does not exist or does not belong to this property")})
            if not rule.enabled:
                return SuccessResponse(data={"ok": False, "message": _("This rule is disabled")})

        pay_hit = bool(prop.remind_day) and _is_pay_period_month(today, prop) and _pay_remind_day_hit(today, prop)
        maturity_hit = bool(prop.rent_end) and ((prop.rent_end - today.date()).days in (30, 15))

        if rule is not None:
            if not _rule_hit(today, prop, rule):
                return SuccessResponse(data={"ok": False, "message": _("Today is not the reminder day for this rule (utility/custom)")})
        else:
            if kind == "maturity" and not maturity_hit:
                return SuccessResponse(data={"ok": False, "message": _("Today is not the expiry reminder day for this property")})
            if kind == "rent" and not pay_hit:
                return SuccessResponse(data={"ok": False, "message": _("Today is not the rent reminder day for this property")})
            if not (pay_hit or maturity_hit):
                return SuccessResponse(data={"ok": False, "message": _("There is no reminder to send today")})

        bot = get_bot_for_property(prop)
        if bot is None:
            return SuccessResponse(data={"ok": False, "message": _("No LINE Bot assigned to this tenant, cannot send")})
        if not bot.is_active:
            return SuccessResponse(data={"ok": False, "message": _("Bot({}) is disabled, cannot send").format(bot.name)})
        if bot.tenant_id is not None and bot.tenant_id != prop.tenant_id:
            return SuccessResponse(data={"ok": False, "message": _("Bot ownership check failed, sending rejected")})

        if rule is not None:
            message = build_rule_message(prop, rule)
            rtype = rule.type if rule.type in ("utility", "custom") else "custom"
            ok = push_to_group(bot, prop.group_id, message, tenant=prop.tenant, prop=prop,
                               msg_type=rtype, group_size=prop.group_size or 1,
                               timeout=8, retries=1, rule_id=str(rule.id))
        else:
            message = build_maturity_message(prop, prop.rent_end) if kind == "maturity" else build_rent_message(prop)
            # 手动触发用快速失败策略(1 次、短超时), 避免前台等重试链超时
            ok = push_to_group(bot, prop.group_id, message, tenant=prop.tenant, prop=prop,
                               msg_type="maturity" if kind == "maturity" else "rent",
                               group_size=prop.group_size or 1, timeout=8, retries=1)
        if ok:
            return SuccessResponse(data={"ok": True, "message": _("Sent to the group")})
        return SuccessResponse(data={"ok": False, "message": _("Send failed: cannot connect to LINE or insufficient group permission (check network/proxy and retry)")})


class CalendarView(APIView):
    """内置提醒日历: 返回某月区间内的所有提醒事件(付租/到期), 实时计算, 不落事件表

    请求: GET /api/tenant/workspace/calendar/?year=2026&month=9
    返回: { days: { "2026-09-05": [{id,name,kind,pay_period,remind_day,...}], ... }, month }
    权限: 本租户用户(数据范围=房源列表范围)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if getattr(user, "is_superuser", False):
            return SuccessResponse(data={"month": None, "days": {}})
        tenant = getattr(user, "tenant", None)
        if tenant is None:
            return SuccessResponse(data={"month": None, "days": {}})

        # 目标月
        try:
            year = int(request.query_params.get("year", date.today().year))
            month = int(request.query_params.get("month", date.today().month))
        except (TypeError, ValueError):
            return SuccessResponse(data={"month": None, "days": {}})
        if not 1 <= month <= 12:
            return SuccessResponse(data={"month": None, "days": {}})

        month_start = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        month_end = date(year, month, last_day)
        today = date.today()

        # 网格范围(周日起始, 6行=42格), 用于把"相邻月灰色格子"里的日期也纳入显示(对齐 Google)
        grid_start = month_start - timedelta(days=((month_start.weekday() + 1) % 7))
        grid_end = grid_start + timedelta(days=41)

        properties = list(apply_owner_data_scope(
            request, Property.objects.filter(tenant=tenant).select_related("line_bot", "owner"),
            api="/api/property/property/", method="GET"))

        events_map = {}  # iso-date -> list

        def _put(d, ev):
            events_map.setdefault(d.isoformat(), []).append(ev)

        for p in properties:
            # 与 Google 一致: 历史已结束的房源仍显示其历史事件(结束日期/过往付租日), 不隐藏
            # 到期事件: 与 Google Calendar 一致, 只显示结束日期当天(rent_end), 不显示提前30/15天
            if p.rent_end:
                if grid_start <= p.rent_end <= grid_end:
                    _put(p.rent_end, {
                        "id": p.id, "name": p.name, "kind": "end",
                        "rent_amount": str(p.rent_amount) if p.rent_amount is not None else None,
                        "rent_start": p.rent_start.isoformat() if p.rent_start else None,
                        "rent_end": p.rent_end.isoformat() if p.rent_end else None,
                        "line_bot_name": p.line_bot.name if p.line_bot_id else None,
                        "group_id": p.group_id,
                    })
            # 自定义规则: 网格范围内每个实际提醒日(水电/自定义, 周期+提醒日)
            for rule in ReminderRule.objects.filter(property=p, enabled=True):
                if not rule.day:
                    continue
                d_iter = grid_start
                while d_iter <= grid_end:
                    d = d_iter
                    if p.rent_start and d < p.rent_start:
                        d_iter += timedelta(days=1)
                        continue
                    if p.rent_end and d >= p.rent_end:
                        d_iter += timedelta(days=1)
                        continue
                    if not _is_pay_period_month(datetime.combine(d, datetime.min.time()), p, rule.period):
                        d_iter += timedelta(days=1)
                        continue
                    if not _remind_day_hit(datetime.combine(d, datetime.min.time()), rule.day):
                        d_iter += timedelta(days=1)
                        continue
                    rtype = rule.type if rule.type in ("utility", "custom") else "custom"
                    _put(d, {
                        "id": p.id, "name": p.name, "kind": rtype,
                        "rule_id": rule.id,
                        "rule_type": rule.type,
                        "rule_name": rule.get_type_display(),
                        "pay_period": rule.period, "remind_day": rule.day,
                        "rent_amount": str(p.rent_amount) if p.rent_amount is not None else None,
                        "rent_start": p.rent_start.isoformat() if p.rent_start else None,
                        "rent_end": p.rent_end.isoformat() if p.rent_end else None,
                        "line_bot_name": p.line_bot.name if p.line_bot_id else None,
                        "group_id": p.group_id,
                    })
                    d_iter += timedelta(days=1)
            # 付租提醒: 网格范围内每个实际付租提醒日(与 Google Calendar event_01 一致: 从 rent_start 起, 按周期, remind_day 那天)
            if p.remind_day:
                # 迭代网格范围内的每一天
                d_iter = grid_start
                while d_iter <= grid_end:
                    d = d_iter
                    # 与 Google 一致: 起租日(rent_start)之前不显示; 已过去的历史提醒也显示(谷歌会显示)
                    if p.rent_start and d < p.rent_start:
                        d_iter += timedelta(days=1)
                        continue
                    # 与 Google UNTIL=rent_end 一致: 结束日期当天不再显示付租提醒
                    if p.rent_end and d >= p.rent_end:
                        d_iter += timedelta(days=1)
                        continue
                    if not _is_pay_period_month(datetime.combine(d, datetime.min.time()), p):
                        d_iter += timedelta(days=1)
                        continue
                    if not _pay_remind_day_hit(datetime.combine(d, datetime.min.time()), p):
                        d_iter += timedelta(days=1)
                        continue
                    _put(d, {
                        "id": p.id, "name": p.name, "kind": "rent",
                        "pay_period": p.pay_period, "remind_day": p.remind_day,
                        "rent_amount": str(p.rent_amount) if p.rent_amount is not None else None,
                        "rent_start": p.rent_start.isoformat() if p.rent_start else None,
                        "rent_end": p.rent_end.isoformat() if p.rent_end else None,
                        "line_bot_name": p.line_bot.name if p.line_bot_id else None,
                        "group_id": p.group_id,
                    })
                    d_iter += timedelta(days=1)

        for ev_list in events_map.values():
            ev_list.sort(key=lambda e: (e["kind"], e["name"]))

        return SuccessResponse(data={
            "month": {"year": year, "month": month},
            "today": today.isoformat(),
            "days": events_map,
        })