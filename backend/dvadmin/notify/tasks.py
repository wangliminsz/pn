# -*- coding: utf-8 -*-
"""
每日提醒任务(Celery)
复刻旧 refer/ant_notify/ant_assist_notify/aanotify.py 逻辑:
1. 付租提醒: 每月 remind_day 天(含闰年/月末特殊处理)
2. 到期提醒: rent_end 前 30 天 / 15 天
按租户取 bot, 走 notify.services push
"""
import calendar
import logging
from datetime import date, datetime, timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from dvadmin.notify.models import MessageLog
from dvadmin.notify.services import push_to_group

logger = logging.getLogger(__name__)


# ---------------- 提醒模板(中/英/泰) ----------------
def _period_months(period):
    """付租周期/规则周期 → 间隔月数(Monthly=1, Quarterly=3, HalfYear=6, Yearly=12)"""
    return {
        "Monthly": 1,
        "Quarterly": 3,
        "HalfYear": 6,
        "Yearly": 12,
    }.get(period, 1)


def _is_pay_period_month(now, property_, period=None):
    """
    判断当月是否是该房源的付租周期(或某规则周期)
    - period: 默认取 property_.pay_period(Monthly/Quarterly/HalfYear/Yearly)
    - Monthly: 每月
    - Quarterly/HalfYear/Yearly: 每 N 个月, 以 rent_start 的月份为基准
    """
    period = period or getattr(property_, "pay_period", "Monthly")
    interval = _period_months(period)
    if interval <= 1:
        return True
    base_month = property_.rent_start.month if (getattr(property_, 'rent_start', None)) else now.month
    return (now.month - base_month) % interval == 0


def _pay_remind_day_hit(now, property_):
    """
    付租提醒日是否命中, 处理闰年/月末
    返回 True 表示今天应发提醒
    """
    remind_day = property_.remind_day
    today = now.day
    last_day = calendar.monthrange(now.year, now.month)[1]

    # 提醒日超过当月天数(如 30/31 号在2月), 则取当月末
    effective_day = min(remind_day, last_day)
    return today == effective_day


def _effective_remind_day(year, month, remind_day):
    """提醒日超过当月天数(如 30/31 在 2 月)时取当月末"""
    return min(remind_day, calendar.monthrange(year, month)[1])


def _remind_day_hit(now, day):
    """通用: 某规则/提醒日在当月是否命中(超当月天数取月末)"""
    if not day:
        return False
    return now.day == _effective_remind_day(now.year, now.month, day)


def _within_rent_range(prop, now):
    """是否在起租~结束范围内"""
    if prop.rent_start and now.date() < prop.rent_start:
        return False
    if prop.rent_end and now.date() > prop.rent_end:
        return False
    return True


def _get_signature(prop=None):
    """签名落款: 优先租户自定义签名, 否则租户公司名, 否则 settings.LINE_SIGNATURE, 否则 'proNotify'"""
    from django.conf import settings
    if prop is not None and getattr(prop, 'tenant', None):
        t = prop.tenant
        custom = getattr(t, 'sign_name', None)
        if custom:
            return custom
        if getattr(t, 'name', None):
            return t.name
    return getattr(settings, 'LINE_SIGNATURE', None) or 'proNotify'


def _fill_props(text, **kwargs):
    """替换自定义消息中的变量占位(找不到的变量置空); 并把字面量 \\n 转成真换行"""
    if not text:
        return text
    out = text
    for key, val in kwargs.items():
        out = out.replace("{%s}" % key, str(val or ""))
    if "\\r\\n" in out:
        out = out.replace("\\r\\n", "\r\n")
    if "\\n" in out:
        out = out.replace("\\n", "\n")
    return out


def _read_message_template(key):
    """读取系统级默认消息模板(SystemConfig)
    未配置/空白返回 None, 调用方回退内置硬编码模板
    """
    try:
        from dvadmin.system.models import SystemConfig
        row = SystemConfig.objects.filter(key=key).first()
        if row is not None and row.value:
            text = str(row.value).strip()
            if text:
                return text
    except Exception:
        pass
    return None


def build_rent_message(prop):
    """付租提醒文案(泰/英); 优先级: 房源 custom_pay_message > SystemConfig(notify.rent_template) > 内置默认"""
    name = prop.name or ""
    sign = _get_signature(prop)
    rent = (str(prop.rent_amount) if prop.rent_amount is not None else "")
    date = (prop.rent_start.strftime("%Y-%m-%d") if prop.rent_start else "")
    rent_end = (prop.rent_end.strftime("%Y-%m-%d") if prop.rent_end else "")
    if getattr(prop, "custom_pay_message", None):
        return _fill_props(prop.custom_pay_message, name=name, rent=rent, date=date, sign=sign)
    tpl = _read_message_template("notify.rent_template")
    if tpl:
        return _fill_props(tpl, name=name, rent=rent, date=date, rent_end=rent_end, sign=sign)
    msg01 = "เรียน ท่านผู้เช่า\r\n\nแจ้งเตือนการชำระค่าเช่าห้องที่ท่านอาศัยอยู่ในขณะนี้ หวังว่าจะได้รับความร่วมมือจากท่าน\r\n\nขออภัยหากชำระแล้ว"
    msg02 = ("Dear Tenant,\r\n\nHi, today is the rental pay day, here is the warm reminding for your rental, "
             "please remember to pay today. Wish you all the best.\r\n\n"
             "Please ignore this message if already paid.\r\n\nThanks very much~")
    msg03 = "Kind Regards,\r\n" + sign
    return f"{name}:\r\n\n{msg01}\r\n\n{msg02}\r\n\n{msg03}"


def build_maturity_message(prop, rent_end):
    """到期提醒文案(泰/英); 优先级: 房源 custom_end_message > SystemConfig(notify.maturity_template) > 内置默认"""
    name = prop.name or ""
    sign = _get_signature(prop)
    end_str = rent_end.strftime("%Y-%m-%d") if rent_end else ""
    date = (prop.rent_start.strftime("%Y-%m-%d") if prop.rent_start else "")
    rent = (str(prop.rent_amount) if prop.rent_amount is not None else "")
    if getattr(prop, "custom_end_message", None):
        return _fill_props(
            prop.custom_end_message,
            name=name,
            rent_end=end_str,
            sign=sign,
        )
    tpl = _read_message_template("notify.maturity_template")
    if tpl:
        return _fill_props(tpl, name=name, rent=rent, date=date, rent_end=end_str, sign=sign)
    msg01 = "เรียน ท่านผู้เช่า\r\n\nการแจ้งเตือน: สัญญาเช่าของคุณจะสิ้นสุดเมื่อวันที่ " + str(end_str) + "\r\n\nหากมีความต้องการใด ๆ กรุณาติดต่อเรา\r\n\nขอบคุณมาก~"
    msg02 = ("Dear Tenant,\r\n\nRemind: your rental contract will end at " + str(end_str) +
             "\r\n\nPlease contact us if any need.\r\n\nThanks very much~")
    msg03 = "Kind Regards,\r\n" + sign
    return f"{name}:\r\n\n{msg01}\r\n\n{msg02}\r\n\n{msg03}"


RULE_PRESET_TEMPLATES = {
    # 预设模板(留空 rule.template 时使用); {name}{amount}{date}{sign} + 规则额外变量
    "utility": (
        "เรียน ท่านผู้เช่า\r\n\nแจ้งเตือนการชำระค่าไฟฟ้าและค่าน้ำ {name} "
        "ยอด {amount} กำหนดชำระวันที่ {date} กรุณาชำระค่าบริการให้เรียบร้อย\r\n\nขอบคุณมาก~\r\n\nKind Regards,\r\n{sign}"
    ),
    "custom": (
        "แจ้งเตือน {name}\r\n\r\n{content}\r\n\r\nKind Regards,\r\n{sign}"
    ),
}


def build_rule_message(prop, rule):
    """
    自定义提醒规则文案: 优先 rule.template(支持 {name}{amount}{date}{sign} + 额外变量 {xxx}),
    否则用预设模板(按 rule.type)
    返回 str
    """
    from dvadmin.property.models import Property
    name = prop.name or ""
    sign = _get_signature(prop)
    extra = dict(rule.extra_vars or {})
    # 金额兜底: 依次尝试常见键, 最后回退房租金额
    amount = (extra.pop("amount", None) or extra.pop("金额", None)
              or extra.pop("电费", None) or extra.pop("水费", None)
              or (str(prop.rent_amount) if prop.rent_amount is not None else ""))
    date = _rule_next_date(prop, rule) or ""
    if rule.template:
        kwargs = {"name": name, "amount": amount, "date": date, "sign": sign, **extra}
        return _fill_props(rule.template, **kwargs)
    preset = RULE_PRESET_TEMPLATES.get(rule.type, RULE_PRESET_TEMPLATES["custom"])
    if rule.type == "utility":
        return _fill_props(preset, name=name, amount=amount or "—", date=date or "—", sign=sign, **extra)
    # custom: 内容=额外变量里的 content/内容
    content = extra.pop("content", None) or extra.pop("内容", None) or ""
    return _fill_props(preset, name=name, content=content, sign=sign, **extra)


def _rule_hit(now, prop, rule):
    """自定义规则今日是否命中: 周期月份 + 提醒日"""
    if not rule.enabled:
        return False
    if not _is_pay_period_month(now, prop, rule.period):
        return False
    return _remind_day_hit(now, rule.day)


def _rule_next_date(prop, rule, from_date=None):
    """自定义规则未来最近一次提醒日期(>= from_date, 默认今天)"""
    from datetime import date as _date
    from_date = from_date or _date.today()
    interval = rule.period_months()
    base_month = prop.rent_start.month if getattr(prop, "rent_start", None) else from_date.month
    y, m = from_date.year, from_date.month
    for _ in range(24):
        if (m - base_month) % interval == 0:
            day = _effective_remind_day(y, m, rule.day)
            cand = _date(y, m, day)
            if cand >= from_date:
                return cand
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
    return None


# ---------------- 核心扫描 ----------------
def _dedup_enabled():
    """
    是否开启「当日防重」门控。
    SystemConfig(key='reminder_dedup') 默认 off: 命中即发(简单可靠, 便于测试)。
    设为 'on'/'true'/'1' 则保留旧行为(同一房源同类型当日成功发送后不再发)。
    """
    try:
        from dvadmin.system.models import SystemConfig
        row = SystemConfig.objects.filter(key="reminder_dedup").first()
        if row is not None and row.value is not None:
            return str(row.value).strip().lower() in ("1", "true", "on", "yes")
    except Exception:
        pass
    return False


def _already_sent_today(prop, msg_type, now, rule_id=None):
    """
    当日防重: 同一房源、同类型(rent/maturity/utility/custom)今天已【成功】发送过则跳过。
    !! 该函数只用于开关开启时的门控 / 工作台绿勾展示;
    !! scan_and_notify 发送前默认不再调用它(命中即发), 除非 _dedup_enabled() 返回 True。
    - 只认 result=success: 失败不算, 宁可多发也不漏发
    - 手动「立即发送」接口不走本函数, 用户主动触发仍可重复发
    - 自定义规则(utility/custom)按 rule_id 单独防重, 互不影响
    """
    if not prop or not prop.id or not msg_type:
        return False
    from dvadmin.notify.models import MessageLog
    day_start = datetime.combine(now.date(), datetime.min.time())
    day_end = day_start + timedelta(days=1)
    qs = MessageLog.objects.filter(
        property_id=prop.id,
        msg_type=msg_type,
        result="success",
        create_datetime__gte=day_start,
        create_datetime__lt=day_end,
    )
    if msg_type in ("utility", "custom") and rule_id:
        qs = qs.filter(rule_id=rule_id)
    return qs.exists()


def scan_and_notify(tenant_ids=None, target_date=None):
    """
    扫描所有房源并推送提醒
    - tenant_ids: 为 None 则扫描全部租户(仅超管/定时任务用)
    - target_date: 指定日期(默认今天), 便于测试
    """
    from dvadmin.property.models import Property
    from dvadmin.notify.models import get_bot_for_property

    now = (target_date or timezone.now().date())
    # 兼容字符串日期, 统一转成 date 再 combine, 避免 TypeError
    if isinstance(now, str):
        from datetime import datetime as _dt
        now = _dt.strptime(now, "%Y-%m-%d").date()
    # 转成 datetime 便于与 now 一致
    now = datetime.combine(now, datetime.min.time())

    qs = Property.objects.filter(group_id__isnull=False)
    if tenant_ids:
        qs = qs.filter(tenant_id__in=tenant_ids)

    # 预取全部启用规则(按房源分组), 避免 N+1
    from dvadmin.property.models import ReminderRule
    rules = list(ReminderRule.objects.filter(enabled=True).select_related("property"))
    rules_by_prop = {}
    for r in rules:
        rules_by_prop.setdefault(r.property_id, []).append(r)

    sent = 0
    alerted_tenants = set()  # 当日已告警"缺bot"的租户, 防止刷屏
    for prop in qs:
        tenant = prop.tenant
        prop_rules = rules_by_prop.get(prop.id, [])

        # 只处理范围内(起租~结束)
        if not _within_rent_range(prop, now):
            continue

        group_size = prop.group_size or 1

        # 判定今日是否有提醒任务触发
        pay_hit = bool(prop.remind_day) and _is_pay_period_month(now, prop) and _pay_remind_day_hit(now, prop)
        maturity_hit = bool(prop.rent_end) and ((prop.rent_end - now.date()).days in (30, 15))
        rules_hit = [r for r in prop_rules if _rule_hit(now, prop, r)]
        if not (pay_hit or maturity_hit or rules_hit):
            continue

        # 今日确实要发提醒 -> 取 bot; 没分配则告警(去重)并跳过, 绝不换别的bot
        bot = get_bot_for_property(prop)
        if bot is None:
            tkey = tenant.id if tenant else 0
            if tkey not in alerted_tenants:
                alerted_tenants.add(tkey)
                msg = f"[无Bot] 租户={getattr(tenant,'name','?')} 今日有房源需提醒, 但未分配任何LineBot, 提醒未发送"
                logger.warning(msg)
                from dvadmin.notify.services import send_simple_alert
                send_simple_alert(msg)
            continue
        if not bot.is_active:
            tkey = tenant.id if tenant else 0
            if tkey not in alerted_tenants:
                alerted_tenants.add(tkey)
                msg = f"[Bot停用] 租户={getattr(tenant,'name','?')} 的Bot({bot.name})已停用, 提醒未发送"
                logger.warning(msg)
                from dvadmin.notify.services import send_simple_alert
                send_simple_alert(msg)
            continue

        # 纵深防御: 校验 bot 归属, 绝不允许跨租户串台
        if bot.tenant_id is not None and bot.tenant_id != tenant.id:
            logger.error("[串台拦截] property=%s bot=%s(归属租户%s) 与房源租户%s不一致, 拒绝发送",
                         prop.id, bot.name, bot.tenant_id, tenant.id)
            continue

        # 1. 付租提醒
        if pay_hit:
            if _dedup_enabled() and _already_sent_today(prop, "rent", now):
                logger.info("当日防重(开关开): 房源#%s 今日已发过 rent, 跳过", prop.id)
            else:
                message = build_rent_message(prop)
                ok = push_to_group(bot, prop.group_id, message, tenant=tenant, prop=prop,
                                   msg_type="rent", group_size=group_size)
                if ok:
                    sent += 1

        # 2. 到期提醒(30天/15天前); 与付租提醒同一天可并发(各自防重)
        if maturity_hit:
            if _dedup_enabled() and _already_sent_today(prop, "maturity", now):
                logger.info("当日防重(开关开): 房源#%s 今日已发过 maturity, 跳过", prop.id)
            else:
                message = build_maturity_message(prop, prop.rent_end)
                ok = push_to_group(bot, prop.group_id, message, tenant=tenant, prop=prop,
                                   msg_type="maturity", group_size=group_size)
                if ok:
                    sent += 1

        # 3. 自定义规则(水电/自定义); 每条规则独立防重(按 rule_id, 仅开关开启时)
        for rule in prop_rules:
            if not _rule_hit(now, prop, rule):
                continue
            rtype = rule.type if rule.type in ("utility", "custom") else "custom"
            if _dedup_enabled() and _already_sent_today(prop, rtype, now, rule_id=rule.id):
                logger.info("当日防重(开关开): 房源#%s 规则#%s(%s) 今日已发送, 跳过", prop.id, rule.id, rtype)
                continue
            message = build_rule_message(prop, rule)
            ok = push_to_group(bot, prop.group_id, message, tenant=tenant, prop=prop,
                               msg_type=rtype, group_size=group_size, rule_id=str(rule.id))
            if ok:
                sent += 1

    return sent


@shared_task
def daily_notify_task(tenant_ids=None, target_date=None):
    """每日提醒定时任务"""
    return scan_and_notify(tenant_ids=tenant_ids, target_date=target_date)


@shared_task
def auto_deactivate_expired_tenants():
    """
    每日扫描: 试用/正式租户到期(expire_time<now 且 is_active=True)自动停用, 并告警
    避免到期客户仍占用 bot 配额
    """
    from django.utils import timezone
    from dvadmin.notify.services import send_simple_alert
    from dvadmin.tenant.models import Tenant

    now = timezone.now()
    expired = Tenant.objects.filter(is_active=True, expire_time__isnull=False, expire_time__lt=now)
    count = 0
    for t in expired:
        t.is_active = False
        t.save(update_fields=["is_active"])
        count += 1
        msg = f"[到期停用] 租户={t.name}({t.tenant_code}) 已过服务到期时间 {t.expire_time}, 已自动停用"
        logger.warning(msg)
        send_simple_alert(msg)
    return count


@shared_task
def broadcast_task(task_id):
    """
    群发任务: 向租户名下所有带 group_id 的房源群发送自定义消息
    - 逐群 push_to_group(自带 bot 归属校验/配额检查/MessageLog 记录)
    - 每发完一个群更新 BroadcastTask 进度, 前端轮询
    - 失败不中断: 单群失败计入 failed, 全部完成后标记 done
    """
    from dvadmin.notify.models import BroadcastTask, get_bot_for_property
    from dvadmin.notify.services import push_to_group
    from dvadmin.property.models import Property

    task = BroadcastTask.objects.filter(pk=task_id).first()
    if task is None:
        return "task not found"
    if task.status == "done":
        return "already done"

    task.status = "running"
    task.save(update_fields=["status"])

    props = (Property.objects.filter(tenant=task.tenant, group_id__isnull=False)
             .exclude(group_id="")
             .select_related("line_bot", "tenant"))
    if task.property_ids is not None:
        props = props.filter(id__in=task.property_ids)
    sent = failed = skipped = 0
    for p in props:
        bot = get_bot_for_property(p)
        if bot is None or not bot.is_active:
            skipped += 1
            task.skipped = skipped
            task.save(update_fields=["skipped"])
            continue
        ok = push_to_group(bot, p.group_id, task.message, tenant=task.tenant, prop=p,
                           msg_type="broadcast", group_size=p.group_size or 1,
                           with_sticker=False, timeout=8, retries=1)
        if ok:
            sent += 1
        else:
            failed += 1
        task.sent = sent
        task.failed = failed
        task.save(update_fields=["sent", "failed"])

    task.sent = sent
    task.failed = failed
    task.skipped = skipped
    task.status = "done"
    task.save(update_fields=["sent", "failed", "skipped", "status"])
    return {"sent": sent, "failed": failed, "skipped": skipped}
