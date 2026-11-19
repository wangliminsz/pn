import logging
import sys

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class NotifyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dvadmin.notify'
    verbose_name = '消息通知'

    def ready(self):
        # 跳过迁移/建表等无 DB 表的场景
        if any(cmd in sys.argv for cmd in ('migrate', 'makemigrations')):
            return
        try:
            self._sync_daily_notify_beat()
        except Exception as e:
            logger.warning("同步每日提醒定时任务失败(可忽略): %s", e)
        try:
            self._start_builtin_scheduler()
        except Exception as e:
            logger.warning("内置每日提醒调度器未启动(可忽略): %s", e)

    @staticmethod
    def _start_builtin_scheduler():
        """
        仅在 uvicorn 运行态启动内置调度器:
        - 启动命令含 uvicorn(Web/ASGI) 时启用; celery worker/beat、管理命令(manage.py runserver含runserver) 等跳过,
          避免与 celery beat 冲突、避免管理命令里误起线程。
        - 多 worker 场景由调度器内部 advisory lock 保证任意时刻仅一个执行。
        """
        joined = " ".join(sys.argv)
        if "uvicorn" not in joined:
            return
        if any(cmd in joined for cmd in ("celery",)):
            return
        from dvadmin.notify.scheduler import start_scheduler
        start_scheduler()

    @staticmethod
    def _sync_daily_notify_beat():
        """每日提醒已改为 uvicorn 内置调度器(scheduler.py)负责, 不再依赖 celery beat。
        这里只做一件事: 删除 django_celery_beat 里遗留的 daily 定时任务, 避免与内置调度器重复发送。
        幂等: 每次进程启动(uvicorn/celery/管理命令)都会把该 beat 任务清掉。
        """
        from django_celery_beat.models import PeriodicTask

        task_name = "daily_property_notify"
        task_path = "dvadmin.notify.tasks.daily_notify_task"

        qs = PeriodicTask.objects.filter(name=task_name) | PeriodicTask.objects.filter(task=task_path)
        deleted, _ = qs.delete()
        if deleted:
            logger.info("已删除遗留的 celery beat 每日提醒任务 '%s' (由 uvicorn 内置调度器接管)", task_name)

    @staticmethod
    def _runtime_notify_hour():
        """运行时通知小时: 优先 SystemConfig(key='notify_send_hour'), 否则 env.py 的 NOTIFY_SEND_HOUR(默认9)"""
        from django.conf import settings
        try:
            from dvadmin.system.models import SystemConfig
            row = SystemConfig.objects.filter(key="notify_send_hour").first()
            if row is not None and row.value is not None:
                val = int(str(row.value))
                return max(0, min(23, val))
        except Exception:
            pass
        hour = int(getattr(settings, "NOTIFY_SEND_HOUR", 9) or 9)
        return max(0, min(23, hour))

    @staticmethod
    def _runtime_notify_minute():
        """运行时通知分钟: 优先 SystemConfig(key='notify_send_minute'), 否则 0"""
        try:
            from dvadmin.system.models import SystemConfig
            row = SystemConfig.objects.filter(key="notify_send_minute").first()
            if row is not None and row.value is not None:
                val = int(str(row.value))
                return max(0, min(59, val))
        except Exception:
            pass
        return 0
