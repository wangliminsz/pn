# -*- coding: utf-8 -*-
from django.db.models import Count, Q
from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from dvadmin.property.models import Property, PropertyAttachment, PropertyChangeLog, ReminderRule
from dvadmin.property.serializers import (PropertyAttachmentSerializer, PropertySerializer,
                                          PropertyChangeLogSerializer, ReminderRuleSerializer,
                                          attachment_storage_rel_url)
from dvadmin.tenant.views import OwnerScopeViewSetMixin
from dvadmin.utils.cos_storage import delete_file, file_exists, save_file
from dvadmin.utils.filters import apply_owner_data_scope
from dvadmin.utils.json_response import DetailResponse, ErrorResponse, SuccessResponse


class PropertyViewSet(OwnerScopeViewSetMixin):
    """
    房源管理(强制租户隔离 + owner 数据范围)
    list:查询
    create:新增
    update:修改
    retrieve:单例
    destroy:删除
    """
    queryset = Property.objects.all()
    serializer_class = PropertySerializer

    def list(self, request, *args, **kwargs):
        """关键字搜索(名称/群ID/负责人) + 排序(name/line_bot/rent_amount/update_datetime, 前缀 - 降序)"""
        keyword = request.query_params.get("keyword")
        ordering = request.query_params.get("ordering", "")
        # 白名单排序字段, 防任意字段注入
        ALLOWED_ORDER = {
            "name": "name",
            "-name": "-name",
            "line_bot": "line_bot__name",
            "-line_bot": "-line_bot__name",
            "rent_amount": "rent_amount",
            "-rent_amount": "-rent_amount",
            "rent_end": "rent_end",
            "-rent_end": "-rent_end",
            "update_datetime": "-update_datetime",
            "-update_datetime": "-update_datetime",
        }
        order_by = ALLOWED_ORDER.get(ordering) or "-update_datetime"
        queryset = self.get_queryset().order_by(order_by).annotate(
            attachments_count=Count('attachments', distinct=True),
            reminder_rules_count=Count('reminder_rules', distinct=True),
        )
        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword)
                | Q(group_id__icontains=keyword)
                | Q(owner__name__icontains=keyword)
            )
        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, request=request)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True, request=request)
        return DetailResponse(data=serializer.data, msg=_("Fetched successfully"))

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data, msg=_("Fetched successfully"))

    @action(methods=["GET"], detail=True, permission_classes=[IsAuthenticated])
    def owner_logs(self, request, pk=None):
        """
        房源负责人变更记录
        可见规则: 能查看该房源(数据范围) 或 当前用户是被改派的原负责人(from_value 姓名匹配)
        """
        visible = self.get_queryset()  # 已叠加 owner 数据范围
        prop = Property.objects.filter(pk=pk).first()
        if prop is None or not visible.filter(pk=prop.id).exists():
            return ErrorResponse(msg=_("Property does not exist or no permission to view"))
        logs = PropertyChangeLog.objects.filter(property=prop).select_related("user", "property").order_by("-create_datetime")
        serializer = PropertyChangeLogSerializer(logs, many=True, request=request)
        return SuccessResponse(data=serializer.data, msg=_("Fetched successfully"))

    @action(methods=["GET"], detail=False, permission_classes=[IsAuthenticated])
    def change_logs(self, request):
        """
        变更记录列表(租户内全员可见)
        可见规则: 该房源当前可见(数据范围) OR 当前用户是被改派的原负责人(from_value == 当前用户姓名)
        - 超管: 全部租户(不过滤)
        - 普通用户: 仅本租户(房源归属租户已硬隔离)
        """
        from dvadmin.property.models import PropertyChangeLog
        qs = PropertyChangeLog.objects.all().select_related("property", "user", "property__tenant").order_by("-create_datetime")

        if not getattr(request.user, "is_superuser", False):
            visible = self.get_queryset()  # 本租户 + 数据范围
            qs = qs.filter(property__in=visible)
            # 追加: 自己是被改派的原负责人(name 或 username 任一匹配 from_value)
            me_names = {getattr(request.user, "name", None), getattr(request.user, "username", None)} - {None, ""}
            if me_names:
                qs = qs | PropertyChangeLog.objects.filter(from_value__in=me_names).select_related("property", "user", "property__tenant").order_by("-create_datetime")

        serializer = PropertyChangeLogSerializer(qs, many=True, request=request)
        return SuccessResponse(data=serializer.data, msg=_("Fetched successfully"))

    @action(methods=["POST"], detail=False, permission_classes=[IsAuthenticated])
    def property_import(self, request):
        """
        房源批量导入(参考 org-chart 的批量导入)
        - file(multipart) 或 rows(json) 二选一
        - dry_run=true(默认) 仅预览不落库; dry_run=false 正式导入
        - 模板列: 房间名称*/负责人/租金/付租周期/提醒日/起租日期/结束日期/备注
          (LineBot / Group ID 导入后手动填, 不入模板)
        """
        from dvadmin.property import import_service

        dry_run = str(request.data.get("dry_run", "true")).lower() in ("1", "true", "yes", "on")
        file_obj = request.FILES.get("file")
        rows = None
        if file_obj:
            try:
                rows = import_service.parse_file(file_obj)
            except Exception as e:
                return ErrorResponse(msg=_("File parse failed: {}").format(e))
        else:
            json_rows = request.data.get("rows")
            if json_rows is None:
                return ErrorResponse(msg=_("Please upload a CSV/Excel file, or provide rows"))
            try:
                rows = import_service.parse_inline_rows(json_rows)
            except Exception as e:
                return ErrorResponse(msg=_("Data parse failed: {}").format(e))

        if not rows:
            return ErrorResponse(msg=_("No valid data rows parsed"))

        if dry_run:
            return SuccessResponse(data=import_service.preview(request, rows), msg=_("Preview generated"))
        result = import_service.apply(request, rows)
        return SuccessResponse(data=result, msg=_("Import completed: {} properties added").format(result['created']))

    @action(methods=["GET"], detail=False, permission_classes=[IsAuthenticated])
    def export_csv(self, request):
        """
        导出房源列表为 CSV(带 UTF-8 BOM, Excel 打开中文不乱码)
        - 数据范围与列表一致: get_queryset() = 租户硬隔离 + owner 数据范围, 不会越权
        - keyword 可选, 同列表搜索(名称/群ID/负责人); 只导当前搜索结果
        - 表头语言随请求 Accept-Language(zh-cn=中文, 其它=英文), 无需 .po/.mo 翻译
        - 文件名: properties_YYYYMMDD_HHMMSS.csv
        """
        import csv
        import io
        from datetime import datetime as _dt
        from django.http import HttpResponse

        keyword = request.query_params.get("keyword")
        qs = self.get_queryset().order_by("name")
        if keyword:
            qs = qs.filter(
                Q(name__icontains=keyword)
                | Q(group_id__icontains=keyword)
                | Q(owner__name__icontains=keyword)
            )
        props = list(qs.select_related("owner", "line_bot"))

        if (request.META.get("HTTP_ACCEPT_LANGUAGE") or "").lower().split(",")[0].strip().startswith("zh"):
            headers = ["房间名称", "租金", "付租周期", "提醒日", "起租日期", "结束日期",
                       "群ID", "群人数", "Line Bot", "负责人", "写入Google日历", "年度提醒", "备注"]
            period_label = {"Monthly": "月付", "Quarterly": "季付", "HalfYear": "半年付", "Yearly": "年付"}
            yes, no = "是", "否"
        else:
            headers = ["Property Name", "Rent", "Pay Period", "Remind Day", "Start Date", "End Date",
                       "Group ID", "Group Size", "Line Bot", "Owner", "Google Calendar", "Annual Remind", "Remark"]
            period_label = {"Monthly": "Monthly", "Quarterly": "Quarterly", "HalfYear": "Half-year", "Yearly": "Yearly"}
            yes, no = "Yes", "No"

        def _yn(v):
            return yes if v else no

        buf = io.StringIO()
        buf.write("\ufeff")
        writer = csv.writer(buf)
        writer.writerow(headers)
        for p in props:
            writer.writerow([
                p.name or "",
                str(p.rent_amount) if p.rent_amount is not None else "",
                period_label.get(p.pay_period, p.pay_period or ""),
                str(p.remind_day) if p.remind_day else "",
                p.rent_start.strftime("%Y-%m-%d") if p.rent_start else "",
                p.rent_end.strftime("%Y-%m-%d") if p.rent_end else "",
                p.group_id or "",
                str(p.group_size) if p.group_size else "",
                p.line_bot.name if p.line_bot_id else "",
                p.owner.name if p.owner_id else "",
                _yn(p.calendar_in),
                _yn(p.if_annual_notify),
                p.memo or "",
            ])
        content = buf.getvalue()
        filename = "properties_{}.csv".format(_dt.now().strftime("%Y%m%d_%H%M%S"))
        response = HttpResponse(content, content_type="text/csv; charset=utf-8")
        response["Access-Control-Expose-Headers"] = "Content-Disposition"
        # 不带引号, 前端 downloadFile 按 `=` 截取即可拿到干净文件名
        response["Content-Disposition"] = "attachment; filename={}".format(filename)
        return response


class PropertyAttachmentViewSet(OwnerScopeViewSetMixin):
    """
    房源附件(合同/收据等): 租户隔离 + 房源 owner 数据范围
    list: 按 property_id 列出附件
    create: multipart 上传(fields: property_id, files[] 可多文件)
    destroy: 删除附件(连同磁盘文件)
    """
    queryset = PropertyAttachment.objects.all()
    serializer_class = PropertyAttachmentSerializer
    # 数据范围按"房源"配置判断, 不用本模型的 creator
    extra_filter_class = None
    permission_classes = [IsAuthenticated]
    def _visible_properties(self):
        if getattr(self.request.user, "is_superuser", False):
            return Property.objects.all()
        # 复用房源列表的数据范围配置(经理=全部/主管=本部门及以下/员工=仅本人)
        return apply_owner_data_scope(
            self.request, Property.objects.filter(tenant=getattr(self.request.user, "tenant", None)),
            api="/api/property/property/", method="GET")

    def get_queryset(self):
        qs = super().get_queryset()
        prop_id = self.request.query_params.get("property_id")
        visible = self._visible_properties()
        if prop_id:
            return qs.filter(property_id=prop_id, property__in=visible)
        return qs.filter(property__in=visible)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().order_by("-create_datetime")
        serializer = self.get_serializer(queryset, many=True, request=request)
        return SuccessResponse(data=serializer.data, msg=_("Fetched successfully"))

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data, msg=_("Fetched successfully"))

    def create(self, request, *args, **kwargs):
        prop_id = request.data.get("property_id")
        if not prop_id:
            return ErrorResponse(msg=_("Missing property_id"))
        prop = Property.objects.filter(pk=prop_id, tenant_id=getattr(request.user.tenant, "id", None)).first()
        visible = self._visible_properties()
        if prop is None or not visible.filter(pk=prop.id).exists():
            return ErrorResponse(msg=_("This property is not within your data scope"))
        files = request.FILES.getlist("files")
        if not files:
            return ErrorResponse(msg=_("No file received"))
        created = []
        for f in files:
            fname = f.name
            rel = attachment_storage_rel_url(prop.tenant_id, prop.id, fname)
            # 重名则追加序号
            if file_exists(rel):
                stem, dot, ext = fname.rpartition(".")
                i = 1
                while file_exists(rel):
                    new_name = f"{stem}_{i}{dot}{ext}" if dot else f"{stem}_{i}"
                    rel = attachment_storage_rel_url(prop.tenant_id, prop.id, new_name)
                    fname = new_name
                    i += 1
            data = b"".join(chunk for chunk in f.chunks())
            save_file(rel, data)
            att = PropertyAttachment.objects.create(
                tenant=prop.tenant, property=prop, name=fname, path=rel,
                size=f.size, mime=f.content_type or "", creator=request.user,
            )
            created.append(self.get_serializer(att, request=request).data)
        return SuccessResponse(data=created, msg=_("Uploaded {} files").format(len(created)))

    def destroy(self, request, *args, **kwargs):
        att = self.get_object()  # 通过 get_queryset 已限定数据范围
        delete_file(att.path)
        att.delete()
        return DetailResponse(data=[], msg=_("Delete successful"))


class ReminderRuleViewSet(OwnerScopeViewSetMixin):
    """
    自定义提醒规则(水电/自定义): 租户隔离 + 房源 owner 数据范围
    归属房源同一租户硬隔离; 数据范围复用房源列表配置
    """
    queryset = ReminderRule.objects.all()
    serializer_class = ReminderRuleSerializer
    # 数据范围按"房源"配置判断
    extra_filter_class = None
    permission_classes = [IsAuthenticated]

    def _visible_properties(self):
        if getattr(self.request.user, "is_superuser", False):
            return Property.objects.all()
        return apply_owner_data_scope(
            self.request, Property.objects.filter(tenant=getattr(self.request.user, "tenant", None)),
            api="/api/property/property/", method="GET")

    def get_queryset(self):
        qs = super().get_queryset()
        prop_id = self.request.query_params.get("property_id")
        visible = self._visible_properties()
        if prop_id:
            return qs.filter(property_id=prop_id, property__in=visible).select_related("property")
        return qs.filter(property__in=visible).select_related("property")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().order_by("id")
        serializer = self.get_serializer(queryset, many=True, request=request)
        return SuccessResponse(data=serializer.data, msg=_("Fetched successfully"))

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data, msg=_("Fetched successfully"))

    def create(self, request, *args, **kwargs):
        prop_id = request.data.get("property")
        if not prop_id:
            return ErrorResponse(msg=_("Missing property"))
        visible = self._visible_properties()
        prop = visible.filter(pk=prop_id).first()
        if prop is None:
            return ErrorResponse(msg=_("Property does not exist or is not within your data scope"))
        data = request.data.copy()
        data["property"] = prop.id
        if "tenant" not in data or not data["tenant"]:
            data["tenant"] = prop.tenant_id
        serializer = self.get_serializer(data=data, request=request)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(data=serializer.data, msg=_("Create successful"))

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.pop("partial", False)
        data = request.data.copy()
        if "tenant" not in data or not data["tenant"]:
            data["tenant"] = instance.property.tenant_id
        serializer = self.get_serializer(instance, data=data, request=request, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return DetailResponse(data=serializer.data, msg=_("Update successful"))
