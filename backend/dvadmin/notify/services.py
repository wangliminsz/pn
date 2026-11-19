# -*- coding: utf-8 -*-
"""
LINE Push 服务
- 每个 Bot 有自己的 channel_access_token, 各自独立配额
- 一条 push 请求内可含多个 Message Object(如文字+贴纸), 计费按「接收人数×次数」, 故合并为1次
- 发送前检查配额, 超额则不发送并告警
- 大陆访问 LINE 被墙, 通过 LINE_API_PROXY(socks5h) 代理
"""
import logging
import random
import time

import requests
from django.conf import settings
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from dvadmin.notify.models import MessageLog

logger = logging.getLogger(__name__)


# 贴纸: Package 2 / sticker 41 或 45
STICKER_PACKAGE_ID = "2"
STICKER_ID = "41"
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
LINE_INFO_URL = "https://api.line.me/v2/bot/info"
RETRY_TIMES = 3  # 消息推送重试次数(后台任务默认; 手动触发可传 retries=1)


def _proxies():
    """返回代理配置(None 则不走代理)"""
    proxy = getattr(settings, "LINE_API_PROXY", None)
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def _headers(line_bot):
    return {
        "Authorization": f"Bearer {line_bot.channel_access_token}",
        "Content-Type": "application/json",
    }


# LINE 群成员接口(标准方案才可用; 免费版 403)。拿不到时用缺省缺省5人
DEFAULT_GROUP_SIZE = 5


# ==================== DeepL ==================== #
DEEPL_USAGE_URL = "https://api-free.deepl.com/v2/usage"
DEEPL_API_URL = "https://api-free.deepl.com/v2/translate"


def _deepl_auth(api_key):
    """拼接 DeepL Auth Header; 兼容 key 是否带 :fx 后缀"""
    if api_key.endswith(":fx"):
        return f"DeepL-Auth-Key {api_key}"
    return f"DeepL-Auth-Key {api_key}:fx"


def get_deepl_usage(api_key):
    """
    从 DeepL 读取该 Key 的真实额度:
    返回 dict {character_count, character_limit} 或 None(失败)
    """
    if not api_key:
        return None
    try:
        resp = requests.get(
            DEEPL_USAGE_URL,
            headers={"Authorization": _deepl_auth(api_key)},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "character_count": data.get("character_count"),
                "character_limit": data.get("character_limit"),
            }
        return {"error": resp.json().get("message", resp.text[:200]), "status_code": resp.status_code}
    except Exception as e:
        logger.warning("读取DeepL usage失败: %s", e)
        return None



def resolve_group_size(line_bot, group_id, specified=0):
    """
    解析群人数(用于计费=接收人数):
    - specified > 0: 用指定的(前端/用户已填)
    - specified <= 0: 调 LINE /members/ids 统计去重成员; 拿不到(403/网络)回退 DEFAULT_GROUP_SIZE
    返回 (count, source) source: manual/api/fallback
    """
    if specified and specified > 0:
        return specified, "manual"
    if not group_id:
        return DEFAULT_GROUP_SIZE, "fallback"
    try:
        resp = requests.get(
            f"https://api.line.me/v2/bot/group/{group_id}/members/ids",
            headers=_headers(line_bot),
            proxies=_proxies(),
            timeout=15,
        )
        if resp.status_code == 200:
            ids = resp.json().get("memberIds", [])
            if ids:
                return len(ids), "api"
    except Exception as e:
        logger.warning("群成员API获取失败, 回退缺省: %s", e)
    return DEFAULT_GROUP_SIZE, "fallback"


GROUP_NAME_CACHE_TTL = 60 * 60 * 24  # 群名称缓存 1 天


def get_cached_group_name(line_bot, group_id):
    """只读群名称缓存(永不调 LINE API): 命中返回名称, 未命中返回 None
    工作台等列表页用此函数, 页面加载绝不打 LINE; 精确刷新走 get_group_name(force=True)"""
    if not line_bot or not group_id:
        return None
    cache_key = f"line_group_name:{line_bot.id}:{group_id}"
    try:
        from django.core.cache import cache
        cached = cache.get(cache_key)
        return cached or None
    except Exception:
        return None


def get_group_name(line_bot, group_id, force=False):
    """
    尝试从 LINE 读取群名称(用于工作台展示):
    - 调 GET /v2/bot/group/{groupId}/summary -> {groupName}
    - 免费/未审核 bot 无权限(403), 网络失败等都返回 None(前端降级不显示)
    - 结果按 bot+group 缓存 1 天, 减少对外请求
    返回 (name, error):
      name: 群名或 None
      error: None | "network"(LINE 不可达/超时) | "denied"(LINE 可达但无权限/异常状态码)
    """
    if not line_bot or not group_id:
        return None, None
    cache_key = f"line_group_name:{line_bot.id}:{group_id}"
    if not force:
        try:
            from django.core.cache import cache
            cached = cache.get(cache_key)
            if cached:
                return cached or None, None
        except Exception:
            pass
    name = None
    error = None
    try:
        resp = requests.get(
            f"https://api.line.me/v2/bot/group/{group_id}/summary",
            headers=_headers(line_bot),
            proxies=_proxies(),
            timeout=5,
        )
        if resp.status_code == 200:
            name = (resp.json().get("groupName") or "").strip() or None
        else:
            error = "denied"
            logger.info("群名称API不可用 bot=%s group=%s status=%s", line_bot, group_id, resp.status_code)
    except Exception as e:
        error = "network"
        logger.warning("群名称API获取失败(网络) bot=%s group=%s: %s", line_bot, group_id, e)
    try:
        from django.core.cache import cache
        cache.set(cache_key, name or "", timeout=GROUP_NAME_CACHE_TTL)
    except Exception:
        pass
    return name, error


def get_current_month_usage(line_bot):
    """统计某 bot 当月已消耗的计费条数"""
    now = timezone.now()
    return (
        MessageLog.objects.filter(
            line_bot=line_bot,
            create_datetime__year=now.year,
            create_datetime__month=now.month,
            result="success",
        ).aggregate(total=Sum("count"))["total"]
        or 0
    )


LINE_QUOTA_CACHE_TTL = 5 * 60  # 配额缓存 5 分钟


def _quota_cache_key(line_bot):
    return f"line_quota:{line_bot.id}"


def get_cached_line_quota(line_bot):
    """只读配额缓存(不触发 LINE API): 返回 (limit, used) 或 (None, None)(未命中)"""
    if not line_bot:
        return None, None
    try:
        from django.core.cache import cache
        cached = cache.get(_quota_cache_key(line_bot))
        if cached:
            return cached
    except Exception:
        pass
    return None, None


def get_line_quota(line_bot, force=False):
    """
    从 LINE 读取该 bot 的真实配额(免费版也可用):
    (limit, used) 元组; 失败返回 (None, None)
    - /v2/bot/message/quota -> {type, value}  本月配额上限
    - /v2/bot/message/quota/consumption -> {totalUsage} 本月已用
    结果按 bot 缓存 LINE_QUOTA_CACHE_TTL(成功才缓存; 失败不缓存以便下次重试)
    force=True 时跳过缓存强制请求 LINE(刷新用), 并刷新缓存
    """
    if not line_bot:
        return None, None
    if not force:
        cached = get_cached_line_quota(line_bot)
        if cached[0] is not None and cached[1] is not None:
            return cached

    try:
        resp = requests.get(
            "https://api.line.me/v2/bot/message/quota",
            headers=_headers(line_bot),
            proxies=_proxies(),
            timeout=5,
        )
        if resp.status_code != 200:
            return None, None
        limit = resp.json().get("value")
    except Exception as e:
        logger.warning("读取配额上限失败 bot=%s: %s", line_bot, e)
        return None, None

    used = None
    try:
        resp = requests.get(
            "https://api.line.me/v2/bot/message/quota/consumption",
            headers=_headers(line_bot),
            proxies=_proxies(),
            timeout=5,
        )
        if resp.status_code == 200:
            used = resp.json().get("totalUsage")
    except Exception as e:
        logger.warning("读取配额用量失败 bot=%s: %s", line_bot, e)

    result = (limit, used)
    if limit is not None and used is not None:
        try:
            from django.core.cache import cache
            cache.set(_quota_cache_key(line_bot), result, timeout=LINE_QUOTA_CACHE_TTL)
        except Exception:
            pass
    return result


def _bot_quota(line_bot, tenant):
    """bot(物理Channel) 月度上限, 用于与 LINE 真实500/10000 对齐
    优先取 bot 自身配置的 monthly_quota(可填付费档如10000), 留空则回退全局 BOT_MSG_LIMIT
    """
    quota = getattr(line_bot, "monthly_quota", None)
    if quota:
        return quota
    return getattr(settings, "BOT_MSG_LIMIT", 500)


def _trial_active(tenant):
    """
    租户可用性检查:
    - 未启用 -> 不可
    - 试用/正式 且未过期 -> 可
    """
    if tenant is None:
        return True
    if not getattr(tenant, "is_active", True):
        return False
    expire_time = getattr(tenant, "expire_time", None)
    if expire_time and expire_time < timezone.now():
        return False
    return True


def _check_quota(line_bot, tenant, count=1):
    """
    配额检查(仅 bot 级, 与 LINE 真实额度对齐; 租户不再有软配额):
    返回 dict: {ok, level, used, limit, reason}
    """
    b_limit = _bot_quota(line_bot, tenant)
    b_used = get_current_month_usage(line_bot)
    if b_used + count <= b_limit:
        return {"ok": True, "level": "bot", "used": b_used, "limit": b_limit, "reason": ""}
    return {"ok": False, "level": "bot", "used": b_used, "limit": b_limit, "reason": "bot_quota_exceeded"}


def _check_quota_alert(line_bot, tenant):
    """配额接近上限告警(bot 级): 返回 dict 或 None"""
    threshold = getattr(settings, "MSG_ALERT_RATIO", 0.9)
    limit = _bot_quota(line_bot, tenant)
    used = get_current_month_usage(line_bot)
    check = {"level": "bot", "used": used, "limit": limit}
    if check.get("limit") and check["used"] >= check["limit"] * threshold:
        return {**check, "hit": True}
    return {**check, "hit": False}


def send_quota_alert(line_bot, tenant, used, limit):
    """发送配额告警(预留: 飞书/webhook)"""
    alert_url = getattr(settings, "MSG_ALERT_WEBHOOK_URL", None)
    message = f"[配额告警] Bot={line_bot.name} 租户={getattr(tenant,'name','')} 本月已用 {used}/{limit}"
    logger.warning(message)
    if alert_url:
        try:
            import requests
            requests.post(alert_url, json={"text": message}, timeout=10)
        except Exception as e:
            logger.warning("告警发送失败: %s", e)


def send_simple_alert(message):
    """通用告警(租户到期停用/异常等): 写日志 + 发 webhook"""
    logger.warning(message)
    alert_url = getattr(settings, "MSG_ALERT_WEBHOOK_URL", None)
    if alert_url:
        try:
            import requests
            requests.post(alert_url, json={"text": message}, timeout=10)
        except Exception as e:
            logger.warning("告警发送失败: %s", e)


def _record_message(line_bot, tenant, prop, group_id, group_size, msg_type, content, result, error_msg="", count=1, rule_id=None):
    return MessageLog.objects.create(
        tenant=tenant,
        line_bot=line_bot,
        property=prop,
        group_id=group_id,
        group_size=group_size,
        msg_type=msg_type,
        rule_id=rule_id,
        content=content,
        result=result,
        error_msg=error_msg,
        count=count,
    )


def push_to_group(line_bot, group_id, message, tenant=None, prop=None, msg_type="",
                  group_size=1, with_sticker=True, sticker_package_id=STICKER_PACKAGE_ID,
                  sticker_id=STICKER_ID, timeout=15, retries=RETRY_TIMES, rule_id=None):
    """
    向指定群发送一条消息(文字+贴纸合并为一次 push, 计费1次/人)
    返回是否成功; 失败或超配额均写入 MessageLog
    timeout/retries: 网络与重试策略(后台任务可保持默认; 手动触发建议降级防前台超时)
    rule_id: 自定义提醒规则ID(用于按规则防重)
    """
    if not group_id:
        return False

    content_preview = (message or "")[:500]

    # 解析群人数(计费=接收人数): 指定值或自动(预留成员API, 缺省5)
    group_size, size_source = resolve_group_size(line_bot, group_id, group_size)
    if size_source != "manual":
        logger.info("群人数自动解析 group=%s -> %s (source=%s)", group_id, group_size, size_source)

    # 租户可用性检查(试用过期/停用)
    if not _trial_active(tenant):
        logger.warning("[TRIAL] 租户不可用, 跳过 tenant=%s", getattr(tenant, "name", None))
        _record_message(line_bot, tenant, prop, group_id, group_size, msg_type,
                        content_preview, "failed", "tenant_inactive", rule_id=rule_id)
        return False

    # 配额检查(bot 级, 与 LINE 真实额度对齐; 租户不再有软配额), 计费=接收人数, 故按 group_size 校验
    quota = _check_quota(line_bot, tenant, count=group_size or 1)
    if not quota["ok"]:
        logger.warning("[QUOTA] level=%s used=%s limit=%s 已满, 跳过推送", quota["level"], quota["used"], quota["limit"])
        _record_message(line_bot, tenant, prop, group_id, group_size, msg_type,
                        content_preview, "failed", quota["reason"], rule_id=rule_id)
        return False
    # 配额接近上限告警(租户级优先)
    alert = _check_quota_alert(line_bot, tenant)
    if alert.get("hit"):
        send_quota_alert(line_bot, tenant, alert["used"], alert["limit"])

    messages = []
    if message:
        messages.append({"type": "text", "text": message})
    if with_sticker and sticker_package_id and sticker_id:
        messages.append({"type": "sticker", "packageId": sticker_package_id, "stickerId": sticker_id})

    if not messages:
        return False

    payload = {"to": group_id, "messages": messages}

    # 轻量重试: 网络类/5xx瞬时错误重试(指数退避), 业务4xx不重试
    last_err = ""
    for attempt in range(retries):
        try:
            resp = requests.post(
                LINE_PUSH_URL,
                headers=_headers(line_bot),
                json=payload,
                proxies=_proxies(),
                timeout=timeout,
            )
            resp_json = resp.json() if resp.content else {}
            if resp.status_code == 200:
                _record_message(line_bot, tenant, prop, group_id, group_size, msg_type,
                                content_preview, "success", count=group_size or 1, rule_id=rule_id)
                time.sleep(random.randint(1, 2))
                return True
            # 5xx 瞬时错误可重试; 4xx(参数/权限等)不可重试
            if resp.status_code >= 500 and attempt < retries - 1:
                last_err = f"{resp.status_code}: {resp_json.get('message', resp.text[:200])}"
                logger.warning("推送5xx, 第%s次重试 bot=%s group=%s: %s", attempt + 1, line_bot, group_id, last_err)
                time.sleep(random.randint(1, 2) * (attempt + 1))
                continue
            msg = f"{resp.status_code}: {resp_json.get('message', resp.text[:200])}"
            logger.error("推送失败 bot=%s group=%s: %s", line_bot, group_id, msg)
            _record_message(line_bot, tenant, prop, group_id, group_size, msg_type,
                            content_preview, "failed", msg, rule_id=rule_id)
            return False
        except requests.exceptions.RequestException as e:
            last_err = str(e)
            if attempt < retries - 1:
                logger.warning("推送网络异常, 第%s次重试 bot=%s group=%s: %s", attempt + 1, line_bot, group_id, e)
                time.sleep(random.randint(1, 2) * (attempt + 1))
                continue
            logger.error("推送网络异常已达重试上限 bot=%s group=%s: %s", line_bot, group_id, e)
            _record_message(line_bot, tenant, prop, group_id, group_size, msg_type,
                            content_preview, "failed", str(e), rule_id=rule_id)
            return False
        except Exception as e:
            logger.exception("推送异常 bot=%s group=%s: %s", line_bot, group_id, e)
            _record_message(line_bot, tenant, prop, group_id, group_size, msg_type,
                            content_preview, "failed", str(e), rule_id=rule_id)
            return False

    # 重试耗尽(5xx)
    logger.error("推送5xx已达重试上限 bot=%s group=%s: %s", line_bot, group_id, last_err)
    _record_message(line_bot, tenant, prop, group_id, group_size, msg_type,
                    content_preview, "failed", last_err or "unexpected", rule_id=rule_id)
    return False
