# -*- coding: utf-8 -*-
"""
内置每日提醒调度器(不依赖 celery beat 常驻进程)

背景: 项目以 uvicorn(单/多 worker) 运行, 而 celery beat 进程经常因环境问题(如 WSL 崩溃)
掉线, 导致「改了提醒时间却不执行」。内置调度器让「执行提醒」始终跟随 uvicorn 进程存活。

设计:
- 每个 worker 进程在 app ready 时启动一个守护线程, 每 interval 秒 tick 一次。
- tick 用 PostgreSQL advisory lock(pg_try_advisory_lock) 做跨进程单例: 任意时刻只有
  一个 worker 能进入「检查是否到点 + 执行」, 防止多 worker 重复发送。
- 到点判断: 读取 SystemConfig('notify_send_hour/minute') 与 Asia/Bangkok 当前时间,
  命中且当天尚未执行(SystemConfig('notify_last_run_date'))则触发 daily_notify_task。
- 改了 hour/minute -> interval 内下一次 tick 即读新值, 无需重启进程。

注意: 若同时运行 celery beat 与本调度器, 可能重复触发。生产二选一(推荐用本调度器)。
"""
import logging
import os
import threading
import time
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger("dvadmin.notify.scheduler")

_ADVISORY_LOCK_KEY = 0x44414  # 任意固定整数作为「每日提醒」跨进程锁 key
_TZ_BANGKOK = ZoneInfo("Asia/Bangkok")

_default_interval = float(os.environ.get("DVADMIN_NOTIFY_SCHEDULER_INTERVAL", "20") or 20)

_started = False
_lock = threading.Lock()
_stop_evt = threading.Event()
_thread = None


def _bangkok_now():
    """Asia/Bangkok 当前 datetime"""
    from django.utils import timezone as dj_tz
    now_utc = datetime.now(timezone.utc)
    return now_utc.astimezone(_TZ_BANGKOK)


def _try_acq_lock():
    """
    尝试获取跨进程 advisory lock。返回 (conn, True/False)。
    True: 本进程获得锁; False: 其它进程持有, 本次跳过。
    调用方必须负责 unlock + close。
    """
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute("SELECT pg_try_advisory_lock(%s)", [_ADVISORY_LOCK_KEY])
    row = cursor.fetchone()
    got = bool(row and row[0])
    return connection, got


def _release_lock(connection):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", [_ADVISORY_LOCK_KEY])
    except Exception:
        pass
    try:
        connection.close()
    except Exception:
        pass


def _should_dispatch(today):
    """
    判断此刻是否到「每日提醒时间」且今天还没执行过。
    today: Asia/Bangkok 当天 date
    返回 None 或 (hour, minute)
    """
    from dvadmin.notify.apps import NotifyConfig
    from dvadmin.system.models import SystemConfig
    try:
        hour = NotifyConfig._runtime_notify_hour()
        minute = NotifyConfig._runtime_notify_minute()
    except Exception as e:
        logger.warning("读取提醒时间失败, 本轮跳过: %s", e)
        return None
    # 当天是否已执行
    last = SystemConfig.objects.filter(key="notify_last_run_date").first()
    last_date = (last.value or "") if (last and last.value is not None) else ""
    if str(last_date) == today.isoformat():
        return None
    return hour, minute


def _mark_done(today):
    """记录当天已执行(事务内由调用方确保锁持有)"""
    from dvadmin.system.models import SystemConfig
    SystemConfig.objects.update_or_create(
        key="notify_last_run_date", defaults={"value": today.isoformat()}
    )


def _tick():
    """
    单次 tick:
    1. 尝试获取 advisory lock(拿不到 = 其他 worker 在执行, 跳过)
    2. 判断是否到点 -> 到点则执行 daily_notify_task(独立线程, 不阻塞循环)
    """
    now = _bangkok_now()
    today = now.date()

    conn, got = _try_acq_lock()
    if not got:
        return  # 其他进程持有, 本 worker 本轮跳过

    try:
        hm = _should_dispatch(today)
        if hm is None:
            return
        hour, minute = hm
        if (now.hour, now.minute) != (hour, minute):
            return

        logger.info("[内置调度] 到达发送时间 %02d:%02d (Bangkok), 触发今日提醒", hour, minute)
        _mark_done(today)

        # 在独立线程执行, 避免长任务阻塞 future ticks / 其它 worker
        def _run():
            try:
                from dvadmin.notify.tasks import daily_notify_task
                n = daily_notify_task()
                logger.info("[内置调度] 每日提醒执行完毕, 发送 %s 条", n)
            except Exception as e:
                logger.exception("[内置调度] 每日提醒执行失败: %s", e)

        threading.Thread(target=_run, daemon=True).start()
    finally:
        _release_lock(conn)


def _loop():
    interval = _default_interval
    logger.info("[内置调度] 每日提醒调度器启动, interval=%ss, tz=Asia/Bangkok", interval)
    while not _stop_evt.is_set():
        try:
            _tick()
        except Exception as e:
            # 连接类异常也可能抛出, 记录并继续下一轮
            logger.warning("[内置调度] tick 异常: %s", e)
        _stop_evt.wait(interval)


def start_scheduler():
    """在 app ready 时调用(幂等)。仅 uvicorn 运行态启动, 管理命令/celery 下跳过。
    由 NotifyConfig.ready() 在进程启动时触发。"""
    global _started, _thread
    if _started:
        return
    with _lock:
        if _started:
            return
        _stop_evt.clear()
        _thread = threading.Thread(target=_loop, daemon=True, name="daily-notify-scheduler")
        _thread.start()
        _started = True


def stop_scheduler():
    """优雅停止(通常无需调用; 进程退出自动回收)"""
    global _started
    _stop_evt.set()
    with _lock:
        _started = False