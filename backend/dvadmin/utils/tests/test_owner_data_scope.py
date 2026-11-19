# -*- coding: utf-8 -*-
"""
数据范围过滤器 apply_owner_data_scope 单测。
覆盖: 超管放行、data_range=0(仅本人, owner空回退creator)、data_range=3(本租户全部)、_ownable_q 兜底。
"""
from types import SimpleNamespace

import pytest
from django.db.models import Q

from dvadmin.tenant.models import Tenant
from dvadmin.system.models import Users, Role, Menu, MenuButton, RoleMenuButtonPermission
from dvadmin.property.models import Property
from dvadmin.utils.filters import apply_owner_data_scope, _ownable_q


def _request(user, path="/api/property/property/", method="GET"):
    r = SimpleNamespace(user=user, path=path, method=method, parser_context={})
    return r


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name="Scope Co", tenant_code="S001", plan_type="paid", is_active=True)


@pytest.fixture
def users(db):
    owner = Users.objects.create_user(username="scope_owner", password="x", name="Owner")
    other = Users.objects.create_user(username="scope_other", password="x", name="Other")
    return owner, other


@pytest.fixture
def role_with_range(db):
    role = Role.objects.create(key="scope_role", name="scope role", status=True)
    menu = Menu.objects.create(name="scope menu", web_path="/property")
    btn = MenuButton.objects.create(name="scope_btn", value="scope_btn", api="/api/property/property/", method=0, menu=menu)
    return role, btn


class TestApplyOwnerDataScope:
    def test_superuser_passthrough(self, db, tenant):
        # create_superuser 依赖「管理员」角色, 直接建 is_superuser=True 用户即可
        su = Users.objects.create(username="scope_su", name="SU", is_superuser=True, is_staff=True)
        qs = Property.objects.filter(tenant=tenant)
        out = apply_owner_data_scope(_request(su), qs)
        # 超管直接返回原 queryset(未叠加 owner 过滤)
        assert str(out.query) == str(qs.query)

    def test_data_range_0_own_only(self, db, tenant, users, role_with_range):
        owner, other = users
        role, btn = role_with_range
        owner.role.add(role)
        RoleMenuButtonPermission.objects.create(role=role, menu_button=btn, data_range=0)

        mine = Property.objects.create(tenant=tenant, name="mine", owner=owner)
        Property.objects.create(tenant=tenant, name="theirs", owner=other)
        # owner 为空、creator=owner -> 也应可见(隐形房源兜底)
        fallback = Property.objects.create(tenant=tenant, name="fallback", owner=None, creator=owner)

        qs = Property.objects.filter(tenant=tenant)
        out = apply_owner_data_scope(_request(owner), qs)
        ids = set(out.values_list("id", flat=True))
        assert ids == {mine.id, fallback.id}

    def test_data_range_3_all_tenant(self, db, tenant, users, role_with_range):
        owner, other = users
        role, btn = role_with_range
        owner.role.add(role)
        RoleMenuButtonPermission.objects.create(role=role, menu_button=btn, data_range=3)

        Property.objects.create(tenant=tenant, name="a", owner=owner)
        Property.objects.create(tenant=tenant, name="b", owner=other)

        out = apply_owner_data_scope(_request(owner), Property.objects.filter(tenant=tenant))
        assert out.count() == 2

    def test_no_menu_button_returns_unfiltered(self, db, tenant, users):
        owner, _ = users
        Property.objects.create(tenant=tenant, name="a", owner=owner)
        # 无匹配按钮 -> 不过滤(返回原 queryset)
        out = apply_owner_data_scope(_request(owner), Property.objects.filter(tenant=tenant))
        assert out.count() == 1


class TestOwnableQ:
    def test_owner_field_prefers_owner_with_creator_fallback(self, db, users):
        owner, other = users
        q = _ownable_q("owner", has_owner=True, has_creator=True, user=owner)
        # owner=自己 或 (owner空 且 creator=自己)
        expected = Q(owner=owner) | Q(owner__isnull=True, creator=owner)
        assert str(q) == str(expected)

    def test_creator_only(self, db, users):
        owner, _ = users
        q = _ownable_q("creator", has_owner=False, has_creator=True, user=owner)
        assert str(q) == str(Q(creator=owner))
