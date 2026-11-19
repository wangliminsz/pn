# -*- coding: utf-8 -*-
from django.urls import path
from rest_framework import routers

from dvadmin.notify.views import (DeeplKeyViewSet, LineBotViewSet, MessageLogViewSet,
                                  NotifyScheduleView, TodayMessagesView)
from dvadmin.notify.groupdoc import GroupDocViewSet

router = routers.SimpleRouter()
router.register(r'linebot', LineBotViewSet)
router.register(r'messagelog', MessageLogViewSet)
router.register(r'groupdoc', GroupDocViewSet, basename='groupdoc')
router.register(r'deeplkey', DeeplKeyViewSet)

urlpatterns = [
    path('schedule/', NotifyScheduleView.as_view()),
    path('today/', TodayMessagesView.as_view()),
]
urlpatterns += router.urls
