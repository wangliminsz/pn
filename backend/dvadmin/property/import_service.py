# -*- coding: utf-8 -*-
"""
房源批量导入服务
- 可从 CSV/XLSX 或 JSON rows 导入房源(名称/负责人/租金/付租周期/提醒日/起租/结束/备注)
- 设计决策(用户明确): LineBot / Group ID 由导入后手动填写, 故模板不含这两列
- 负责人(owner) 可选: 填的是"本租户内的账号", 缺省 = 导入人自己
- 参考 org_chart 的 parse/preview/apply 三段式, 但只涉及 Property 单表, 无部门/账号创建
"""
import csv
import io
import re
from datetime import datetime, date

from django.utils.translation import gettext as _

# 付租周期别名 → 标准值
PAY_PERIOD_ALIAS = {
    "每月": "Monthly", "月付": "Monthly", "月租": "Monthly", "monthly": "Monthly", "month": "Monthly", "m": "Monthly",
    "每季度": "Quarterly", "季度": "Quarterly", "季付": "Quarterly", "quarterly": "Quarterly", "quarter": "Quarterly", "q": "Quarterly",
    "每半年": "HalfYear", "半年": "HalfYear", "半年付": "HalfYear", "halfyear": "HalfYear", "half-year": "HalfYear", "semiannual": "HalfYear", "hy": "HalfYear",
    "每年": "Yearly", "年付": "Yearly", "一年": "Yearly", "yearly": "Yearly", "year": "Yearly", "annual": "Yearly", "y": "Yearly",
}


def _norm_key(key):
    """列名归一: 去除所有非字母数字(中英文)字符, 全小写"""
    s = str(key)
    return re.sub(r"[^a-zA-Z0-9\u4e00-\u9fa5]", "", s.strip().lower())


def _get(norm, *names):
    """从归一化 dict 取第一个非空值"""
    for n in names:
        v = norm.get(_norm_key(n))
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return ""


def _normalize_row(raw):
    norm = {_norm_key(k): v for k, v in (raw or {}).items() if k is not None}

    def get(*names):
        return _get(norm, *names)

    row = {
        "name": get("房间名称", "name", "房间", "room", "roomname", "propertyname", "property", "房号"),
        "owner_raw": get("负责人", "负责人账号", "owner", "owneraccount", "username", "agent", "account", "员工账号"),
        "rent_raw": get("租金", "rent", "rentamount", "rental", "月租", "价格"),
        "pay_raw": get("付租周期", "payperiod", "周期", "period", "paymentperiod", "付租"),
        "remind_raw": get("提醒日", "remindday", "remind", "提醒号", "day"),
        "start_raw": get("起租日期", "rentstart", "startdate", "start", "起租", "begin"),
        "end_raw": get("结束日期", "rentend", "enddate", "end", "结束", "到期", "到期日"),
        "memo": get("备注", "memo", "remark", "note", "notes"),
        "line_bot_raw": get("linebot", "line_bot", "linebotname", "bot", "botname"),
        "group_id": get("groupid", "group_id", "群id", "群"),
    }
    row["errors"] = []

    # ---- 名称(必填) ----
    if not row["name"]:
        row["errors"].append(_("Room name is required"))

    # ---- 租金(可选, 数值) ----
    rent = 0
    if row["rent_raw"]:
        num = re.sub(r"[^0-9.\-]", "", row["rent_raw"])
        try:
            rent = float(num)
            if rent < 0:
                row["errors"].append(_("Rent cannot be negative"))
        except ValueError:
            row["errors"].append(_("Rent not recognized: {}").format(row["rent_raw"]))
    row["rent_amount"] = rent

    # ---- 付租周期 ----
    pay = row["pay_raw"]
    row["pay_period"] = "Monthly"
    if pay:
        norm_pay = re.sub(r"[\s\-_]", "", pay.strip().lower())
        alias = PAY_PERIOD_ALIAS.get(pay.strip().lower()) or PAY_PERIOD_ALIAS.get(norm_pay)
        if alias:
            row["pay_period"] = alias
        else:
            row["errors"].append(_("Payment period not recognized: {}").format(pay))

    # ---- 提醒日(默认 1) ----
    remind = row["remind_raw"]
    row["remind_day"] = 1
    if remind:
        try:
            d = int(re.sub(r"[^0-9]", "", remind) or 1)
            if 1 <= d <= 31:
                row["remind_day"] = d
            else:
                row["errors"].append(_("Reminder day must be 1-31"))
        except ValueError:
            row["errors"].append(_("Reminder day not recognized: {}").format(remind))

    # ---- 起租/结束日期(可空, 但建议填) ----
    row["rent_start"] = _parse_date(row["start_raw"])
    row["rent_end"] = _parse_date(row["end_raw"])
    if row["start_raw"] and not row["rent_start"]:
        row["errors"].append(_("Rent start date not recognized: {}").format(row["start_raw"]))
    if row["end_raw"] and not row["rent_end"]:
        row["errors"].append(_("Rent end date not recognized: {}").format(row["end_raw"]))
    if row["rent_start"] and row["rent_end"] and row["rent_start"] > row["rent_end"]:
        row["errors"].append(_("Rent start date cannot be later than rent end date"))

    # ---- 负责人账号(可选) ----
    row["owner_username"] = row["owner_raw"] or ""
    if row["owner_username"] and not re.fullmatch(r"[A-Za-z0-9@\._\-+]+", row["owner_username"]):
        row["errors"].append(_("Owner account contains invalid characters"))

    return row


def _parse_date(value):
    """把 日期单元格/字符串 归一到 YYYY-MM-DD(或 None)。
    支持 Excel datetime/date、'YYYY-MM-DD'、'YYYY/M/D'、'M/D/YYYY'、'YYYYMMDD'、带时间戳"""
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, (datetime, date)):
        return value.date().isoformat()
    s = str(value).strip().replace("/", "-")
    # 去掉时间部分
    s = s.split(" ")[0].split("T")[0]
    for fmt in ("%Y-%m-%d", "%m-%d-%Y", "%Y%m%d", "%Y-%m"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_inline_rows(rows):
    return [_normalize_row(r) for r in rows]


def parse_file(file_obj):
    """解析上传文件(CSV/XLSX)为标准行"""
    filename = (getattr(file_obj, "name", "") or "").lower()
    raw_rows = []
    data = file_obj.read()
    if filename.endswith((".xls", ".xlsx")):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
        ws = wb.active
        values_rows = ws.iter_rows(values_only=True)
        header = None
        for idx, values in enumerate(values_rows):
            if values is None or all(v is None or str(v).strip() == "" for v in values):
                continue
            if idx == 0:
                header = [str(v).strip() if v is not None else "" for v in values]
                continue
            raw_rows.append(dict(zip(header, values)))
    else:
        text = data.decode("utf-8-sig", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        header = None
        for idx, values in enumerate(reader):
            if not values or all(str(v).strip() == "" for v in values):
                continue
            if idx == 0:
                header = [v.strip() for v in values]
                continue
            raw_rows.append(dict(zip(header, values)))
    return [_normalize_row(r) for r in raw_rows]


def _resolve_owners(request, rows):
    """解析负责人账号 → Users 实例(本租户内)。返回 (usr_map, warn)
    usr_map: {username: Users}; warn: 无法解析的账号列表(跳该行)"""
    from dvadmin.system.models import Users
    tenant = request.user.tenant
    usr_map = {}
    usernames = {r["owner_username"] for r in rows if r["owner_username"] and not r["errors"]}
    if usernames:
        qs = Users.objects.filter(username__in=usernames)
        if tenant is not None:
            qs = qs.filter(tenant=tenant)
        for u in qs:
            usr_map[u.username] = u
    return usr_map


def preview(request, rows):
    """dry_run: 校验 + 统计(姓名重复/既有同名警告), 不落库"""
    import copy
    rows = [copy.deepcopy(r) for r in rows]

    # 文件内同名去重(首行优先)
    seen = {}
    dup_count = 0
    for r in rows:
        nm = r["name"]
        if not nm or r["errors"]:
            continue
        key = nm.strip().lower()
        if key in seen:
            r["dup_status"] = "duplicate"
            dup_count += 1
        else:
            seen[key] = r
            r["dup_status"] = None

    errors = [{"row": i + 1, "msg": r["errors"]} for i, r in enumerate(rows) if r["errors"]]

    usr_map = _resolve_owners(request, rows)
    # 解析 LineBot(与 apply 一致: 按 bot_code 或 name 在本租户/平台默认内匹配)
    from django.db.models import Q
    bot_map = {}
    bot_values = {r["line_bot_raw"].strip() for r in rows if r.get("line_bot_raw") and not r["errors"]}
    if bot_values:
        from dvadmin.notify.models import LineBot
        tenant = request.user.tenant
        qs = LineBot.objects.filter(is_active=True)
        if tenant is not None:
            qs = qs.filter(tenant=tenant)
        qs = qs.filter(Q(bot_code__in=bot_values) | Q(name__in=bot_values))
        for b in qs:
            bot_map[b.bot_code] = b
            bot_map[b.name] = b
    for i, r in enumerate(rows):
        if r.get("dup_status") or r["errors"]:
            continue
        if r["owner_username"] and r["owner_username"] not in usr_map:
            errors.append({"row": i + 1, "msg": _("Owner account not found in this tenant: {}").format(r['owner_username'])})
            r["errors"] = r["errors"] + [_("Owner account not found in this tenant: {}").format(r['owner_username'])]
        if r.get("line_bot_raw") and r["line_bot_raw"].strip() not in bot_map:
            errors.append({"row": i + 1, "msg": _("Line Bot not found in this tenant: {}").format(r['line_bot_raw'].strip())})
            r["errors"] = r["errors"] + [_("Line Bot not found in this tenant: {}").format(r['line_bot_raw'].strip())]

    existing_names = set()
    if rows:
        from dvadmin.property.models import Property
        names = {r["name"].strip() for r in rows if r["name"] and not r["errors"]}
        tenant = request.user.tenant
        qs = Property.objects.filter(name__in=names) if names else Property.objects.none()
        if tenant is not None:
            qs = qs.filter(tenant=tenant)
        existing_names = set(qs.values_list("name", flat=True))

    valid = [
        r for r in rows
        if not r["errors"] and not r.get("dup_status")
        and (not r["owner_username"] or r["owner_username"] in usr_map)
    ]
    stats = {
        "valid_rows": len(valid),
        "duplicate_rows": dup_count,
        "invalid_rows": len([e for e in errors if e["row"] is not None]),
        "existing_warn": sorted(existing_names),
    }
    return {"rows": rows, "stats": stats, "errors": errors}


def apply(request, rows):
    """正式导入: 批量创建 Property(跳过错误/重复行; 既有同名仍新建但计入警告)
    支持: 负责人 / LineBot(填 bot_code 或 name) / Group ID"""
    from dvadmin.property.models import Property
    from dvadmin.notify.models import LineBot

    usr_map = _resolve_owners(request, rows)
    # 解析 LineBot: 按 bot_code 或 name 在本租户(及平台默认)内匹配
    bot_map = {}
    bot_values = {r["line_bot_raw"].strip() for r in rows if r.get("line_bot_raw") and not r["errors"]}
    if bot_values:
        tenant = request.user.tenant
        qs = LineBot.objects.filter(is_active=True)
        if tenant is not None:
            qs = qs.filter(tenant=tenant)
        for b in qs.filter(bot_code__in=bot_values) | qs.filter(name__in=bot_values):
            bot_map[b.bot_code] = b
            bot_map[b.name] = b
    seen = set()
    created = 0
    duplicates = 0
    invalid = 0
    existing_warn = set()
    tenant = request.user.tenant

    existing_qs = Property.objects.all()
    if tenant is not None:
        existing_qs = existing_qs.filter(tenant=tenant)

    for i, r in enumerate(rows):
        if r["errors"]:
            invalid += 1
            continue
        key = r["name"].strip().lower()
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        owner = usr_map.get(r["owner_username"]) if r["owner_username"] else None
        if r["owner_username"] and owner is None:
            invalid += 1  # 负责人不存在(预览应已拦截)
            continue
        bot = None
        if r.get("line_bot_raw"):
            bot_key = r["line_bot_raw"].strip()
            bot = bot_map.get(bot_key)
            if bot is None:
                invalid += 1
                continue
        if existing_qs.filter(name=r["name"].strip()).exists():
            existing_warn.add(r["name"].strip())
        Property.objects.create(
            tenant=tenant if tenant else None,
            creator=request.user,
            owner=owner or request.user,
            name=r["name"].strip(),
            rent_amount=r["rent_amount"] or None,
            remind_day=r["remind_day"],
            pay_period=r["pay_period"],
            rent_start=r["rent_start"],
            rent_end=r["rent_end"],
            memo=(r["memo"] or None),
            line_bot=bot,
            group_id=(r.get("group_id") or "").strip() or None,
        )
        created += 1

    return {
        "created": created,
        "duplicates": duplicates,
        "invalid": invalid,
        "existing_warn": sorted(existing_warn),
    }