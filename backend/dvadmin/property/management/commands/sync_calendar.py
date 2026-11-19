# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '手动同步所有开启日历的房源到Google Calendar(可不用celery直接跑)'

    def add_arguments(self, parser):
        parser.add_argument('--property_id', type=int, default=None, help='只同步指定房源')
        parser.add_argument('--tenant_id', type=int, default=None, help='只同步指定租户下的房源')

    def handle(self, *args, **options):
        from dvadmin.property.gcal_events import sync_property_events
        from dvadmin.property.models import Property

        qs = Property.objects.filter(calendar_in=True).exclude(rent_start=None).exclude(rent_end=None)
        if options.get('tenant_id'):
            qs = qs.filter(tenant_id=options['tenant_id'])
        if options.get('property_id'):
            qs = qs.filter(id=options['property_id'])

        ok = fail = 0
        for prop in qs:
            o, m = sync_property_events(prop)
            self.stdout.write(f'[{prop.name}] {m}')
            if o:
                ok += 1
            else:
                fail += 1
        self.stdout.write(self.style.SUCCESS(f'同步完成 ok={ok} fail={fail}'))
