# -*- coding: utf-8 -*-
"""
payment.py 核心逻辑单测: _mark_paid 幂等(webhook 重放防护) + signup 建租户幂等。
覆盖: 续费只顺延一次、无租户标记失败、signup 不重复建租户。
"""
import datetime

import pytest
from django.utils import timezone

from dvadmin.tenant.models import Tenant, TenantPayment
from dvadmin.system.models import Users, Role
from dvadmin.tenant.payment import _mark_paid


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(
        name="Test Co",
        tenant_code="T001",
        plan_type="paid",
        is_active=True,
        expire_time=timezone.now() + datetime.timedelta(days=30),
    )


@pytest.fixture
def renewal_payment(db, tenant):
    return TenantPayment.objects.create(
        tenant=tenant,
        purpose="renewal",
        charge_id="chrg_test_renewal",
        amount=150000,
        status="pending",
        extend_days=365,
    )


class TestMarkPaidRenewal:
    def test_marks_paid_and_extends(self, renewal_payment, tenant):
        old_expire = tenant.expire_time
        payment, changed = _mark_paid(renewal_payment)
        payment.refresh_from_db()
        tenant.refresh_from_db()
        assert payment.status == "paid"
        assert changed is True
        assert payment.paid_at is not None
        assert tenant.expire_time > old_expire
        # 顺延 = 365 天(从 max(旧到期, now) 起)
        expected = max(old_expire, timezone.now()) + datetime.timedelta(days=365)
        assert abs((tenant.expire_time - expected).total_seconds()) < 5

    def test_idempotent_no_double_extend(self, renewal_payment, tenant):
        _mark_paid(renewal_payment)
        tenant.refresh_from_db()
        expire_after_first = tenant.expire_time
        paid_at_first = renewal_payment.paid_at

        # 第二次调用(模拟 webhook 重放): 应直接返回 False, 不再顺延
        payment, changed = _mark_paid(renewal_payment)
        tenant.refresh_from_db()
        assert changed is False
        assert tenant.expire_time == expire_after_first
        assert payment.paid_at == paid_at_first

    def test_no_tenant_marks_failed(self, db):
        payment = TenantPayment.objects.create(
            tenant=None, purpose="renewal", charge_id="chrg_no_tenant",
            amount=100, status="pending", extend_days=365,
        )
        _, changed = _mark_paid(payment)
        payment.refresh_from_db()
        assert payment.status == "failed"
        assert changed is False


class TestMarkPaidSignup:
    def test_creates_tenant_once_idempotent(self, db, monkeypatch):
        from dvadmin.tenant import payment as payment_mod

        # 注册用户(尚无租户)
        user = Users.objects.create_user(username="signup@test.com", password="x", name="Signup User")

        # 绕过 org_chart 的菜单/按钮授权依赖, 仅返回真实的三个职级角色
        roles = {
            "manager": Role.objects.create(tenant=None, key="tenant_manager", name="经理", sort=1, status=True),
            "supervisor": Role.objects.create(tenant=None, key="tenant_supervisor", name="主管", sort=2, status=True),
            "staff": Role.objects.create(tenant=None, key="tenant_emp", name="员工", sort=3, status=True),
        }
        monkeypatch.setattr("dvadmin.tenant.org_chart.ensure_tenant_tier_roles", lambda t: roles)
        monkeypatch.setattr(payment_mod, "_gen_tenant_code", lambda: "7777")

        p = TenantPayment.objects.create(
            tenant=None, purpose="signup", signup_user=user,
            charge_id="chrg_signup", amount=150000, status="pending", extend_days=365,
        )

        payment, changed = _mark_paid(p)
        assert changed is True
        payment.refresh_from_db()
        user.refresh_from_db()
        assert payment.status == "paid"
        assert user.tenant_id is not None
        assert Tenant.objects.filter(id=user.tenant_id).exists()
        created_tenant_id = user.tenant_id

        # 重放: 应返回 False, 不再新建租户
        payment2, changed2 = _mark_paid(p)
        user.refresh_from_db()
        assert changed2 is False
        assert user.tenant_id == created_tenant_id
        assert Tenant.objects.filter(users=user).count() == 1
