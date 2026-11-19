# -*- coding: utf-8 -*-
import logging

from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from dvadmin.property.models import Property, ReminderRule
from dvadmin.property.tasks import sync_property_calendar, delete_property_calendar

logger = logging.getLogger(__name__)


def _safe_calendar_id(instance):
    """取该房源应使用的 Google Calendar id; 环境未装 googleapiclient 时降级为 None 并告警, 不阻断主流程"""
    try:
        from dvadmin.property.gcal_events import _calendar_id_for
        return _calendar_id_for(instance)
    except ImportError as e:
        logger.warning("googleapiclient 未安装, 跳过精确日历清理: %s", e)
        return None


def _enqueue_sync(instance):
    if instance.calendar_in:
        sync_property_calendar.delay(instance.id)
    else:
        # 关闭日历 -> 真正删除已写入的 Google 事件(需传 event_id + calendar_id)
        calendar_id = _safe_calendar_id(instance)
        delete_property_calendar.delay(instance.id, instance.event_id_01, instance.event_id_02, calendar_id)


@receiver(post_save, sender=Property)
def on_property_saved(sender, instance, created, **kwargs):
    # 同步任务自身回写 event_id_01/02 时的 save 不应再次入队, 避免信号循环
    update_fields = kwargs.get('update_fields')
    if update_fields is not None and set(update_fields) <= {'event_id_01', 'event_id_02'}:
        return
    # 确保事务提交后再异步同步日历(网络操作)
    transaction.on_commit(lambda: _enqueue_sync(instance))


@receiver(post_delete, sender=Property)
def on_property_deleted(sender, instance, **kwargs):
    calendar_id = _safe_calendar_id(instance)
    e1, e2 = instance.event_id_01, instance.event_id_02
    transaction.on_commit(
        lambda: delete_property_calendar.delay(instance.id, e1, e2, calendar_id)
    )


@receiver(post_save, sender=ReminderRule)
def on_rule_saved(sender, instance, created, **kwargs):
    # 规则自身回写 event_id 时的 save 不应再次入队, 避免信号循环
    update_fields = kwargs.get('update_fields')
    if update_fields is not None and set(update_fields) <= {'event_id'}:
        return
    # 规则变更 → 同步其房源日历(重写该房源全部事件, 含本规则)
    from dvadmin.property.tasks import sync_property_calendar
    transaction.on_commit(lambda: sync_property_calendar.delay(instance.property_id))


@receiver(post_delete, sender=ReminderRule)
def on_rule_deleted(sender, instance, **kwargs):
    # 删除规则 → 同步其房源日历(会移除该规则对应事件)
    from dvadmin.property.tasks import sync_property_calendar
    transaction.on_commit(lambda: sync_property_calendar.delay(instance.property_id))
