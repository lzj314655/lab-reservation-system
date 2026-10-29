"""APScheduler 定时任务（替代原 lifespan 内的 asyncio 手写循环）。

选型说明：
- 任务是"每分钟的幂等批量 SQL"，无重试语义/无优先级/无削峰需求 → 不需要 Celery 的
  broker（Redis/RabbitMQ），进程内 APScheduler 零新增基础设施；
- 多 worker / 多实例部署时任务会各跑一份，真正的执行互斥由任务内的
  MySQL GET_LOCK 广播锁保证（见 reservation_service.expire_pending_reservations）；
- coalesce + misfire_grace_time：应用重启错过调度窗口时合并补跑一次而非丢弃；
- jitter：把整分钟对齐的扫描打散，避免与其他周期任务形成尖峰。
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services import reservation_service

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None

SCAN_JOB_ID = "expire_scan"
SCAN_INTERVAL_SECONDS = 60


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        reservation_service.expire_pending_reservations,
        trigger="interval",
        seconds=SCAN_INTERVAL_SECONDS,
        jitter=10,
        coalesce=True,
        misfire_grace_time=30,
        max_instances=1,
        next_run_time=datetime.now(),  # 启动立即执行一次
        id=SCAN_JOB_ID,
    )
    _scheduler.start()
    logger.info("APScheduler 已启动: 到期扫描每 %d 秒执行一次", SCAN_INTERVAL_SECONDS)


def shutdown_scheduler():
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    logger.info("APScheduler 已停止")
