# -*- coding: utf-8 -*-
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.utils.translation import gettext as _

from dvadmin.tenant.models import Tenant
from dvadmin.tenant.serializers import TenantSerializer
from dvadmin.tenant.org_chart import (TEMPLATE_HEADERS, apply, build_tree, create_or_update_dept,
                                      delete_dept, delete_member, parse_file, parse_inline_rows,
                                      preview, save_member)
from dvadmin.utils.filters import CoreModelFilterBankend, OwnerDataLevelFilter
from dvadmin.utils.json_response import DetailResponse, ErrorResponse, SuccessResponse
from dvadmin.utils.permission import SuperuserPermission
from dvadmin.utils.viewset import CustomModelViewSet


def _org_manage_ok(user, tenant_id):
    """组织架构管理权限: 超管 或 本租户的租户经理(tenant_manager)"""
    if getattr(user, "is_superuser", False):
        return True
    tenant = getattr(user, "tenant", None)
    if tenant is None or tenant.id != tenant_id:
        return False
    return user.role.filter(key="tenant_manager").exists()


def _org_guard(request, pk):
    """取到 Tenamt 且校验管理权限; 返回 (instance|None, instance)"""
    instance = Tenant.objects.filter(pk=pk).first()
    if instance is None or not _org_manage_ok(request.user, instance.id):
        return None
    return instance


class TenantViewSet(CustomModelViewSet):
    """
    租户管理接口(仅超级管理员可操作)
    list:查询
    create:新增
    update:修改
    retrieve:单例
    destroy:删除
    """
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [SuperuserPermission]

    def get_queryset(self):
        # 预取已分配的 Line Bot, 避免 line_bots 字段 N+1
        return super().get_queryset().prefetch_related("linebot_set")

    @action(methods=["GET"], detail=False)
    def options(self, request):
        """下拉选项"""
        data = self.get_queryset().values("id", "name", "tenant_code")
        return SuccessResponse(data=data)

    def list(self, request, *args, **kwargs):
        """关键字搜索: 名称/租户标识/联系人/电话/签名/GoogleID(单框多字段模糊匹配)
        ?expired=1 只显示已到期/停用的租户(expire_time < now 或 is_active=False)"""
        request.query_params._mutable = True
        name_list = request.query_params.pop('name', None)
        keyword = (name_list[-1] if isinstance(name_list, (list, tuple)) and name_list else name_list) or None
        expired = request.query_params.pop('expired', None)
        want_expired = (expired[-1] if isinstance(expired, (list, tuple)) and expired else expired)
        queryset = self.get_queryset()
        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword)
                | Q(tenant_code__icontains=keyword)
                | Q(contact_name__icontains=keyword)
                | Q(contact_phone__icontains=keyword)
                | Q(sign_name__icontains=keyword)
                | Q(google_calendar_id__icontains=keyword)
            )
        if want_expired and str(want_expired) not in ("0", "false", "False"):
            from django.db.models import Q as _Q
            now = timezone.now()
            queryset = queryset.filter(_Q(expire_time__lt=now) | _Q(is_active=False))
        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, request=request)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True, request=request)
        return SuccessResponse(data=serializer.data, msg=_("Query successful"))

    @action(methods=["GET"], detail=True, permission_classes=[IsAuthenticated])
    def orgchart(self, request, pk):
        """组织架构树(部门 + 成员)"""
        instance = _org_guard(request, pk)
        if instance is None:
            return ErrorResponse(msg=_("No permission to manage this tenant's org chart"))
        return DetailResponse(data=build_tree(instance))

    @action(methods=["GET"], detail=True, permission_classes=[IsAuthenticated])
    def orgchart_template(self, request, pk):
        """导入模板列定义 + 新账号默认密码(前端据此生成 CSV 模板并在导入页展示)"""
        from application import dispatch

        default_password = dispatch.get_system_config_values("base.default_password") or "admin123456"
        return SuccessResponse(data={"headers": TEMPLATE_HEADERS, "default_password": default_password})

    @action(methods=["POST"], detail=True, permission_classes=[IsAuthenticated])
    def orgchart_import(self, request, pk):
        """
        组织架构批量导入
        - 支持上传文件(multipart: file) 或 JSON(rows)
        - dry_run=true(默认) 仅预览; dry_run=false 正式落库
        """
        instance = _org_guard(request, pk)
        if instance is None:
            return ErrorResponse(msg=_("No permission to manage this tenant's org chart"))
        dry_run = str(request.data.get("dry_run", request.query_params.get("dry_run", "true"))).lower() in ("1", "true", "yes")

        rows = []
        file_obj = request.FILES.get("file")
        if file_obj:
            rows = parse_file(file_obj)
        else:
            json_rows = request.data.get("rows")
            if not isinstance(json_rows, list):
                return ErrorResponse(msg=_("Please upload a file or provide a rows array"))
            rows = parse_inline_rows(json_rows)

        if not rows:
            return ErrorResponse(msg=_("No valid data rows parsed"))

        if dry_run:
            return SuccessResponse(data=preview(instance, rows))

        result = apply(instance, rows)
        return SuccessResponse(data=result, msg=_("Org chart import completed"))

    @action(methods=["POST"], detail=True, permission_classes=[IsAuthenticated])
    def orgchart_dept_save(self, request, pk=None):
        """新增/重命名部门(id 存在则更新)；parent_id 为空=挂在公司根"""
        instance = _org_guard(request, pk)
        if instance is None:
            return ErrorResponse(msg=_("No permission to manage this tenant's org chart"))
        try:
            dept = create_or_update_dept(
                instance,
                dept_id=request.data.get("id"),
                name=(request.data.get("name") or "").strip(),
                parent_id=request.data.get("parent_id"),
            )
        except ValueError as e:
            return ErrorResponse(msg=str(e))
        return SuccessResponse(data={"id": dept.id, "name": dept.name}, msg=_("Dept saved"))

    @action(methods=["POST"], detail=True, permission_classes=[IsAuthenticated])
    def orgchart_dept_delete(self, request, pk=None):
        """删除部门(有子部门/成员则拒绝)"""
        instance = _org_guard(request, pk)
        if instance is None:
            return ErrorResponse(msg=_("No permission to manage this tenant's org chart"))
        try:
            delete_dept(instance, request.data.get("id"))
        except ValueError as e:
            return ErrorResponse(msg=str(e))
        return SuccessResponse(data=[], msg=_("Dept deleted"))

    @action(methods=["POST"], detail=True, permission_classes=[IsAuthenticated])
    def orgchart_member_save(self, request, pk=None):
        """新增/编辑成员(id 存在则更新)；dept_id 为空=挂公司根；新增默认密码见返回"""
        instance = _org_guard(request, pk)
        if instance is None:
            return ErrorResponse(msg=_("No permission to manage this tenant's org chart"))
        try:
            user = save_member(
                instance,
                user_id=request.data.get("id"),
                name=(request.data.get("name") or "").strip(),
                username=(request.data.get("username") or "").strip(),
                mobile=(request.data.get("mobile") or "").strip(),
                dept_id=request.data.get("dept_id"),
                tier=request.data.get("tier"),
                is_active=bool(request.data.get("is_active", True)),
            )
        except ValueError as e:
            return ErrorResponse(msg=str(e))
        from application import dispatch
        default_password = (dispatch.get_system_config_values("base.default_password")
                            or "admin123456")
        return SuccessResponse(
            data={"id": user.id, "username": user.username, "default_password": default_password},
            msg=_("Member saved"),
        )

    @action(methods=["POST"], detail=True, permission_classes=[IsAuthenticated])
    def orgchart_member_delete(self, request, pk=None):
        """删除成员"""
        instance = _org_guard(request, pk)
        if instance is None:
            return ErrorResponse(msg=_("No permission to manage this tenant's org chart"))
        try:
            delete_member(instance, request.data.get("id"))
        except ValueError as e:
            return ErrorResponse(msg=str(e))
        return SuccessResponse(data=[], msg=_("Member deleted"))

    @action(methods=["POST"], detail=True, permission_classes=[IsAuthenticated])
    def orgchart_clear(self, request, pk=None):
        """清空该租户的组织架构(删除其全部部门与成员), 但保留租户本身, 便于重建导入"""
        instance = _org_guard(request, pk)
        if instance is None:
            return ErrorResponse(msg=_("No permission to manage this tenant's org chart"))
        deleted_users = Users.objects.filter(tenant=instance).count()
        deleted_depts = Dept.objects.filter(tenant=instance).count()
        # 先删成员(用户), 再删部门(避免外键约束)
        Users.objects.filter(tenant=instance).delete()
        Dept.objects.filter(tenant=instance).delete()
        return SuccessResponse(
            data={"deleted_users": deleted_users, "deleted_depts": deleted_depts},
            msg=_("Org chart cleared (members {}, depts {})").format(deleted_users, deleted_depts),
        )

    def destroy(self, request, *args, **kwargs):
        """
        删除租户: 级联清理该租户名下所有数据(按依赖顺序), 避免 PROTECT 外键拦截
        删除顺序: 消息日志 -> 群文档记录 -> 群发任务 -> 房源(含附件/提醒规则/变更日志) -> 用户 -> 部门 -> 角色 -> 租户支付 -> 租户
        LineBot 记录保留不删(已取消分配的 bot 留作平台默认, 不随租户删除)
        """
        instance = self.get_object()
        # 延迟导入, 避免 apps 加载顺序造成的循环依赖
        from dvadmin.notify.models import LineBot, MessageLog, GroupDocRecord, BroadcastTask
        from dvadmin.property.models import Property
        from dvadmin.system.models import Dept, Role, Users
        from dvadmin.tenant.models import TenantPayment

        # 保护: 租户仍已分配 LineBot 时禁止删除(需先取消分配); 已取消分配则 LineBot 记录保留
        if LineBot.objects.filter(tenant=instance).exists():
            return ErrorResponse(msg=_("Linebot assigned"))

        with transaction.atomic():
            # 1. 消息日志(它 PROTECT LineBot/Property, 引用的 bot 保留也须先删)
            MessageLog.objects.filter(tenant=instance).delete()
            # 2. 群文档记录(它 PROTECT LineBot/tenant)
            GroupDocRecord.objects.filter(tenant=instance).delete()
            # 3. 群发任务(它 PROTECT tenant)
            BroadcastTask.objects.filter(tenant=instance).delete()
            # 4. 房源(它 PROTECT LineBot/User.owner, 随房源 CASCADE 清理附件/提醒规则/变更日志)
            Property.objects.filter(tenant=instance).delete()
            # 5. 用户(Users.dept PROTECT 指向部门, 故需先删用户再删部门)
            Users.objects.filter(tenant=instance).delete()
            # 6. 部门
            Dept.objects.filter(tenant=instance).delete()
            # 7. 角色(被 用户/权限绑定 PROTECT, 前述均已清理)
            Role.objects.filter(tenant=instance).delete()
            # 8. 租户支付记录(显式清理, CASCADE 也行)
            TenantPayment.objects.filter(tenant=instance).delete()
            # 9. 租户本体(不删除 LineBot: 上方已拦截"仍被分配"的情况, 取消分配后记录保留)
            instance.delete()
        return DetailResponse(data=[], msg=_("Delete successful"))

    @action(methods=["POST"], detail=True, permission_classes=[IsAuthenticated])
    def google_calendar(self, request, pk=None):
        """
        租户经理(或超管)修改本租户的 Google Calendar ID, 并自动同步本租户房源到新日历
        body: { google_calendar_id: string }(空串=清空, 不再写日历)
        返回: { google_calendar_id, synced, failed, msgs }
        """
        instance = Tenant.objects.filter(pk=pk).first()
        if instance is None or not _org_manage_ok(request.user, instance.id):
            return ErrorResponse(msg=_("No permission to manage this tenant's calendar settings"))
        # 校验唯一性(复用序列化器逻辑)
        new_id = (request.data.get("google_calendar_id") or "").strip()
        dup = Tenant.objects.filter(google_calendar_id=new_id).exclude(pk=instance.pk) if new_id else Tenant.objects.none()
        if dup.exists():
            return ErrorResponse(msg=_("This Google calendar ID is already used by another tenant"))
        old_id = instance.google_calendar_id or None  # 改前旧日历, 用于清理旧事件
        instance.google_calendar_id = new_id or None
        instance.save(update_fields=["google_calendar_id"])

        # 自动同步本租户房源(换日历会先删旧日历事件再写新日历; 清空则删除旧事件)
        synced = failed = 0
        msgs = []
        from dvadmin.property.gcal_events import sync_tenant_events
        try:
            synced, failed, msgs = sync_tenant_events(instance, legacy_calendar_id=old_id)
        except Exception as e:
            return SuccessResponse(data={
                "google_calendar_id": instance.google_calendar_id or "",
                "synced": 0, "failed": 0, "msgs": [_("Calendar sync exception: {}").format(e)],
            }, msg=_("Google calendar saved, but sync failed"))
        return SuccessResponse(data={
            "google_calendar_id": instance.google_calendar_id or "",
            "synced": synced,
            "failed": failed,
            "msgs": msgs,
        }, msg=_("Google calendar updated, synced {}, failed {}").format(synced, failed))

    @action(methods=["POST"], detail=True, permission_classes=[IsAuthenticated])
    def sign_name(self, request, pk=None):
        """
        租户经理(或超管)修改本租户的落款签名(提醒消息末尾的公司名)
        body: { sign_name: string }(空串=恢复默认, 用公司名/全局签名)
        """
        instance = Tenant.objects.filter(pk=pk).first()
        if instance is None or not _org_manage_ok(request.user, instance.id):
            return ErrorResponse(msg=_("No permission to manage this tenant's signature settings"))
        new_sign = (request.data.get("sign_name") or "").strip()
        instance.sign_name = new_sign or None
        instance.save(update_fields=["sign_name"])
        return SuccessResponse(data={"sign_name": instance.sign_name or ""}, msg=_("Signature updated"))

    @action(methods=["POST"], detail=True, permission_classes=[IsAuthenticated])
    def company_name(self, request, pk=None):
        """
        租户经理(或超管)修改本租户的公司名称
        body: { name: string }
        """
        instance = Tenant.objects.filter(pk=pk).first()
        if instance is None or not _org_manage_ok(request.user, instance.id):
            return ErrorResponse(msg=_("No permission to manage this tenant's company name"))
        new_name = (request.data.get("name") or "").strip()
        if not new_name:
            return ErrorResponse(msg=_("Company name cannot be empty"))
        instance.name = new_name
        instance.save(update_fields=["name"])
        return SuccessResponse(data={"name": instance.name}, msg=_("Company name updated"))

    @action(methods=["POST"], detail=True, permission_classes=[SuperuserPermission])
    def sync_calendar(self, request, pk=None):
        """
        超管手动触发: 补写该租户全部已开启日历的房源到 Google Calendar
        (配好服务账号后一键补写老房源; 不改租户日历ID; 相当于前端版 manage.py sync_calendar --tenant_id)
        """
        instance = Tenant.objects.filter(pk=pk).first()
        if instance is None:
            return ErrorResponse(msg=_("Tenant does not exist"))
        from dvadmin.property.gcal_events import sync_tenant_events
        try:
            synced, failed, msgs = sync_tenant_events(instance)
        except Exception as e:
            return ErrorResponse(msg=_("Sync exception: {}").format(e))
        return SuccessResponse(data={"synced": synced, "failed": failed, "msgs": msgs},
                               msg=_("Sync completed: {} succeeded, {} failed").format(synced, failed))


def get_tenant_queryset(tenant_id, queryset):
    """
    Celery 定时任务等无请求上下文场景下, 按租户过滤数据集
    如果不传 tenant_id 则认为非法调用, 返回空集, 防止全表扫描越权
    """
    if tenant_id:
        return queryset.filter(tenant_id=tenant_id)
    return queryset.none()


class TenantModelViewSet(CustomModelViewSet):
    """
    业务模型视图基类: 强制租户隔离(第一层硬过滤)
    - 超级管理员(tenant为null): 返回全部
    - 普通用户: 自动 filter(tenant=request.user.tenant)
    - 前端禁止传入 tenant, 由序列化器在 create 时注入
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if getattr(user, "is_superuser", False):
            return queryset
        tenant = getattr(user, "tenant", None)
        if tenant is None:
            return queryset.none()
        return queryset.filter(tenant=tenant)


class OwnerScopeViewSetMixin(TenantModelViewSet):
    """
    业务视图基类: 租户硬隔离(第一层) + 内部 owner/creator 数据范围(第二层, 配置驱动)
    数据范围详见 OwnerDataLevelFilter; 权限由 RoleMenuButtonPermission.data_range 按按钮配置。
    """

    # 用通用的 OwnerDataLevelFilter 替换系统默认 DataLevelPermissionMargeFilter(避免 dept_belong_id 冲突)
    extra_filter_class = [CoreModelFilterBankend, OwnerDataLevelFilter]
