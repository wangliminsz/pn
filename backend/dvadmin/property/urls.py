# -*- coding: utf-8 -*-
from django.urls import path
from rest_framework import routers

from dvadmin.property.ai_views import AIConfigView, AIAssistView
from dvadmin.property.views import PropertyAttachmentViewSet, PropertyViewSet, ReminderRuleViewSet

router = routers.SimpleRouter()
router.register(r'property', PropertyViewSet)
router.register(r'attachment', PropertyAttachmentViewSet, basename='property-attachment')
router.register(r'reminder_rule', ReminderRuleViewSet, basename='reminder-rule')

urlpatterns = []
urlpatterns += router.urls

urlpatterns += [
    path('ai/assist/', AIAssistView.as_view(), name='property-ai-assist'),
    path('ai/config/', AIConfigView.as_view(), name='property-ai-config'),
]