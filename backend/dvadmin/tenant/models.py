# -*- coding: utf-8 -*-
from django.db import models
from django.utils.translation import gettext_lazy as _

from dvadmin.utils.models import CoreModel


class Tenant(CoreModel):
    """
    租户(一家中介/物业公司)
    逻辑多租户的单库单表方案: 所有业务数据通过 tenant 字段做硬隔离
    """
    PLAN_TYPE_CHOICES = (
        ('trial', '试用客户'),
        ('paid', '正式客户'),
    )
    name = models.CharField(max_length=128, verbose_name=_("公司名称"), help_text="公司名称")
    tenant_code = models.CharField(max_length=64, unique=True, verbose_name=_("租户标识"),
                                   help_text="唯一字符串标识")
    contact_name = models.CharField(max_length=64, null=True, blank=True, verbose_name=_("联系人"),
                                    help_text="联系人")
    contact_phone = models.CharField(max_length=32, null=True, blank=True, verbose_name=_("联系电话"),
                                     help_text="联系电话")
    google_calendar_id = models.CharField(max_length=255, null=True, blank=True,
                                          verbose_name=_("Google日历ID(公司默认)"),
                                          help_text="共享给系统服务账号的Google日历ID")
    sign_name = models.CharField(max_length=64, null=True, blank=True,
                                 verbose_name=_("落款签名"),
                                 help_text="提醒消息末尾的公司名, 为空用全局 LINE_SIGNATURE")
    plan_type = models.CharField(max_length=32, choices=PLAN_TYPE_CHOICES, default='trial',
                                 verbose_name=_("客户类型"), help_text="试用客户/正式客户")
    is_active = models.BooleanField(default=True, verbose_name=_("是否启用"), help_text="是否启用该租户")
    expire_time = models.DateTimeField(null=True, blank=True, verbose_name=_("服务到期时间"),
                                       help_text="服务到期时间")
    referral_code = models.CharField(max_length=16, unique=True, null=True, blank=True,
                                     verbose_name=_("推荐码"), help_text="本租户的专属推荐码(新用户注册时填写, 用于归属推荐)")
    referrer_tenant = models.ForeignKey(
        to='tenant.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("推荐来源租户"),
        help_text="该租户是通过哪个租户的推荐码注册付费的",
        db_constraint=False,
        related_name='referred_tenants',
    )
    remark = models.TextField(null=True, blank=True, verbose_name=_("备注"), help_text="备注")

    class Meta:
        db_table = "dvadmin_tenant"
        verbose_name = "租户"
        verbose_name_plural = verbose_name
        ordering = ["name", "-create_datetime"]

    def __str__(self):
        return self.name

    @classmethod
    def make_referral_code(cls, size=6):
        """生成唯一推荐码(字母+数字, 大写, 避免易混淆字符)"""
        import random
        import string
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 去掉 0/O/1/I/L
        while True:
            code = "".join(random.choice(alphabet) for _ in range(size))
            if not cls.objects.filter(referral_code__iexact=code).exists():
                return code


class TenantModel(CoreModel):
    """
    所有业务模型的抽象基类, 自动带上 tenant 外键
    所有业务表必须继承本基类, 实现租户隔离
    """
    tenant = models.ForeignKey(
        to='tenant.Tenant',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("所属租户"),
        help_text="所属租户",
        db_constraint=False,
    )

    class Meta:
        abstract = True


class TenantPayment(CoreModel):
    """
    租户续费支付记录(Omise PromptPay)
    - 每次进入支付页可发起一笔 charge, 完成后到期时间+1年
    - charge_id 来自 Omise(dev 模式为本地伪 ID)
    """
    STATUS_CHOICES = (
        ('pending', '待支付'),
        ('paid', '已支付'),
        ('failed', '失败'),
    )
    PURPOSE_CHOICES = (
        ('renewal', '老租户续费'),
        ('signup', '新注册建租户'),
    )
    tenant = models.ForeignKey(
        to='tenant.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("所属租户"),
        help_text="所属租户(signup 订单在付费前为空)",
        db_constraint=False,
        related_name="payments",
    )
    purpose = models.CharField(max_length=16, choices=PURPOSE_CHOICES, default='renewal',
                               verbose_name=_("支付用途"), help_text="renewal=老租户续费; signup=新注册建租户")
    signup_user = models.ForeignKey(
        to='system.Users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("注册用户"),
        help_text="signup 订单对应的注册用户(付费成功后成为新租户经理)",
        db_constraint=False,
        related_name="signup_payments",
    )
    charge_id = models.CharField(max_length=128, unique=True, verbose_name=_("Omise Charge ID"),
                                 help_text="Omise Charge ID(dev 模式为本地伪 ID)")
    amount = models.BigIntegerField(default=0, verbose_name=_("支付金额(泰铢, 最小单位 satang)"),
                                    help_text="支付金额, 单位=泰铢的1/100")
    currency = models.CharField(max_length=8, default='thb', verbose_name=_("币种"))
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending',
                              verbose_name=_("支付状态"))
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name=_("支付时间"))
    extend_days = models.IntegerField(default=365, verbose_name=_("续费天数"),
                                      help_text="支付成功后到期时间顺延天数")

    class Meta:
        db_table = "dvadmin_tenant_payment"
        verbose_name = "租户续费支付记录"
        verbose_name_plural = verbose_name
        ordering = ("-create_datetime",)

    def __str__(self):
        return f"{self.tenant_id}:{self.charge_id}:{self.status}"
