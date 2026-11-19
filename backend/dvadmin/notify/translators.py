# -*- coding: utf-8 -*-
"""
翻译服务: 多 Provider 顺序降级
- 百度(主): 国内直连免代理, 月配额高
- googleCloud: 走代理, 冗余
- deepTranslator(网页版): 最后兜底(易 429)
按顺序依次尝试, 失败自动降级下一个, 全部失败返回 None
(DeepL 相关函数保留但已停用: 免费额度不足, 暂不参与翻译链路)
"""
import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# 每个 Provider 一个持久 Session, 复用 TCP/TLS 连接(Uvicorn 进程内), 消除每次请求的 TLS 握手冷启动
_SESSION = requests.Session()


def _google_key():
    """动态读取(支持运行中改配置即时生效)"""
    return getattr(settings, "GOOGLE_TRANSLATE_API_KEY", None)


def _baidu_appid():
    return getattr(settings, "BAIDU_APPID", None)


def _baidu_appkey():
    return getattr(settings, "BAIDU_APPKEY", None)


def _baidu_url():
    endpoint = getattr(settings, "BAIDU_ENDPOINT", "http://api.fanyi.baidu.com")
    path = getattr(settings, "BAIDU_PATH", "/api/trans/vip/translate")
    return endpoint + path


# 百度翻译免费版 QPS=1, 用进程内节流错开突发调用, 减少 54003(请求频率超限)
import threading
_baidu_lock = threading.Lock()
_baidu_last_call = 0.0
_BUADU_MIN_INTERVAL = 1.5  # 秒


def _baidu_throttle():
    """百度 QPS=1 节流: 距上次调用不足最小间隔则等待, 避免 54003"""
    global _baidu_last_call
    with _baidu_lock:
        now = time.monotonic()
        wait = _BUADU_MIN_INTERVAL - (now - _baidu_last_call)
        if wait > 0:
            time.sleep(wait)
            now = time.monotonic()
        _baidu_last_call = now


def _get_proxy():
    """每次动态读取代理(支持运行中改配置/部署SG无代理时即时生效)"""
    return getattr(settings, "LINE_API_PROXY", None) or None


def _proxies():
    proxy = _get_proxy()
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def _deepl_auth(api_key):
    """拼接 DeepL Auth Header; 兼容 key 是否带 :fx 后缀"""
    if api_key.endswith(":fx"):
        return f"DeepL-Auth-Key {api_key}"
    return f"DeepL-Auth-Key {api_key}:fx"


def _get_deepl_keys():
    """从 DB 读取所有启用 Key(默认优先), 用于多 Key 轮询/超限降级"""
    from dvadmin.notify.models import get_active_deepl_keys
    return get_active_deepl_keys()


def _translate_deepl(text, target="EN", api_key=None):
    """DeepL 官方 API, 免代理; Session 连接池复用; 超时降级; 单 Key 翻译"""
    if not api_key:
        raise RuntimeError("DeepL key not configured")
    resp = _SESSION.post(
        getattr(settings, "DEEPL_API_URL", "https://api-free.deepl.com/v2/translate"),
        headers={"Authorization": _deepl_auth(api_key), "Content-Type": "application/json"},
        json={"text": [text], "target_lang": target, "preserve_formatting": True},
        timeout=8,
    )
    if resp.status_code == 456 or resp.status_code == 452:
        # 456: 配额超限(本月字符/翻译数用尽); 452: 超出最大请求数
        raise RuntimeError(f"DeepL quota-exceeded {resp.status_code}")
    if resp.status_code != 200:
        raise RuntimeError(f"DeepL {resp.status_code}: {resp.text[:120]}")
    return resp.json()["translations"][0]["text"]


def _translate_deepl_multi(text, target="EN"):
    """
    多 Key 池翻译: 依次尝试所有启用 Key(默认优先), 遇 456/452(额度超限)自动切换下一个;
    全部失败抛最后一个错误
    """
    keys = _get_deepl_keys()
    if not keys:
        raise RuntimeError("No active DeepL key configured")
    last_err = None
    for key in keys:
        try:
            return _translate_deepl(text, target=target, api_key=key.api_key)
        except RuntimeError as e:
            last_err = e
            if "quota-exceeded" in str(e):
                logger.warning("DeepL key=%s 额度超限, 切换到下一个", getattr(key, "name", key.id))
                continue
            raise
    raise RuntimeError(f"DeepL all keys failed: {last_err}")



def _translate_google_cloud(text, target="en"):
    """Google Cloud Translation (v2), 走代理; Session 连接池复用; 兜底"""
    google_key = _google_key()
    if not google_key:
        raise RuntimeError("GOOGLE_TRANSLATE_API_KEY not configured")
    resp = _SESSION.post(
        f"https://translation.googleapis.com/language/translate/v2?key={google_key}",
        json={"q": text, "target": target},
        proxies=_proxies(),
        timeout=8,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"GoogleCloud {resp.status_code}: {resp.text[:120]}")
    return resp.json()["data"]["translations"][0]["translatedText"]


def _translate_deep_translator(text, source="th", target="en"):
    """deep_translator 网页版, 最后兜底(易 429)"""
    from deep_translator import GoogleTranslator
    kwargs = {}
    proxy = _get_proxy()
    if proxy:
        kwargs["proxies"] = {"http": proxy, "https": proxy}
    translator = GoogleTranslator(source=source, target=target, **kwargs)
    return translator.translate(text)


def _translate_baidu(text, source="th", target="en"):
    """百度翻译(主Provider): 国内直连免代理, 月配额高; QPS=1(免费版需限速调用)"""
    import random
    from hashlib import md5

    appid = _baidu_appid()
    appkey = _baidu_appkey()
    if not appid or not appkey:
        raise RuntimeError("BAIDU appid/appkey not configured")
    _baidu_throttle()
    salt = random.randint(32768, 65536)
    raw = f"{appid}{text}{salt}{appkey}"
    sign = md5(raw.encode("utf-8")).hexdigest()
    payload = {
        "appid": appid,
        "q": text,
        "from": source,
        "to": target,
        "salt": salt,
        "sign": sign,
    }
    resp = _SESSION.post(
        _baidu_url(),
        params=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=8,
    )
    result = resp.json()
    if result.get("error_code") not in (None, "52000"):
        raise RuntimeError(f"Baidu {result.get('error_code')}: {result.get('error_msg')}")
    # Baidu 按换行拆分返回多条 trans_result, 用 \n 重新拼接以保留原始换行
    parts = result.get("trans_result") or []
    return "\n".join(x.get("dst", "") for x in parts)


def _translate_fallback(text):
    """兜底: 用 deep_translator 自动探测语言译成英文"""
    return _translate_deep_translator(text, source="auto", target="en")


def translate(text, source="auto", target="en"):
    """
    多 provider 顺序降级翻译, 全部失败返回 None
    仅当 text 非空才处理
    """
    if not text:
        return None
    # 顺序: 百度(主, 国内直连月配额高) -> googleCloud(降级) -> deep_translator 最后兜底
    # DeepL 已停用(免费额度不足), 相关函数保留备用
    providers = []
    if _baidu_appid() and _baidu_appkey():
        providers.append("baidu")
    if _google_key():
        providers.append("googleCloud")

    errors = []
    for provider in providers:
        try:
            if provider == "baidu":
                res = _translate_baidu(text, source=source, target=target)
            elif provider == "googleCloud":
                res = _translate_google_cloud(text, target=target)
            else:
                res = _translate_fallback(text)
            if res:
                return res
        except Exception as e:
            errors.append(f"{provider}: {e}")
            logger.warning("翻译 provider %s 失败: %s", provider, e)
            continue

    # 全部失败再兜底一次 deep_translator
    try:
        return _translate_fallback(text)
    except Exception as e:
        errors.append(f"fallback: {e}")
        logger.warning("翻译全部失败: %s", errors)
        return None
