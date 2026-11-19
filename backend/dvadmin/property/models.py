# -*- coding: utf-8 -*-
from django.db import models
from django.utils.translation import gettext_lazy as _

from dvadmin.tenant.models import TenantModel


class Property(TenantModel):
    """
    房源(一间出租房 = 一个 Line 群)
    字段含义参考 refer/ant_notify/thai_notify.csv
    """
    PAY_PERIOD_CHOICES = (
        ('Monthly', '每月'),
        ('Quarterly', '每季度'),
        ('HalfYear', '每半年'),
        ('Yearly', '每年'),
    )

    # 付租周期 → 提醒间隔月数(Quarterly=3, HalfYear=6, Yearly=12; Monthly=1)
    PAY_PERIOD_MONTHS = {
        'Monthly': 1,
        'Quarterly': 3,
        'HalfYear': 6,
        'Yearly': 12,
    }

    name = models.CharField(max_length=128, verbose_name=_("房间名称"), help_text="房间名称")
    rent_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                      verbose_name=_("租金金额"), help_text="租金金额")
    remind_day = models.IntegerField(default=1, verbose_name=_("提醒日(每月第几天)"),
                                     help_text="每月第几天提醒(1-31)")
    pay_period = models.CharField(max_length=32, choices=PAY_PERIOD_CHOICES, default='Monthly',
                                  verbose_name=_("付租周期"), help_text="每月/每季度/每半年/每年")
    rent_start = models.DateField(null=True, blank=True, verbose_name=_("起租日期"), help_text="起租日期")
    rent_end = models.DateField(null=True, blank=True, verbose_name=_("结束日期"), help_text="结束日期")
    group_id = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("Line群ID"),
                                help_text="该房间对应的Line群ID")
    owner = models.ForeignKey(
        to='system.Users',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("负责人"),
        help_text="负责该房源的人(缺省=创建人; 可指派他人)",
        db_constraint=False,
        related_name="owned_properties",
    )
    line_bot = models.ForeignKey(
        to='notify.LineBot',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("LineBot"),
        help_text="该房源(群)用哪个Bot发送; 为空用租户名下bot, 归属必须与本房源租户一致",
        db_constraint=False,
    )
    group_size = models.IntegerField(default=0, verbose_name=_("群人数"),
                                     help_text="该Line群的人数用于估算消耗; 填0表示自动(优先LINE成员API,取不到缺省5)")
    calendar_in = models.BooleanField(default=True, verbose_name=_("写入Google日历"),
                                      help_text="是否写入Google日历")
    if_annual_notify = models.BooleanField(default=False, verbose_name=_("年度提醒"),
                                           help_text="是否开启年度提醒")
    memo = models.CharField(max_length=512, null=True, blank=True, verbose_name=_("备注"),
                            help_text="备注(如收款账户等)")
    custom_pay_message = models.TextField(null=True, blank=True, verbose_name=_("自定义付租消息"),
                                          help_text="留空使用系统模板; 支持变量 {name}{rent}{date}{sign}")
    custom_end_message = models.TextField(null=True, blank=True, verbose_name=_("自定义到期消息"),
                                          help_text="留空使用系统模板; 支持变量 {name}{rent_end}{sign}")
    # Google Calendar 事件ID: event_id_01 = 周期付租提醒(循环), event_id_02 = 结束日期事件
    event_id_01 = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("日历事件ID01"),
                                   help_text="周期付租提醒事件ID")
    event_id_02 = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("日历事件ID02"),
                                   help_text="结束日期事件ID")
    calendar_id = models.CharField(max_length=512, null=True, blank=True, verbose_name=_("事件所在日历ID"),
                                   help_text="当前事件写入的 Google 日历ID(用于换日历/清空时定位旧事件并迁移)")

    class Meta:
        db_table = "dvadmin_property"
        verbose_name = "房源"
        verbose_name_plural = verbose_name
        ordering = ["-update_datetime"]

    def __str__(self):
        return self.name


class PropertyChangeLog(TenantModel):
    """
    房源变更记录(目前只记负责人 owner 变更; 与房源同租户硬隔离)
    谁有权限看该房源, 谁就能看它的变更记录(复用房源数据范围)
    """
    property = models.ForeignKey(
        to=Property,
        on_delete=models.CASCADE,
        related_name="change_logs",
        db_constraint=False,
        verbose_name=_("房源"),
    )
    user = models.ForeignKey(
        to='system.Users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("操作人"),
        db_constraint=False,
        related_name="property_change_logs",
    )
    field = models.CharField(max_length=64, default="owner", verbose_name=_("变更字段"))
    from_value = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("变更前"))
    to_value = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("变更后"))

    class Meta:
        db_table = "dvadmin_property_change_log"
        verbose_name = "房源变更记录"
        verbose_name_plural = verbose_name
        ordering = ["-create_datetime"]

    def __str__(self):
        return f"ChangeLog({self.property_id}) {self.field}"


class PropertyAttachment(TenantModel):
    """
    房源附件(合同/收据/图等)
    文件落盘: MEDIA_ROOT/{tenant_id}/property_files/{property_id}/{filename}
    """
    property = models.ForeignKey(
        to=Property,
        on_delete=models.CASCADE,
        related_name="attachments",
        db_constraint=False,
        verbose_name=_("房源"),
    )
    name = models.CharField(max_length=255, verbose_name=_("文件名"))
    path = models.CharField(max_length=512, verbose_name=_("存储相对路径"))
    size = models.BigIntegerField(default=0, verbose_name=_("字节数"))
    mime = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("MIME"))

    class Meta:
        db_table = "dvadmin_property_attachment"
        verbose_name = "房源附件"
        verbose_name_plural = verbose_name
        ordering = ["-create_datetime"]

    def __str__(self):
        return self.name


class ReminderRule(TenantModel):
    """
    自定义周期提醒规则(一房源 → N 条)
    独立于「付租提醒/到期提醒」: 水电费、物业费、续租提醒等
    - type: 规则类型(utility=水电, custom=自定义)
    - period: 每月/每季度/每半年/每年(与付租周期一致)
    - day: 每月第几天提醒(与付租提醒日相同语义, 超当月天数取月末)
    - template: 自定义消息模板(留空=系统预设模板); 支持 {name}{amount}{date}{sign} 及规则额外变量
    - extra_vars: 额外变量 KV(JSON), 模板可引用 {key}; 如 {"电费": "850", "电费单位": "泰铢"}
    - enabled: 开关
    """
    TYPE_CHOICES = (
        ('utility', '水电提醒'),
        ('custom', '自定义提醒'),
    )
    PERIOD_CHOICES = (
        ('Monthly', '每月'),
        ('Quarterly', '每季度'),
        ('HalfYear', '每半年'),
        ('Yearly', '每年'),
    )
    property = models.ForeignKey(
        to=Property,
        on_delete=models.CASCADE,
        related_name="reminder_rules",
        db_constraint=False,
        verbose_name=_("房源"),
    )
    type = models.CharField(max_length=16, choices=TYPE_CHOICES, default='custom',
                            verbose_name=_("规则类型"), help_text="utility=水电, custom=自定义")
    period = models.CharField(max_length=16, choices=PERIOD_CHOICES, default='Monthly',
                              verbose_name=_("提醒周期"), help_text="每月/每季度/每半年/每年")
    day = models.IntegerField(default=1, verbose_name=_("每月第几天提醒"),
                              help_text="1-31, 超当月天数取月末(与付租提醒一致)")
    template = models.TextField(null=True, blank=True, verbose_name=_("自定义消息模板"),
                                help_text="留空=系统预设模板; 支持 {name}{amount}{date}{sign} 及额外变量 {xxx}")
    extra_vars = models.JSONField(null=True, blank=True, default=dict, verbose_name=_("额外变量"),
                                  help_text="模板可引用的自定义变量, 如 {\"电费\": \"850\", \"单位\": \"泰铢\"}")
    enabled = models.BooleanField(default=True, verbose_name=_("启用"), help_text="是否启用该规则")
    event_id = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("Google日历事件ID"),
                                help_text="该规则写入的 Google 日历事件ID")

    class Meta:
        db_table = "dvadmin_reminder_rule"
        verbose_name = "自定义提醒规则"
        verbose_name_plural = verbose_name
        ordering = ["id"]

    def __str__(self):
        return f"Rule({self.property_id}) {self.type} {self.period} {self.day}"

    def period_months(self):
        # 注意: 字段名 property 会遮蔽内建 property, 故用普通方法
        return Property.PAY_PERIOD_MONTHS.get(self.period, 1)
