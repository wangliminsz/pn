# -*- coding: utf-8 -*-
"""
深色主题 SVG 验证码生成器(替代 django-simple-captcha 的 PNG)
- 4 位随机字母数字, 排除易混淆 0O/1l/I
- 深色背景 + 浅色前景 + 干扰线/噪点, 与 proNotify 深色登录页一致
- 答案由调用方写入 CaptchaStore(兼容现有 LoginSerializer 校验逻辑)
"""
import random
import string
import base64
from io import BytesIO

# 排除易混淆字符
_CHARS = "23456789ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz"

# 深色主题配色(与 design-system/pronotify 一致)
_BG = "#1a1a1c"
_FG_COLORS = ["#64DAAA", "#6A9DFF", "#E2B25C", "#D98FB8", "#8FC8E8"]
_LINE_COLOR = "rgba(100,154,255,0.35)"
_NOISE_COLOR = "rgba(255,255,255,0.18)"


def _random_text(length=4):
    return "".join(random.choice(_CHARS) for _ in range(length))


def _sanitize_for_svg(text):
    """SVG text 节点转义, 防 SVG 注入"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def generate_svg(text=None, width=120, height=44):
    """生成深色 SVG 验证码, 返回 (svg_str, answer)"""
    text = text or _random_text(4)
    answer = text
    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" style="background:{_BG}">'
    )
    # 背景(圆角卡片)
    parts.append(
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" fill="{_BG}"/>'
    )
    parts.append(
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" '
        f'fill="none" stroke="rgba(255,255,255,0.12)"'
        f'/>'
    )

    # 干扰线(2-3 条)
    random.seed()
    for _ in range(random.randint(2, 3)):
        x1 = random.randint(0, width // 3)
        y1 = random.randint(2, height - 2)
        x2 = random.randint(width * 2 // 3, width)
        y2 = random.randint(2, height - 2)
        parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{_LINE_COLOR}" stroke-width="1.2"/>'
        )

    # 噪点
    for _ in range(random.randint(18, 30)):
        cx = random.randint(2, width - 2)
        cy = random.randint(2, height - 2)
        r = random.choice([0.8, 1.0, 1.2, 1.4])
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{_NOISE_COLOR}"/>'
        )

    # 文字: 逐字符随机颜色/旋转/微小位移
    n = len(text)
    char_w = width / (n + 1)
    for i, ch in enumerate(text):
        x = char_w * (i + 1)
        y = height / 2 + random.randint(-3, 4)
        color = random.choice(_FG_COLORS)
        rot = random.randint(-18, 18)
        dy = random.randint(-2, 2)
        parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="26" '
            f'font-family="Verdana, Arial, sans-serif" font-weight="bold" '
            f'text-anchor="middle" fill="{color}" '
            f'transform="rotate({rot} {x:.1f} {y:.1f}) translate(0 {dy})">'
            f'{_sanitize_for_svg(ch)}</text>'
        )

    parts.append("</svg>")
    return "".join(parts), answer


def svg_to_data_uri(svg_str):
    """SVG 字符串 -> data URI(base64), 前端 <img src> 直接用"""
    encoded = base64.b64encode(svg_str.encode("utf-8")).decode("utf-8")
    return "data:image/svg+xml;base64," + encoded