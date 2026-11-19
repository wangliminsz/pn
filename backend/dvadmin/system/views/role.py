# -*- coding: utf-8 -*-
from django.utils.translation import gettext as _
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q

from dvadmin.system.models import Role, Menu, MenuButton, Dept, Users
from dvadmin.system.views.dept import DeptSerializer
from dvadmin.system.views.menu import MenuSerializer
from dvadmin.system.views.menu_button import MenuButtonSerializer
from dvadmin.utils.crud_mixin import FastCrudMixin
from dvadmin.utils.field_permission import FieldPermissionMixin
from dvadmin.utils.json_response import SuccessResponse, DetailResponse, ErrorResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.permission import CustomPermission


class RoleSerializer(CustomModelSerializer):
    """
    角色-序列化器
    """
    users = serializers.SerializerMethodField()

    @staticmethod
    def get_users(instance):
        users = instance.users_set.exclude(id=1).values('id', 'name', 'dept__name')
        return users

    class Meta:
        model = Role
        fields = "__all__"
        read_only_fields = ["id"]


class RoleCreateUpdateSerializer(CustomModelSerializer):
    """
    角色管理 创建/更新时的列化器
    """
    menu = MenuSerializer(many=True, read_only=True)
    dept = DeptSerializer(many=True, read_only=True)
    permission = MenuButtonSerializer(many=True, read_only=True)
    key = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=50)

    def validate(self, attrs: dict):
        # 唯一性校验改为按租户范围(同租户内 name/key 不重复; 平台模板角色 tenant=null 全局唯一)
        request = self.context.get('request')
        tenant = None
        if request and not getattr(request.user, 'is_superuser', False):
            tenant = getattr(request.user, 'tenant', None)
        key = attrs.get('key')
        name = attrs.get('name')
        instance = self.instance
        base = Role.objects.all()
        if tenant is not None:
            base = base.filter(tenant=tenant)
        else:
            base = base.filter(tenant__isnull=True)
        if instance is not None:
            base = base.exclude(id=instance.id)
        if key and base.filter(key=key).exists():
            raise serializers.ValidationError(_("Permission key already exists in this tenant"))
        if name and base.filter(name=name).exists():
            raise serializers.ValidationError(_("Role name already exists in this tenant"))
        return super().validate(attrs)

    def create(self, validated_data):
        # 租户用户创建角色时注入其租户
        request = self.context.get('request')
        if request and not getattr(request.user, 'is_superuser', False):
            tenant = getattr(request.user, 'tenant', None)
            if tenant is not None:
                validated_data['tenant'] = tenant
        return super().create(validated_data)

    # def save(self, **kwargs):
    #     is_superuser = self.request.user.is_superuser
    #     if not is_superuser:
    #         self.validated_data.pop('admin')
    #     data = super().save(**kwargs)
    #     return data

    class Meta:
        model = Role
        fields = '__all__'


class MenuPermissionSerializer(CustomModelSerializer):
    """
    菜单的按钮权限
    """
    menuPermission = serializers.SerializerMethodField()

    def get_menuPermission(self, instance):
        is_superuser = self.request.user.is_superuser
        if is_superuser:
            queryset = MenuButton.objects.filter(menu__id=instance.id)
        else:
            menu_permission_id_list = self.request.user.role.values_list('permission', flat=True)
            queryset = MenuButton.objects.filter(id__in=menu_permission_id_list, menu__id=instance.id)
        serializer = MenuButtonSerializer(queryset, many=True, read_only=True)
        return serializer.data

    class Meta:
        model = Menu
        fields = ['id', 'parent', 'name', 'menuPermission']


class MenuButtonPermissionSerializer(CustomModelSerializer):
    """
    菜单和按钮权限
    """
    isCheck = serializers.SerializerMethodField()

    def get_isCheck(self, instance):
        is_superuser = self.request.user.is_superuser
        if is_superuser:
            return True
        else:
            return MenuButton.objects.filter(
                menu__id=instance.id,
                role__id__in=self.request.user.role.values_list('id', flat=True),
            ).exists()

    class Meta:
        model = Menu
        fields = '__all__'


class RoleViewSet(CustomModelViewSet, FastCrudMixin,FieldPermissionMixin):
    """
    角色管理接口
    list:查询
    create:新增
    update:修改
    retrieve:单例
    destroy:删除
    """
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    create_serializer_class = RoleCreateUpdateSerializer
    update_serializer_class = RoleCreateUpdateSerializer
    search_fields = ['name', 'key']

    def get_queryset(self):
        """超管看全部; 租户用户只看本租户的角色(含平台模板角色, 便于套用)"""
        qs = super().get_queryset()
        user = self.request.user
        if getattr(user, "is_superuser", False):
            return qs
        tenant = getattr(user, "tenant", None)
        if tenant is None:
            return qs.none()
        return qs.filter(Q(tenant=tenant) | Q(tenant__isnull=True))

    @action(methods=["GET"], detail=False, permission_classes=[IsAuthenticated])
    def options(self, request):
        """角色下拉(启用): 超管全部; 租户用户本租户角色+平台模板角色"""
        qs = Role.objects.filter(status=True)
        user = request.user
        if not getattr(user, "is_superuser", False):
            tenant = getattr(user, "tenant", None)
            if tenant is None:
                return SuccessResponse(data=[])
            qs = qs.filter(Q(tenant=tenant) | Q(tenant__isnull=True))
        data = qs.values("id", "name", "key")
        return SuccessResponse(data=data)

    @action(methods=['PUT'], detail=True, permission_classes=[IsAuthenticated])
    def set_role_users(self, request, pk):
        """
        设置 角色-用户
        :param request:
        :return:
        """
        data = request.data
        direction = data.get('direction')
        movedKeys = data.get('movedKeys')
        role = self.get_object()
        self._guard_role_tenant(role)
        # 只允许操作本租户下的用户
        user_qs = Users.objects.filter(id__in=movedKeys) if movedKeys else Users.objects.none()
        if not getattr(request.user, 'is_superuser', False):
            tenant = getattr(request.user, 'tenant', None)
            if tenant is not None:
                user_qs = user_qs.filter(tenant=tenant)
        if direction == "left":
            role.users_set.remove(*list(user_qs))
        else:
            role.users_set.add(*list(user_qs))
        serializer = RoleSerializer(role)
        return DetailResponse(data=serializer.data, msg=_("Update successful"))

    @action(methods=['GET'], detail=False, permission_classes=[IsAuthenticated, CustomPermission])
    def get_role_users(self, request):
        """
        获取角色已授权、未授权的用户
        已授权的用户:1
        未授权的用户:0
        """
        role_id = request.query_params.get('role_id', None)

        if not role_id:
            return ErrorResponse(msg=_("Please select a role"))

        # 非超管: 限本租户用户, 且 role 必须属于本租户(或平台模板角色)
        tenant = None
        if not getattr(request.user, 'is_superuser', False):
            tenant = getattr(request.user, 'tenant', None)
            if tenant is None:
                return ErrorResponse(msg=_("No tenant, no permission"))
            role = Role.objects.filter(id=role_id).filter(Q(tenant=tenant) | Q(tenant__isnull=True)).first()
            if role is None:
                return ErrorResponse(msg=_("No permission to operate this role"))

        if request.query_params.get('authorized', 0) == "1":
            queryset = Users.objects.filter(role__id=role_id).exclude(is_superuser=True)
        else:
            queryset = Users.objects.exclude(role__id=role_id).exclude(is_superuser=True)

        if tenant is not None:
            queryset = queryset.filter(tenant=tenant)

        if name := request.query_params.get('name', None):
            queryset = queryset.filter(name__icontains=name)

        if dept := request.query_params.get('dept', None):
            queryset = queryset.filter(dept=dept)

        page = self.paginate_queryset(queryset.values('id', 'name', 'dept__name'))
        if page is not None:
            return self.get_paginated_response(page)

        return SuccessResponse(data=page)

    @action(methods=['DELETE'], detail=True, permission_classes=[IsAuthenticated, CustomPermission])
    def remove_role_user(self, request, pk):
        """
        角色-删除用户
        """
        user_id = request.data.get('user_id', None)

        if not user_id:
            return ErrorResponse(msg=_("Please select a user"))

        role = self.get_object()
        self._guard_role_tenant(role, request)
        users = self._scope_users_to_tenant(Users.objects.filter(id__in=user_id), request)
        role.users_set.remove(*list(users))

        return SuccessResponse(msg=_("Delete successful"))

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated, CustomPermission])
    def add_role_users(self, request, pk):
        """
        角色-添加用户
        """
        users_id = request.data.get('users_id', None)

        if not users_id:
            return ErrorResponse(msg=_("Please select a user"))

        role = self.get_object()
        self._guard_role_tenant(role, request)
        users = self._scope_users_to_tenant(Users.objects.filter(id__in=users_id), request)
        role.users_set.add(*list(users))

        return DetailResponse(msg=_("Add successful"))

    def _guard_role_tenant(self, role, request):
        """非超管: 只能操作本租户角色(或平台模板角色), 否则拒绝"""
        if getattr(request.user, 'is_superuser', False):
            return
        tenant = getattr(request.user, 'tenant', None)
        if tenant is None:
            raise PermissionDenied(_("No tenant, no permission to operate this role"))
        if role.tenant_id is not None and role.tenant_id != tenant.id:
            raise PermissionDenied(_("No permission to operate this role"))

    def _scope_users_to_tenant(self, qs, request):
        """非超管: 用户集合限本租户"""
        if getattr(request.user, 'is_superuser', False):
            return qs
        tenant = getattr(request.user, 'tenant', None)
        if tenant is not None:
            qs = qs.filter(tenant=tenant)
        else:
            qs = qs.none()
        return qs
