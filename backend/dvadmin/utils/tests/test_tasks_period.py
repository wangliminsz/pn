# -*- coding: utf-8 -*-
"""
tasks.py 周期/提醒日逻辑纯函数单测(不依赖 DB)。
覆盖: 付租周期月份判定、提醒日命中(月末/闰年)、规则下次日期、租期范围、文案填充。
"""
import calendar
from datetime import date, datetime
from types import SimpleNamespace

from dvadmin.notify.tasks import (
    _period_months,
    _is_pay_period_month,
    _pay_remind_day_hit,
    _effective_remind_day,
    _remind_day_hit,
    _within_rent_range,
    _rule_next_date,
    _fill_props,
)


def _prop(**kw):
    defaults = dict(name="Room A", pay_period="Monthly", remind_day=1,
                    rent_start=None, rent_end=None)
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _rule(**kw):
    defaults = dict(period="Monthly", day=1, enabled=True)
    defaults.update(kw)
    r = SimpleNamespace(**defaults)
    r.period_months = lambda: _period_months(r.period)
    return r


class TestPeriodMonths:
    def test_mapping(self):
        assert _period_months("Monthly") == 1
        assert _period_months("Quarterly") == 3
        assert _period_months("HalfYear") == 6
        assert _period_months("Yearly") == 12

    def test_unknown_falls_back_monthly(self):
        assert _period_months("Nope") == 1


class TestIsPayPeriodMonth:
    def test_monthly_always_true(self):
        p = _prop(pay_period="Monthly")
        assert _is_pay_period_month(datetime(2026, 3, 1), p) is True

    def test_quarterly_based_on_rent_start(self):
        # rent_start = 2026-01 => 1,4,7,10 月命中
        p = _prop(pay_period="Quarterly", rent_start=date(2026, 1, 15))
        assert _is_pay_period_month(datetime(2026, 1, 1), p) is True
        assert _is_pay_period_month(datetime(2026, 4, 1), p) is True
        assert _is_pay_period_month(datetime(2026, 2, 1), p) is False
        assert _is_pay_period_month(datetime(2026, 3, 1), p) is False

    def test_yearly_same_month_only(self):
        p = _prop(pay_period="Yearly", rent_start=date(2026, 5, 10))
        assert _is_pay_period_month(datetime(2026, 5, 1), p) is True
        assert _is_pay_period_month(datetime(2026, 6, 1), p) is False

    def test_no_rent_start_uses_now_month(self):
        p = _prop(pay_period="Quarterly", rent_start=None)
        # 无 rent_start 时 base_month = now.month, 恒命中(0 % 3 == 0)
        assert _is_pay_period_month(datetime(2026, 7, 1), p) is True


class TestPayRemindDayHit:
    def test_exact_day(self):
        p = _prop(remind_day=15)
        assert _pay_remind_day_hit(datetime(2026, 3, 15), p) is True
        assert _pay_remind_day_hit(datetime(2026, 3, 14), p) is False

    def test_month_end_clamp_february(self):
        # remind_day=31 在 2 月(28天)应取 28
        p = _prop(remind_day=31)
        assert _pay_remind_day_hit(datetime(2026, 2, 28), p) is True
        assert _pay_remind_day_hit(datetime(2026, 2, 27), p) is False

    def test_leap_year_february(self):
        # 2024 闰年 2 月有 29 天, remind_day=30 -> 取 29
        p = _prop(remind_day=30)
        assert _pay_remind_day_hit(datetime(2024, 2, 29), p) is True

    def test_non_leap_february_30_clamps_to_28(self):
        p = _prop(remind_day=30)
        assert _pay_remind_day_hit(datetime(2026, 2, 28), p) is True


class TestEffectiveRemindDay:
    def test_clamp(self):
        assert _effective_remind_day(2026, 2, 31) == 28
        assert _effective_remind_day(2024, 2, 30) == 29
        assert _effective_remind_day(2026, 4, 15) == 15

    def test_remind_day_hit_wrapper(self):
        assert _remind_day_hit(datetime(2026, 2, 28), 30) is True
        assert _remind_day_hit(datetime(2026, 2, 28), 28) is True
        assert _remind_day_hit(datetime(2026, 2, 28), None) is False
        assert _remind_day_hit(datetime(2026, 2, 28), 0) is False


class TestWithinRentRange:
    def test_no_bounds(self):
        assert _within_rent_range(_prop(), datetime(2026, 1, 1)) is True

    def test_start_only(self):
        p = _prop(rent_start=date(2026, 3, 1))
        assert _within_rent_range(p, datetime(2026, 2, 28)) is False
        assert _within_rent_range(p, datetime(2026, 3, 1)) is True

    def test_end_only(self):
        p = _prop(rent_end=date(2026, 12, 31))
        assert _within_rent_range(p, datetime(2027, 1, 1)) is False
        assert _within_rent_range(p, datetime(2026, 12, 31)) is True


class TestRuleNextDate:
    def test_monthly_rule_next_day(self):
        p = _prop(rent_start=date(2026, 1, 1), pay_period="Monthly")
        r = _rule(period="Monthly", day=10)
        assert _rule_next_date(p, r, date(2026, 3, 1)) == date(2026, 3, 10)

    def test_monthly_rule_already_past_today_rolls_next_month(self):
        p = _prop(rent_start=date(2026, 1, 1))
        r = _rule(period="Monthly", day=10)
        assert _rule_next_date(p, r, date(2026, 3, 15)) == date(2026, 4, 10)

    def test_quarterly_rule_respects_base_month(self):
        p = _prop(rent_start=date(2026, 1, 1))
        r = _rule(period="Quarterly", day=5)
        # 基准月 1 => 命中 1,4,7,10 月
        assert _rule_next_date(p, r, date(2026, 3, 1)) == date(2026, 4, 5)

    def test_rule_day_clamps_month_end(self):
        p = _prop(rent_start=date(2026, 1, 1))
        r = _rule(period="Monthly", day=31)
        assert _rule_next_date(p, r, date(2026, 2, 1)) == date(2026, 2, 28)


class TestFillProps:
    def test_replace_and_newline(self):
        text = "Hi {name}, rent {rent}\nthanks\n{sign}"
        out = _fill_props(text, name="Room", rent="1000", sign="Co")
        assert "Room" in out and "1000" in out
        assert "\n" in out  # 字面量 \n 被替换
        # 未提供的变量置空
        assert "thanks" in out

    def test_unprovided_var_remains_literal(self):
        # 只替换传入的 kwargs; 未提供的占位符原样保留(调用方按需传参)
        assert _fill_props("x{foo}y", bar="1") == "x{foo}y"

    def test_empty_value_replaced_with_empty(self):
        assert _fill_props("a{foo}b", foo="") == "ab"
