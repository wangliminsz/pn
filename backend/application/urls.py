"""backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.urls import path, include, re_path
from django.views.static import serve
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from application import dispatch
from application import settings
from application.sse_views import sse_view
from dvadmin.system.views.dictionary import InitDictionaryViewSet
from dvadmin.system.views.login import (
    LoginView,
    CaptchaView,
    ApiLogin,
    LogoutView,
    LoginTokenView
)
from dvadmin.system.views.system_config import InitSettingsViewSet
from dvadmin.system.views.payment_public import PublicPaymentConfigView
from dvadmin.notify.webhook import line_webhook as webhook_view
from dvadmin.utils.swagger import CustomOpenAPISchemaGenerator

# =========== 初始化系统配置 =================
dispatch.init_system_config()
dispatch.init_dictionary()
# =========== 初始化系统配置 =================

permission_classes = [permissions.AllowAny, ] if settings.DEBUG else [permissions.IsAuthenticated, ]
schema_view = get_schema_view(
    openapi.Info(
        title="Snippets API",
        default_version="v1",
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=permission_classes,
    generator_class=CustomOpenAPISchemaGenerator,
)
# 前端页面映射
from django.http import Http404, HttpResponse
from django.shortcuts import render
import mimetypes
import os


def web_view(request):
    return render(request, 'web/index.html')


def serve_web_files(request, filename):
    # 设定文件路径
    filepath = os.path.join(settings.BASE_DIR, 'templates', 'web', filename)

    # 检查文件是否存在
    if not os.path.exists(filepath):
        raise Http404("File does not exist")

    # 根据文件扩展名，确定 MIME 类型
    mime_type, _ = mimetypes.guess_type(filepath)

    # 打开文件并读取内容
    with open(filepath, 'rb') as f:
        response = HttpResponse(f.read(), content_type=mime_type)
        return response


# 兼容旧版后端: 租户模块未注册 public_config 路由时, 兜底提供前端依赖的只读接口
def _tenant_registers_public_config():
    try:
        from dvadmin.tenant import urls as tenant_urls
    except Exception:
        return False
    for pattern in getattr(tenant_urls, "urlpatterns", []):
        if str(getattr(pattern, "pattern", "")).strip("/") == "payment/public_config":
            return True
    return False


_COMPAT_URLPATTERNS = [] if _tenant_registers_public_config() else [
    path("api/tenant/payment/public_config/", PublicPaymentConfigView.as_view()),
]

urlpatterns = (
        [
            re_path(
                r"^swagger(?P<format>\.json|\.yaml)$",
                schema_view.without_ui(cache_timeout=0),
                name="schema-json",
            ),
            path(
                "",
                schema_view.with_ui("swagger", cache_timeout=0),
                name="schema-swagger-ui",
            ),
            path(
                r"redoc/",
                schema_view.with_ui("redoc", cache_timeout=0),
                name="schema-redoc",
            ),
            path("api/system/", include("dvadmin.system.urls")),
            path("api/tenant/", include("dvadmin.tenant.urls")),
            path("api/property/", include("dvadmin.property.urls")),
            path("api/notify/", include("dvadmin.notify.urls")),
            path("webhook/line/", webhook_view, name="line_webhook"),
            path("webhook/line", webhook_view),  # 兼容无尾斜杠(LINE webhook 校验)
            path("api/login/", LoginView.as_view(), name="token_obtain_pair"),
            path("api/logout/", LogoutView.as_view(), name="token_obtain_pair"),
            path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
            re_path(
                r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")
            ),
            path("api/captcha/", CaptchaView.as_view()),
            path("api/init/dictionary/", InitDictionaryViewSet.as_view()),
            path("api/init/settings/", InitSettingsViewSet.as_view()),
            path("apiLogin/", ApiLogin.as_view()),

            # 仅用于开发，上线需关闭
            path("api/token/", LoginTokenView.as_view()),
            # 前端页面映射
            path('web/', web_view, name='web_view'),
            path('web/<path:filename>', serve_web_files, name='serve_web_files'),
            # sse
            path('sse/', sse_view, name='sse'),
        ]
        + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
        + static(settings.STATIC_URL, document_root=settings.STATIC_URL)
        + [re_path(ele.get('re_path'), include(ele.get('include'))) for ele in settings.PLUGINS_URL_PATTERNS]
        + _COMPAT_URLPATTERNS
)
