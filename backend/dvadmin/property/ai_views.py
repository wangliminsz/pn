# -*- coding: utf-8 -*-
"""
AI 助手(房源): 一句话 -> 预览确认卡(形态 A, 单轮)
- 配置(Model/Key/Base)存 SystemConfig, 前端可随时切换(超管)
- 解析接口: 调 LLM 把口语整理成房源 JSON 草稿 -> 业务校验 -> 返回前端预览
"""
import json
import logging
import time

import requests
from django.utils.translation import gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from dvadmin.system.models import SystemConfig
from dvadmin.utils.json_response import ErrorResponse, SuccessResponse
from dvadmin.utils.permission import SuperuserPermission

logger = logging.getLogger("dvadmin.property.ai")

# 默认模型配置(可由 SystemConfig 覆盖; api_key 不写死在代码里, 首次使用写入数据库)
DEFAULT_AI_BASE = "https://token.sensenova.cn/v1"
DEFAULT_AI_MODEL = "deepseek-v4-flash"

CFG_KEYS = ("ai_base", "ai_model", "ai_api_key")


def _get_ai_config():
    """读取运行时 AI 配置(缺省用默认 base/model, api_key 必须数据库里有)"""
    row_base = SystemConfig.objects.filter(key="ai_base").first()
    row_model = SystemConfig.objects.filter(key="ai_model").first()
    row_key = SystemConfig.objects.filter(key="ai_api_key").first()
    base = row_base.value if (row_base and row_base.value) else DEFAULT_AI_BASE
    model = row_model.value if (row_model and row_model.value) else DEFAULT_AI_MODEL
    key = row_key.value if (row_key and row_key.value) else ""
    return {"base": str(base).rstrip("/"), "model": str(model), "api_key": str(key)}


def _mask_key(key):
    if not key:
        return ""
    return key[:4] + "*" * 8 + key[-4:] if len(key) > 10 else "****"


class AIConfigView(APIView):
    """
    全局 AI 配置(仅超管)
    - GET:  返回 {base, model, api_key(脱敏), has_key}
    - PUT:  {base?, model?, api_key?} 写入 SystemConfig; api_key 为空则保留原值
    """

    permission_classes = [SuperuserPermission]

    def get(self, request):
        cfg = _get_ai_config()
        return SuccessResponse(data={
            "base": cfg["base"],
            "model": cfg["model"],
            "api_key": _mask_key(cfg["api_key"]),
            "has_key": bool(cfg["api_key"]),
        })

    def put(self, request):
        base = (request.data.get("base") or "").strip()
        model = (request.data.get("model") or "").strip()
        api_key = (request.data.get("api_key") or "").strip()
        if base:
            SystemConfig.objects.update_or_create(key="ai_base", defaults={"value": base})
        if model:
            SystemConfig.objects.update_or_create(key="ai_model", defaults={"value": model})
        # 前端传 masked 值时不覆盖; 传真实新 key 才更新
        if api_key and "*" not in api_key:
            SystemConfig.objects.update_or_create(key="ai_api_key", defaults={"value": api_key})
        cfg = _get_ai_config()
        return SuccessResponse(data={
            "base": cfg["base"],
            "model": cfg["model"],
            "api_key": _mask_key(cfg["api_key"]),
            "has_key": bool(cfg["api_key"]),
        }, msg=_("AI config saved"))


PROMPT_TEMPLATE = """你是一个房源录入助手。用户会用一两句话描述想添加的租房房源(可能中英泰混合)。
请把以下信息整理成 JSON, 只返回 JSON, 不要任何解释/markdown。

重要参考: 今天是 {today}(Asia/Bangkok 泰国日期)。用户说的「今年/明年/本月/下月/今天」等相对词, 一律按今天推算成准确日期。

字段(JSON key 固定):
- name: 房间名(尽量填写; 没提到就用空字符串)
- rent_amount: 月租金数字(数字, 没提到给 null)
- pay_period: "Monthly"|"Quarterly"|"HalfYear"|"Yearly", 默认 "Monthly"(月付/每季度/半年/每年)
- remind_day: 提醒日(1-31 数字, 没提到给 null)
- rent_start: "YYYY-MM-DD" 起租日(没提到给 null)
- rent_end:   "YYYY-MM-DD" 结束日(没提到给 null)
- owner_username: 负责人登录名/姓名(用户可能说"负责人张三"。没提到给 null)
- line_bot_name: 用户提到的 LINE 群发机器人名称(如 "proNotify"。没提到给 null)
- group_id: 用户提到的 LINE 群 ID(C 开头的一串, 如 C59721...。没提到给 null)
- memo: 备注(如押金/包含费用等, 没提到给空字符串)

规则:
- 若用户没有给明确值, 对应字段给 null 或空字符串, 不要编造。
- rent_amount 保持纯数字, 不要单位(如 6500 而不是 6500泰铢/6500฿)。
- 日期尽量按用户提供的解析为标准 YYYY-MM-DD, 相对词(今年/明年)按上面的今天推算。

用户输入: {text}
输出 JSON:"""


def _bangkok_today():
    """Asia/Bangkok 今天日期字符串, 供 LLM 推算"今年/明年"等相对词"""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Asia/Bangkok")).strftime("%Y-%m-%d")


class AIAssistView(APIView):
    """房源 AI 助手: 一句话 -> 结构化草稿(单轮, 不落库, 前端确认后再走正常创建)"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        text = (request.data.get("text") or "").strip()
        if not text:
            return ErrorResponse(msg=_("Please enter the property description to add"))

        cfg = _get_ai_config()
        if not cfg.get("api_key"):
            return ErrorResponse(msg=_("AI API Key is not configured"))

        try:
            today = _bangkok_today()
            payload = {
                "model": cfg["model"],
                "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(text=text, today=today)}],
                "temperature": 0.1,
                "max_tokens": 600,
            }
            # 公测免费模型可能偶发过载/限流(429/529/5xx): 短退避重试最多3次
            resp = None
            last_err = ""
            for attempt in range(3):
                resp = requests.post(
                    cfg["base"] + "/chat/completions",
                    headers={"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=120,
                )
                if resp.status_code in (200, 400, 401, 403, 404, 422):
                    break
                # 429 / 529 / 5xx: 退避重试
                last_err = f"{resp.status_code}: {resp.text[:200]}"
                logger.warning("AI 调用第%s次返回 %s, 重试中", attempt + 1, last_err)
                time.sleep(3 * (attempt + 1))
            if resp is None or resp.status_code != 200:
                logger.error("AI 调用失败: %s", last_err or (resp.status_code if resp is not None else "-"))
                reason = _("service rate-limited/overloaded") if (resp and resp.status_code in (429, 529)) else _("service error")
                return ErrorResponse(msg=_("AI {}, please retry later").format(reason))
            content = resp.json()["choices"][0]["message"]["content"]
            draft = self._extract_json(content)
        except requests.exceptions.RequestException as e:
            logger.warning("AI 调用网络异常: %s", e)
            return ErrorResponse(msg=_("Cannot connect to the AI service (network/proxy issue), please retry later"))
        except Exception as e:
            logger.exception("AI 解析异常: %s", e)
            return ErrorResponse(msg=_("AI parsing failed: {}").format(e))

        # 业务校验补全(bot/员工均限当前租户, 防止串数据)
        try:
            ctx = self._build_ctx(request)
        except Exception as e:
            logger.exception("构建 AI 匹配上下文失败: %s", e)
            ctx = {}
        return SuccessResponse(data={"draft": self._validate(draft, ctx)})

    @staticmethod
    def _build_ctx(request):
        """预构建「本租户 bots + 激活员工」查找表, 供 _validate 匹配负责人/LineBot"""
        from dvadmin.notify.models import get_tenant_bots
        from dvadmin.system.models import Users

        bots_by_name = {}
        for b in get_tenant_bots(request.user.tenant):
            key = (b.name or "").strip().lower()
            if key:
                bots_by_name.setdefault(key, b)
        users_by_username, users_by_name = {}, {}
        for u in Users.objects.filter(tenant=request.user.tenant, is_active=True):
            if (u.username or "").strip():
                users_by_username.setdefault(u.username.strip().lower(), u)
            if (u.name or "").strip():
                users_by_name.setdefault(u.name.strip().lower(), u)
        return {
            "bots_by_name": bots_by_name,
            "users_by_username": users_by_username,
            "users_by_name": users_by_name,
            "default_owner_id": request.user.id,
        }

    @staticmethod
    def _validate(draft, ctx=None):
        """把 AI 草稿规整成前端可直接展示+提交的房源字段; 标出缺项
        ctx 可选, 提供后额外解析负责人/LineBot/群ID(均限本租户)
        """
        from datetime import datetime

        out = {
            "name": draft.get("name") or "",
            "rent_amount": draft.get("rent_amount"),
            "pay_period": draft.get("pay_period") if draft.get("pay_period") in ("Monthly", "Quarterly", "HalfYear", "Yearly") else "Monthly",
            "remind_day": draft.get("remind_day"),
            "rent_start": draft.get("rent_start"),
            "rent_end": draft.get("rent_end"),
            "owner_username": draft.get("owner_username"),
            "owner_id": None,
            "owner_warn": "",
            "line_bot_name": draft.get("line_bot_name") or "",
            "line_bot_id": None,
            "bot_warn": "",
            "group_id": (draft.get("group_id") or "").strip(),
            "group_warn": "",
            "memo": draft.get("memo") or "",
        }
        # 数字规整
        for k in ("rent_amount", "remind_day"):
            v = out[k]
            if isinstance(v, str):
                try:
                    out[k] = int(float(v))
                except (TypeError, ValueError):
                    out[k] = None
        if out["rent_amount"] is not None and isinstance(out["rent_amount"], (int, float)):
            out["rent_amount"] = float(out["rent_amount"])

        # 日期规整
        for k in ("rent_start", "rent_end"):
            v = out[k]
            if isinstance(v, str):
                v = v.strip()
                for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
                    try:
                        out[k] = datetime.strptime(v, fmt).strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue
                else:
                    out[k] = None

        # 缺项提示(租金非必填, 不出警告; 提醒日未提给默认1, 也不警告)
        missing = []
        if not out["name"]:
            missing.append(_("Room name"))
        if not out["rent_start"]:
            missing.append(_("Rent start date"))
        if not out["rent_end"]:
            missing.append(_("Rent end date"))
        if out["rent_amount"] is None:
            out["rent_amount"] = None
        elif isinstance(out["rent_amount"], (int, float)) and out["rent_amount"] < 0:
            out["rent_amount"] = None
        if out["remind_day"] is None:
            # 缺省: 取起租日的日(如起租 2026-09-06 -> 提醒日 6)
            if out["rent_start"]:
                try:
                    out["remind_day"] = datetime.strptime(out["rent_start"], "%Y-%m-%d").day
                except (TypeError, ValueError):
                    out["remind_day"] = 1
            else:
                out["remind_day"] = 1
        if out["rent_start"] and out["rent_end"] and out["rent_start"] >= out["rent_end"]:
            out["date_warn"] = _("Rent start date must be earlier than rent end date")
        else:
            out["date_warn"] = ""
        if ctx is None:
            ctx = {}

        # 负责人: 本租户激活员工按 username/姓名匹配; 没提到 → 缺省=当前用户; 匹配不到 → 留空+提示
        owner_username = (out.get("owner_username") or "").strip()
        owner_obj = None
        if owner_username:
            lower = owner_username.lower()
            owner_obj = (ctx.get("users_by_username") or {}).get(lower) or (ctx.get("users_by_name") or {}).get(lower)
            if owner_obj is None:
                out["owner_warn"] = "not_found"
        elif ctx.get("default_owner_id"):
            out["owner_id"] = ctx["default_owner_id"]
        if owner_obj is not None:
            out["owner_id"] = owner_obj.id

        # LineBot: 本租户 bots 按名称匹配(小写); 匹配不到 → 留空+提示
        bot_name = (out.get("line_bot_name") or "").strip()
        bot_obj = None
        if bot_name:
            bot_obj = (ctx.get("bots_by_name") or {}).get(bot_name.lower())
            if bot_obj is None:
                out["bot_warn"] = "not_found"
        if bot_obj is not None:
            out["line_bot_id"] = bot_obj.id

        # 群 ID: 软提示(LINE 群 ID 一般以 C 开头, 防 AI 幻觉乱码)
        gid = out.get("group_id") or ""
        if gid and not gid.lower().startswith("c"):
            out["group_warn"] = "bad_format"
        return {**out, "missing": missing}

    @staticmethod
    def _extract_json(content):
        """从 LLM 回复里提取 JSON(兼容代码块包装)"""
        c = content.strip()
        if c.startswith("```"):
            c = c.split("\n", 1)[-1]
            if c.endswith("```"):
                c = c[:-3]
            c = c.strip()
        start, end = c.find("{"), c.rfind("}")
        return json.loads(c[start:end + 1])