# -*- coding: utf-8 -*-
import os

from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build

# 预创建 discovery 缓存, 避免每次 build 触发网络请求(被墙时尤其重要)
_DISCOVERY_CACHE = {}


def _setup_proxy():
    """
    国内环境下访问 Google 需走 VPN 代理。
    从 settings.GOOGLE_API_PROXY 读取(如 http://host:port 或 socks5://host:port),
    设置到环境变量, httplib2 与 requests 都会自动读取。
    """
    proxy = getattr(settings, 'GOOGLE_API_PROXY', '') or ''
    if proxy:
        os.environ.setdefault('HTTPS_PROXY', proxy)
        os.environ.setdefault('HTTP_PROXY', proxy)
        os.environ.setdefault('ALL_PROXY', proxy)


def get_credentials():
    """构建服务账号凭据"""
    _setup_proxy()
    return service_account.Credentials.from_service_account_file(
        settings.GOOGLE_CALENDAR_SERVICE_ACCOUNT_FILE,
        scopes=settings.GOOGLE_CALENDAR_SCOPES,
    )


def get_calendar_service():
    """构建 Google Calendar v3 服务对象"""
    _setup_proxy()
    credentials = get_credentials()
    service = build(
        'calendar', 'v3',
        credentials=credentials,
        cache_discovery=False,
    )
    return service
