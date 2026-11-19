# -*- coding: utf-8 -*-
"""
Line Bot Webhook 处理
- 多 Bot 验签: 根据 X-LINE-Signature 能验签通过的 channel_secret 定位是哪个 Bot
- 群消息: 翻译(depth_translator, 走代理) + 群文档/图片存 media/{tenant_id}/group_files/
- reply 消息不计入配额
"""
import logging
import os
import re
from urllib.parse import quote

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from dvadmin.utils.cos_storage import COS_ENABLED, save_file
from linebot import WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    FollowEvent,
    FileMessage,
    ImageMessage,
    JoinEvent,
    LeaveEvent,
    MessageEvent,
    SourceGroup,
    TextMessage,
    TextSendMessage,
)

logger = logging.getLogger(__name__)

# 翻译代理(与 Google Calendar/LINE 相同)
PROXY = getattr(settings, "LINE_API_PROXY", None) or None


def _translate(text, source='auto', target='en'):
    """多 provider 随机 + 降级翻译, 失败返回 None"""
    if not text:
        return None
    from dvadmin.notify.translators import translate as translate_multi
    return translate_multi(text, source=source, target=target)


def _detect_language(text):
    """简单语言探测: 含泰文字符视为 th, 否则 en"""
    if re.search(r'[\u0E00-\u0E7F]', text):
        return 'th'
    return 'en'


def _find_parser_for_signature(body, signature):
    """遍历所有启用 Bot, 找到能通过验签的那个, 返回 (event_list, line_bot)"""
    from dvadmin.notify.models import LineBot

    for bot in LineBot.objects.filter(is_active=True):
        try:
            parser = WebhookParser(bot.channel_secret)
            events = parser.parse(body, signature)
            # 验签通过
            return events, bot
        except InvalidSignatureError:
            continue
        except Exception as e:
            logger.warning("解析异常 bot=%s: %s", bot.name, e)
    return None, None


def _get_property_by_group(group_id):
    """根据群ID找房源 -> 用于定位租户"""
    from dvadmin.property.models import Property
    return Property.objects.filter(group_id=group_id).first()


def _get_message_text(event):
    """提取消息文本"""
    if isinstance(event.message, TextMessage):
        return event.message.text
    return None


def _group_files_rel(tenant_id, group_id):
    """群文档相对路径(相对 MEDIA_ROOT / COS 根): {tenant_id}/group_files/{group_id}"""
    return f"{str(tenant_id) if tenant_id else 'unknown'}/group_files/{str(group_id or 'unknown')}"


def _download_media(line_bot, message_id, rel_dir, ext):
    """下载 LINE 文件/图片到 COS(或本地), 返回文件名"""
    import requests
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    headers = {"Authorization": f"Bearer {line_bot.channel_access_token}"}
    try:
        resp = requests.get(url, headers=headers, proxies=_proxies(), timeout=30)
        if resp.status_code != 200:
            return None
        # 用真实字节探测扩展名(图片可能 png/gif/webp, 避免 jpg 标签标错)
        ext = _sniff_ext(resp.content, ext)
        filename = f"{message_id}.{ext}"
        rel = f"{rel_dir}/{filename}"
        if COS_ENABLED:
            save_file(rel, resp.content)
        else:
            local = os.path.join(settings.MEDIA_ROOT, rel)
            os.makedirs(os.path.dirname(local), exist_ok=True)
            with open(local, 'wb') as f:
                f.write(resp.content)
        return filename
    except Exception as e:
        logger.error("下载媒体失败: %s", e)
        return None


def _sniff_ext(data, fallback):
    """根据文件字节 magic number 判断真实扩展名; 识别不出来用 fallback"""
    if not data:
        return fallback
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    if data[:3] == b'\xff\xd8\xff':
        return 'jpg'
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    if data[:4] == b'%PDF':
        return 'pdf'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'webp'
    if data[:2] == b'BM':
        return 'bmp'
    return fallback


def _proxies():
    proxy = getattr(settings, "LINE_API_PROXY", None)
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def _reply_text(line_bot, reply_token, text):
    """通过代理调用 LINE reply API(不走SDK, 以支持大陆代理)"""
    import requests
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Authorization": f"Bearer {line_bot.channel_access_token}",
        "Content-Type": "application/json",
    }
    payload = {"replyToken": reply_token, "messages": [{"type": "text", "text": text}]}
    try:
        resp = requests.post(url, headers=headers, json=payload, proxies=_proxies(), timeout=15)
        return resp.status_code == 200
    except Exception as e:
        logger.warning("reply失败: %s", e)
        return False


def _handle_translate(line_bot, event, prop):
    """群文本消息翻译: 参考单用户版, 仅当消息含泰语时才翻译为英文并 reply; 英文/其他不回复"""
    if not getattr(settings, "LINE_BOT_TRANSLATE_ENABLED", True):
        return
    text = _get_message_text(event)
    if not text:
        return
    source = _detect_language(text)
    # 只处理含泰语 -> 译成英文; 英文/其他语言不回
    if source != 'th':
        return
    result = _translate(text, source='th', target='en')
    if result:
        _reply_text(line_bot, event.reply_token, result)


def _handle_image(line_bot, event, prop, group_id):
    """图片/文件下载保存到群文档目录(按租户+群区分), 成功后回执确认形成闭环
    并写入 GroupDocRecord(仅新存储): 记录 bot 名 / 存储时间 / 消息时间 / 发送人
    """
    from datetime import datetime

    from dvadmin.notify.models import GroupDocRecord

    tenant = prop.tenant if prop else None
    rel_dir = _group_files_rel(tenant.id if tenant else None, group_id)
    # 根据消息类型推断扩展名: 图片默认 jpg, 文件取真实文件名后缀, 未知则兜底
    if isinstance(event.message, ImageMessage):
        ext = 'jpg'
        ack = "Img received, thanks"
    elif isinstance(event.message, FileMessage):
        fn = event.message.file_name or ''
        ext = os.path.splitext(fn)[1].lstrip('.') or 'pdf'
        ack = "File received, thanks"
    else:
        ext = 'file'
        ack = "File received, thanks"
    filename = _download_media(line_bot, event.message.id, rel_dir, ext)
    if filename:
        logger.info("已存群文档: %s/%s", rel_dir, filename)
        # 记录存储信息(仅新文件; 不阻塞主流程)
        try:
            GroupDocRecord.objects.create(
                tenant=tenant,
                line_bot=line_bot,
                bot_name=line_bot.name,
                property=prop,
                group_id=group_id,
                message_id=event.message.id,
                file_name=filename,
                store_time=datetime.now(),
                message_time=datetime.fromtimestamp(event.timestamp / 1000) if getattr(event, 'timestamp', None) else None,
                sender_user_id=getattr(event.source, 'user_id', None),
            )
        except Exception as e:
            logger.warning("记录群文档失败: %s", e)
        _reply_text(line_bot, event.reply_token, ack)


def _handle_message(line_bot, event):
    prop = None
    group_id = None
    if isinstance(event.source, SourceGroup):
        group_id = event.source.group_id
        prop = _get_property_by_group(group_id)
    if isinstance(event.message, TextMessage):
        text = event.message.text
        # 调试命令: 发送 group_id/group-id/groupid/#id/#group 让 bot 上报本群在这台 bot 视角的 group_id
        if text and text.strip().lower() in ('group_id', 'group-id', 'groupid', '#id', '#group', 'group'):
            reply = f"Group ID:\n\n{group_id}"
            _reply_text(line_bot, event.reply_token, reply)
            return
        _handle_translate(line_bot, event, prop)
    elif isinstance(event.message, (ImageMessage, FileMessage)):
        _handle_image(line_bot, event, prop, group_id)
    # 其他类型暂不处理


@csrf_exempt
@require_POST
def line_webhook(request):
    signature = request.META.get('HTTP_X_LINE_SIGNATURE', '')
    body = request.body.decode('utf-8')

    events, line_bot = _find_parser_for_signature(body, signature)
    if events is None:
        return HttpResponseForbidden()

    for event in events:
        try:
            if isinstance(event, MessageEvent):
                _handle_message(line_bot, event)
            elif isinstance(event, (JoinEvent, FollowEvent)):
                logger.info("Bot %s 加入/关注事件", line_bot.name)
            elif isinstance(event, LeaveEvent):
                logger.info("Bot %s 退出事件", line_bot.name)
        except Exception as e:
            logger.exception("处理事件异常 bot=%s: %s", line_bot.name, e)

    return HttpResponse()
