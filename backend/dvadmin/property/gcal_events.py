# -*- coding: utf-8 -*-
"""
Google Calendar 房源事件写入/同步/删除
- event_id_01: 周期付租提醒(从 rent_start 到 rent_end, 按 pay_period 每月/每季, remind_day 那天)
- event_id_02: 结束日期事件(rent_end, 红色)
- 自定义规则(ReminderRule): 每规则一个循环事件, event_id 记录在 rule.event_id
  事件类型(type)对齐本地提醒日历: Rent Reminder/Expiry/Utility Reminder/Custom Reminder
参考旧单用户版 refer/ant_notify/ant_calendar/cal_01.py
"""
from datetime import date, timedelta
import calendar as _calendar

from django.conf import settings
from googleapiclient.errors import HttpError

from dvadmin.utils.google_calendar import get_calendar_service

EVENT_01_COLOR = '9'   # 蓝色(周期付租提醒 R)
EVENT_02_COLOR = '11'  # 红色(结束日期 E)
EVENT_UTILITY_COLOR = '10'  # 绿色(水电提醒 U)
EVENT_CUSTOM_COLOR = '10'  # 绿色(自定义提醒 C)

# 事件类型后缀(对齐本地提醒日历 kind: rent/end/utility/custom; 本地图例 R蓝/C绿/E红)
TYPE_RENT = 'rent'
TYPE_END = 'end'
TYPE_UTILITY = 'utility'
TYPE_CUSTOM = 'custom'

_TYPE_SUFFIX = {
    TYPE_RENT: 'R',
    TYPE_END: 'E',
    TYPE_UTILITY: 'U',
    TYPE_CUSTOM: 'C',
}

_PERIOD_MONTHS = {
    'Monthly': 1,
    'Quarterly': 3,
    'HalfYear': 6,
    'Yearly': 12,
}


def _calendar_id_for(prop):
    """优先取创建人(中介)的 Google 日历, 否则取租户默认"""
    creator = getattr(prop, 'creator', None)
    if creator and getattr(creator, 'google_calendar_id', None):
        return creator.google_calendar_id
    tenant = getattr(prop, 'tenant', None)
    if tenant and getattr(tenant, 'google_calendar_id', None):
        return tenant.google_calendar_id
    return None


def _until(prop):
    """
    RRULE UNTIL 截止(循环事件的最后一天 = 结束日期前一天)
    对齐本地提醒日历: rent/custom 提醒在 rent_end 当天不显示(跳过 d>=rent_end), 只显示到期事件
    """
    if not prop.rent_end:
        return ''
    last = prop.rent_end - timedelta(days=1)
    return last.strftime('%Y%m%dT000000Z')


def _event_summary(prop, kind, extra=''):
    """事件标题: 房源名[类型码]; 类型码放在末尾且尽量短, 如: Elements 101 [R]"""
    code = _TYPE_SUFFIX.get(kind, '')
    return f'{prop.name}{extra} [{code}]' if code else prop.name


def _first_remind_date(prop, period, day, from_date=None):
    """
    计算某周期+提醒日从 from_date(默认 rent_start)起第一次命中日期(>= from_date)
    与本地提醒日历 CalendarView 的迭代逻辑一致:
    - 周期: 以 rent_start 所在月份为基准(Monthly 每月, Quarterly 每3月, ...)
    - 提醒日: min(day, 当月天数)
    若到 rent_end 都没有命中返回 None
    """
    from_date = from_date or prop.rent_start
    if not from_date or not prop.rent_end:
        return None
    interval = _PERIOD_MONTHS.get(period, 1)
    base_month = from_date.month
    y, m = from_date.year, from_date.month
    for _ in range(24):
        if (m - base_month) % interval == 0:
            d = min(day, _calendar.monthrange(y, m)[1])
            cand = date(y, m, d)
            if cand >= from_date and cand <= prop.rent_end:
                return cand
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return None


def _rrule_day(day):
    """BYMONTHDAY; remind_day>28 在短月无意义, 统一用 -1(每月最后一天)"""
    return day if day <= 28 else -1


def build_pay_event_body(prop, first_date=None):
    """周期付租提醒事件(event_01)"""
    first = first_date or _first_remind_date(prop, prop.pay_period, prop.remind_day)
    if first is None:
        first = prop.rent_start
    interval = _PERIOD_MONTHS.get(prop.pay_period, 1)
    rrule = [
        f'RRULE:FREQ=MONTHLY;INTERVAL={interval};BYMONTHDAY={_rrule_day(prop.remind_day)};UNTIL={_until(prop)}'
    ]
    return {
        'summary': _event_summary(prop, TYPE_RENT),
        'description': 'Rent reminder (auto)',
        'start': {'date': first.strftime('%Y-%m-%d')},
        'end': {'date': (first + timedelta(days=1)).strftime('%Y-%m-%d')},
        'recurrence': rrule,
        'colorId': EVENT_01_COLOR,
    }


def build_end_event_body(prop):
    """结束日期事件(event_02, 红色)"""
    return {
        'summary': _event_summary(prop, TYPE_END),
        'description': 'Lease ends (auto)',
        'start': {'date': prop.rent_end.strftime('%Y-%m-%d')},
        'end': {'date': (prop.rent_end + timedelta(days=1)).strftime('%Y-%m-%d')},
        'colorId': EVENT_02_COLOR,
    }


def build_rule_event_body(prop, rule, first_date=None):
    """自定义规则循环事件; 周期对齐 rule.period, 提醒日对齐 rule.day"""
    from dvadmin.notify.tasks import build_rule_message

    first = first_date or _first_remind_date(prop, rule.period, rule.day)
    if first is None:
        first = prop.rent_start
    interval = _PERIOD_MONTHS.get(rule.period, 1)
    rrule = [f'RRULE:FREQ=MONTHLY;INTERVAL={interval};BYMONTHDAY={_rrule_day(rule.day)}']
    until = _until(prop)
    if until:
        rrule[0] += f';UNTIL={until}'

    kind = rule.type if rule.type in (TYPE_UTILITY, TYPE_CUSTOM) else TYPE_CUSTOM
    color = EVENT_UTILITY_COLOR if kind == TYPE_UTILITY else EVENT_CUSTOM_COLOR
    desc = build_rule_message(prop, rule) or ''
    return {
        'summary': _event_summary(prop, kind),
        'description': desc,
        'start': {'date': first.strftime('%Y-%m-%d')},
        'end': {'date': (first + timedelta(days=1)).strftime('%Y-%m-%d')},
        'recurrence': rrule,
        'colorId': color,
    }


def _upsert_event(service, calendar_id, event_id, body):
    """
    更新或插入事件, 返回事件ID
    若已记录 event_id 对应的旧事件在 Google 已被删(404/410)或无法更新, 则删除记录并重新插入
    """
    if event_id:
        try:
            service.events().update(calendarId=calendar_id, eventId=event_id, body=body).execute()
            return event_id
        except HttpError as e:
            status = getattr(getattr(e, 'resp', None), 'status', None)
            if status in (404, 410):
                event_id = None
            else:
                raise
    created = service.events().insert(calendarId=calendar_id, body=body).execute()
    return created['id']


def _delete_event(service, calendar_id, event_id):
    if not event_id:
        return
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    except HttpError:
        pass


def sync_property_events(prop, legacy_calendar_id=None):
    """
    创建或更新房源的两个日历事件 + 全部自定义规则事件, 并回写事件ID/calendar_id
    - 换日历: 目标日历 != 已记录日历 → 先删旧日历事件, 再写入新日历
      (旧数据 calendar_id 为 NULL 时, 用 legacy_calendar_id=租户改前的旧日历ID 兜底删除旧事件)
    - 清空日历(目标为 None): 删除已记录日历上的事件并重置事件ID
    返回 (ok, msg)
    """
    from dvadmin.property.models import ReminderRule

    if not prop.calendar_in or not prop.rent_start or not prop.rent_end:
        return False, '无需写入(未开启日历或缺少起止日期)'
    target = _calendar_id_for(prop)
    if not target:
        # 日历被清空: 删除旧日历上的事件
        if prop.calendar_id or legacy_calendar_id:
            delete_property_events(prop, calendar_id=prop.calendar_id or legacy_calendar_id)
            return True, '已清除旧日历事件(日历已清空)'
        return False, '缺少 Google 日历ID(中介或租户未配置)'
    service = get_calendar_service()
    try:
        # 日历变更: 先删旧日历事件, 重置事件ID(旧数据 calendar_id 为 NULL 用 legacy_calendar_id 兜底)
        old_cal = prop.calendar_id or legacy_calendar_id
        if old_cal and old_cal != target:
            for eid in (prop.event_id_01, prop.event_id_02):
                _delete_event(service, old_cal, eid)
            for rule in ReminderRule.objects.filter(property=prop):
                _delete_event(service, old_cal, rule.event_id)
                rule.event_id = None
                rule.save(update_fields=['event_id'])
            prop.event_id_01 = None
            prop.event_id_02 = None

        # --- event_01: 周期付租 ---
        prop.event_id_01 = _upsert_event(service, target, prop.event_id_01, build_pay_event_body(prop))
        # --- event_02: 结束日期(红色) ---
        prop.event_id_02 = _upsert_event(service, target, prop.event_id_02, build_end_event_body(prop))

        # --- 自定义规则事件 ---
        for rule in ReminderRule.objects.filter(property=prop, enabled=True):
            rule.event_id = _upsert_event(service, target, rule.event_id, build_rule_event_body(prop, rule))
            rule.save(update_fields=['event_id'])
        # 已停用的规则: 删除其事件
        for rule in ReminderRule.objects.filter(property=prop, enabled=False):
            if rule.event_id:
                _delete_event(service, target, rule.event_id)
                rule.event_id = None
                rule.save(update_fields=['event_id'])

        prop.calendar_id = target
        prop.save(update_fields=['event_id_01', 'event_id_02', 'calendar_id'])
        return True, '日历同步成功'
    except HttpError as e:
        return False, f'Google API 错误: {e}'


def sync_tenant_events(tenant, legacy_calendar_id=None):
    """
    同步某租户下所有开启日历的房源(用于租户更换/清空 Google 日历后一键迁移)
    legacy_calendar_id: 租户改前的旧日历ID, 用于清理旧数据(calendar_id 为 NULL)的旧事件
    返回 (ok_count, fail_count, msgs)
    """
    from dvadmin.property.models import Property
    qs = Property.objects.filter(tenant=tenant, calendar_in=True)
    ok = fail = 0
    msgs = []
    for prop in qs:
        o, m = sync_property_events(prop, legacy_calendar_id=legacy_calendar_id)
        if o:
            ok += 1
        else:
            fail += 1
            msgs.append(f'[{prop.name}] {m}')
    return ok, fail, msgs[:20]


def delete_events_by_ids(calendar_id, event_id_01=None, event_id_02=None):
    """按事件ID删除(仅传日历ID与事件ID), 用于房源已被删除的场景"""
    if not calendar_id:
        return
    service = get_calendar_service()
    for eid in (event_id_01, event_id_02):
        _delete_event(service, calendar_id, eid)


def delete_property_events(prop, calendar_id=None):
    """删除房源的两个日历事件 + 全部规则事件(用于房源删除/清空日历时)"""
    from dvadmin.property.models import ReminderRule

    calendar_id = calendar_id or _calendar_id_for(prop)
    if not calendar_id:
        return
    service = get_calendar_service()
    for eid in (prop.event_id_01, prop.event_id_02):
        _delete_event(service, calendar_id, eid)
    for rule in ReminderRule.objects.filter(property=prop):
        if rule.event_id:
            _delete_event(service, calendar_id, rule.event_id)
            rule.event_id = None
            rule.save(update_fields=['event_id'])
    prop.event_id_01 = None
    prop.event_id_02 = None
    prop.save(update_fields=['event_id_01', 'event_id_02'])