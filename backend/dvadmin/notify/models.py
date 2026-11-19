# -*- coding: utf-8 -*-
from django.db import models
from django.utils.translation import gettext_lazy as _

from dvadmin.utils.models import CoreModel


class LineBot(CoreModel):
    """
    LINE Bot 凭证(多 Bot)
    每个 Channel 各自有独立的 500 条免费消息额度, 互不共享
    每个 bot 只归属一个租户(tenant); tenant=null 表示平台默认/演示 bot
    """
    tenant = models.ForeignKey(
        to='tenant.Tenant',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("归属租户"),
        help_text="该Bot属于哪个租户; 空为平台默认/演示Bot",
        db_constraint=False,
    )
    name = models.CharField(max_length=64, verbose_name=_("Bot名称"), help_text="如 proNotify_01")
    bot_code = models.CharField(max_length=64, unique=True, verbose_name=_("Bot标识"),
                                help_text="唯一字符串标识, 如 pro_bot_01")
    channel_id = models.CharField(max_length=64, null=True, blank=True, verbose_name=_("Channel ID"),
                                  help_text="LINE Channel ID")
    basic_id = models.CharField(max_length=64, null=True, blank=True, verbose_name=_("Bot basic ID"),
                                help_text="如 @xxxx")
    bot_user_id = models.CharField(max_length=64, null=True, blank=True, verbose_name=_("Bot User Id"),
                                   help_text="LINE Bot User Id")
    channel_access_token = models.CharField(max_length=512, verbose_name=_("Channel Access Token"),
                                            help_text="LINE Channel Access Token")
    channel_secret = models.CharField(max_length=128, verbose_name=_("Channel Secret"),
                                      help_text="LINE Channel Secret")
    is_default = models.BooleanField(default=False, verbose_name=_("默认Bot"),
                                     help_text="是否作为默认Bot(无绑定时使用)")
    is_active = models.BooleanField(default=True, verbose_name=_("是否启用"), help_text="是否启用该Bot")
    monthly_quota = models.IntegerField(null=True, blank=True, verbose_name=_("月消息配额(该Bot)"),
                                        help_text="该Bot(物理Channel)月消息上限, 如免费500/付费10000; 留空用全局配置")

    class Meta:
        db_table = "dvadmin_line_bot"
        verbose_name = "LineBot"
        verbose_name_plural = verbose_name
        ordering = ["name", "-create_datetime"]

    def __str__(self):
        return self.name


def get_tenant_bots(tenant):
    """某租户名下的 bot 列表(用于分配/下拉)"""
    if tenant is None:
        return LineBot.objects.none()
    return LineBot.objects.filter(tenant=tenant, is_active=True)


def get_bot_for_property(prop):
    """
    取该房源(群)应使用的 bot, 带归属校验防串台:
    1. 优先 prop.line_bot(且归属本租户且启用)
    2. 其次租户名下任一启用 bot
    **没有分配则返回 None**(绝不启用全局默认兜底, 避免未分配租户蹭别的bot)
    """
    tenant = getattr(prop, 'tenant', None)
    # 1. 群级指定 bot
    prop_bot = getattr(prop, 'line_bot', None)
    if prop_bot is not None:
        # 校验归属: 若 bot 有归属租户, 必须与房源租户相同
        if prop_bot.is_active and (prop_bot.tenant is None or prop_bot.tenant_id == (tenant.id if tenant else None)):
            return prop_bot
    # 2. 租户名下任一启用 bot
    tenant_bots = get_tenant_bots(tenant)
    tb = tenant_bots.first()
    if tb is not None:
        return tb
    # 3. 无分配 -> 返回 None (没有就是没有, 由调用方告警)
    return None


class DeeplKey(CoreModel):
    """
    DeepL API Key(多 Key 池, 用于扩展免费额度)
    翻译时按 is_default 优先, 再按创建顺序轮询/降级, 452/456(月额度超限)自动切换下一个
    """
    name = models.CharField(max_length=64, verbose_name=_("Key名称"), help_text="如 主账号 / 备用01")
    api_key = models.CharField(max_length=255, verbose_name=_("API Key"),
                               help_text="DeepL Auth Key(仅需去掉:fx 后缀的裸key即可)")
    is_default = models.BooleanField(default=False, verbose_name=_("默认Key"),
                                     help_text="是否作为默认Key(翻译优先使用)")
    is_active = models.BooleanField(default=True, verbose_name=_("是否启用"), help_text="是否启用该Key")
    remark = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("备注"),
                              help_text="如来源/用途/付费计划")

    class Meta:
        db_table = "dvadmin_deepl_key"
        verbose_name = "DeepL Key"
        verbose_name_plural = verbose_name
        ordering = ["-is_default", "id"]

    def __str__(self):
        return self.name


def get_default_deepl_key():
    """全局默认 Key(按 is_default, 否则第一条启用)"""
    key = DeeplKey.objects.filter(is_active=True, is_default=True).first()
    if key:
        return key
    return DeeplKey.objects.filter(is_active=True).first()


def get_active_deepl_keys():
    """全部启用 Key(默认优先), 用于多 Key 轮询/超限降级"""
    return list(DeeplKey.objects.filter(is_active=True).order_by("-is_default", "id"))


class MessageLog(CoreModel):
    """
    消息发送记录(用于配额统计)
    line 计费按「接收人数 × 次数」, 每条 push 记录接收人数
    """
    RESULT_CHOICES = (
        ('success', '成功'),
        ('failed', '失败'),
    )
    tenant = models.ForeignKey(
        to='tenant.Tenant',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("租户"),
        help_text="所属租户",
        db_constraint=False,
    )
    line_bot = models.ForeignKey(
        to='notify.LineBot',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("LineBot"),
        help_text="使用的Bot",
        db_constraint=False,
    )
    property = models.ForeignKey(
        to='property.Property',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("房源"),
        help_text="关联房源(提醒触发)",
        db_constraint=False,
    )
    group_id = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("Line群ID"),
                                help_text="发送目标群ID")
    group_size = models.IntegerField(default=1, verbose_name=_("接收人数"),
                                     help_text="该群的人数(计费条数=接收人数×次数)")
    msg_type = models.CharField(max_length=32, null=True, blank=True, verbose_name=_("消息类型"),
                                help_text="rent/maturity/annual/utility/custom等")
    rule_id = models.CharField(max_length=64, null=True, blank=True, verbose_name=_("规则ID"),
                               help_text="自定义提醒规则(ReminderRule)ID; 普通 rent/maturity 为空")
    content = models.TextField(null=True, blank=True, verbose_name=_("消息内容"), help_text="消息内容")
    result = models.CharField(max_length=32, choices=RESULT_CHOICES, default='success',
                              verbose_name=_("发送结果"), help_text="发送结果")
    error_msg = models.TextField(null=True, blank=True, verbose_name=_("错误信息"), help_text="错误信息")
    # 计费条数 = 接收人数 × 1(每条push记录1次)
    count = models.IntegerField(default=1, verbose_name=_("计费条数"), help_text="本次消耗的配额条数")

    class Meta:
        db_table = "dvadmin_message_log"
        verbose_name = "消息记录"
        verbose_name_plural = verbose_name
        ordering = ["-create_datetime"]

    def __str__(self):
        return f"{self.line_bot}->{self.group_id}"


class GroupDocRecord(CoreModel):
    """群文档存储记录(仅新存储的文件): 记录存储时间 / Bot / 消息时间 / 发送人
    webhook 收到群图片/文件并成功落盘时写入一条
    """
    tenant = models.ForeignKey(
        to='tenant.Tenant',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("租户"),
        help_text="所属租户",
        db_constraint=False,
    )
    line_bot = models.ForeignKey(
        to='notify.LineBot',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("LineBot"),
        help_text="收到该文件的Bot",
        db_constraint=False,
    )
    bot_name = models.CharField(max_length=64, null=True, blank=True, verbose_name=_("Bot名称快照"),
                                help_text="存储时 Bot 名称(防改名影响历史)")
    property = models.ForeignKey(
        to='property.Property',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("房源"),
        help_text="关联房源(按 group_id 定位)",
        db_constraint=False,
    )
    group_id = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("Line群ID"),
                                help_text="来源群ID")
    message_id = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("LINE消息ID"),
                                  help_text="LINE 消息 id(文件唯一标识)")
    file_name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("文件名"),
                                 help_text="落盘文件名")
    store_time = models.DateTimeField(null=True, blank=True, verbose_name=_("存储时间"),
                                      help_text="文件下载落盘时间")
    message_time = models.DateTimeField(null=True, blank=True, verbose_name=_("消息时间"),
                                        help_text="LINE 事件时间戳(用户真正发送的时间)")
    sender_user_id = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("发送人ID"),
                                      help_text="LINE 用户 id(若有)")

    class Meta:
        db_table = "dvadmin_group_doc_record"
        verbose_name = "群文档记录"
        verbose_name_plural = verbose_name
        ordering = ["-store_time", "-create_datetime"]

    def __str__(self):
        return f"GroupDoc({self.file_name}) bot={self.bot_name} group={self.group_id}"


class BroadcastTask(CoreModel):
    """
    群发信息任务(租户经理发起, 后台 Celery 执行)
    记录进度: 每发完一个群更新一次 sent/failed/skipped, 前端轮询
    """
    STATUS_CHOICES = (
        ('pending', '等待执行'),
        ('running', '执行中'),
        ('done', '已完成'),
        ('failed', '失败'),
    )
    tenant = models.ForeignKey(
        to='tenant.Tenant',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("租户"),
        help_text="目录租户",
        db_constraint=False,
    )
    message = models.TextField(verbose_name=_("群发内容"), help_text="发给所有群的自定义消息")
    total = models.IntegerField(default=0, verbose_name=_("目标群数"), help_text="本次需要发送的群数量")
    est_recipients = models.IntegerField(default=0, verbose_name=_("估算接收人数"),
                                         help_text="Σ group_size(计费参考)")
    sent = models.IntegerField(default=0, verbose_name=_("已发送成功"))
    failed = models.IntegerField(default=0, verbose_name=_("发送失败"))
    skipped = models.IntegerField(default=0, verbose_name=_("跳过"))
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='pending',
                              verbose_name=_("状态"))
    error_msg = models.TextField(null=True, blank=True, verbose_name=_("错误信息"),
                                 help_text="整体失败原因")
    celery_task_id = models.CharField(max_length=128, null=True, blank=True,
                                      verbose_name=_("Celery任务ID"),
                                      help_text="用于清理时撤销排队中的后台任务")
    property_ids = models.JSONField(null=True, blank=True, default=None,
                                    verbose_name=_("目标房源IDs"),
                                    help_text="勾选群发的房源ID列表; 为空=本租户全部带群ID房源")

    class Meta:
        db_table = "dvadmin_broadcast_task"
        verbose_name = "群发任务"
        verbose_name_plural = verbose_name
        ordering = ["-create_datetime"]

    def __str__(self):
        return f"BroadcastTask({self.id}) tenant={getattr(self.tenant, 'name', None)} status={self.status}"
