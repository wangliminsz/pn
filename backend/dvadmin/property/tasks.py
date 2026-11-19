# -*- coding: utf-8 -*-
from celery import shared_task


@shared_task(bind=True, max_retries=3, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=120, retry_jitter=True)
def sync_property_calendar(self, property_id):
    from dvadmin.property.gcal_events import sync_property_events
    from dvadmin.property.models import Property
    prop = Property.objects.filter(id=property_id).first()
    if prop:
        sync_property_events(prop)


@shared_task(bind=True, max_retries=3, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=120, retry_jitter=True)
def delete_property_calendar(self, property_id, event_id_01=None, event_id_02=None, calendar_id=None):
    from dvadmin.property.gcal_events import delete_events_by_ids
    from dvadmin.property.models import Property, ReminderRule
    delete_events_by_ids(calendar_id, event_id_01, event_id_02)
    # 同时删除该房源下所有自定义规则事件
    rule_event_ids = list(ReminderRule.objects.filter(property_id=property_id)
                          .exclude(event_id__isnull=True).values_list('event_id', flat=True))
    for rid in rule_event_ids:
        delete_events_by_ids(calendar_id, rid)
    # 删除成功后清空残留 event_id, 避免重新开启时更新已不存在的事件
    ReminderRule.objects.filter(property_id=property_id).update(event_id=None)
    prop = Property.objects.filter(id=property_id).first()
    if prop and (prop.event_id_01 or prop.event_id_02):
        prop.event_id_01 = None
        prop.event_id_02 = None
        prop.save(update_fields=['event_id_01', 'event_id_02'])


@shared_task
def sync_all_property_calendars():
    from dvadmin.property.gcal_events import sync_property_events
    from dvadmin.property.models import Property
    qs = Property.objects.filter(calendar_in=True).exclude(rent_start=None).exclude(rent_end=None)
    for prop in qs:
        sync_property_events(prop)
