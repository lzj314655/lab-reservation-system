import logging
import time
from datetime import datetime

from sqlalchemy import and_, or_, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.pagination import normalize_page
from app.common.response import PageResponse
from app.database import SessionLocal
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.reservation import ReservationCreateRequest, ReservationResponse

logger = logging.getLogger(__name__)

# 死锁(1213) / 锁等待超时(1205) 的最大重试次数与退避基数
MAX_CREATE_RETRY = 3
LOCK_BACKOFF_BASE = 0.05
_DB_ERRNO_DEADLOCK = {1213, 1205}
_DB_ERRNO_DUPLICATE = 1062


def _db_errno(exc: Exception) -> int | None:
    """提取 MySQL 驱动错误码（pymysql: exc.orig.args[0]）"""
    orig = getattr(exc, "orig", None)
    try:
        return int(orig.args[0])
    except (AttributeError, IndexError, TypeError, ValueError):
        return None


def _normalize_time(value: str) -> str:
    """把任意时间字符串统一为 HH:MM，非法则抛 ValueError。"""
    s = str(value).strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).strftime("%H:%M")
        except ValueError:
            continue
    parts = s.split(":")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
    raise ValueError(f"无法解析时间: {value}")


def create_reservation(
    db: Session, current_user: User, data: ReservationCreateRequest
):
    """创建预约（并发安全）。

    并发控制分四层：
    L1 参数级校验（不碰库，失败直接抛业务异常）
    L2 父行锁：SELECT ... FROM labs WHERE id=? FOR UPDATE，
       同一实验室的所有预约写入在实验室行上天然串行、锁顺序全局一致 → 结构性无死锁
    L3 唯一索引 uk_res_active_slot 兜底（任何绕过应用锁的写入触发 1062）
    L4 死锁/锁超时(1213/1205) 指数退避重试
    """
    # ---------- L1 参数级校验 ----------
    try:
        start_time = _normalize_time(data.start_time)
        end_time = _normalize_time(data.end_time)
    except ValueError as exc:
        raise BusinessException(message=str(exc))

    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    if data.date < current_date:
        raise BusinessException(message="预约日期不能小于当前的日期")
    if end_time < start_time:
        raise BusinessException(message="预约的结束时间不能小于开始时间")
    if data.date == current_date and start_time < current_time:
        raise BusinessException(message="预约开始时间不能小于当前的时间")

    # ---------- L4 事务级重试 ----------
    last_exc = None
    for attempt in range(MAX_CREATE_RETRY + 1):
        try:
            return _create_reservation_once(
                db, current_user, data, start_time, end_time
            )
        except OperationalError as exc:
            last_exc = exc
            if _db_errno(exc) not in _DB_ERRNO_DEADLOCK or attempt == MAX_CREATE_RETRY:
                raise
            logger.warning(
                "预约写入遇到锁冲突(errno=%s, 第%d次)，回滚后重试",
                _db_errno(exc), attempt + 1,
            )
            db.rollback()
            time.sleep(LOCK_BACKOFF_BASE * (2 ** attempt))
        except IntegrityError as exc:
            db.rollback()
            if _db_errno(exc) == _DB_ERRNO_DUPLICATE:
                # L3 唯一索引兜底命中：说明有写入绕过了应用锁
                logger.warning("唯一索引兜底命中: %s", exc)
                raise BusinessException(message="手慢了，该时段刚被他人预约")
            raise
    raise last_exc


def _create_reservation_once(
    db: Session,
    current_user: User,
    data: ReservationCreateRequest,
    start_time: str,
    end_time: str,
) -> Reservation:
    """单次尝试：加父行锁 → 校验 → 冲突检测 → 插入 → 提交（同一事务）"""
    # ---------- L2 父行锁 ----------
    # 锁实验室行而不是冲突结果集：空时段没有已存在行，锁结果集只能加间隙锁（RR 下
    # 并发首单互相等待对方间隙锁 → 死锁 1213）；锁父行则所有写入方按同一顺序排队。
    lab = (
        db.query(Lab)
        .filter(Lab.id == data.lab_id)
        .with_for_update()
        .first()
    )
    if not lab:
        raise BusinessException(message="实验室不存在")
    if lab.status != 1:
        raise BusinessException(message="实验室已关闭")

    # 实验室开放时间校验（基于已锁定的 lab 对象）
    if lab.open_time:
        try:
            lab_open = _normalize_time(lab.open_time)
            if start_time < lab_open:
                raise BusinessException(message="预约时间不能早于实验室的开放时间")
        except ValueError:
            logger.warning("实验室 open_time 格式异常: %s", lab.open_time)
    if lab.close_time:
        try:
            lab_close = _normalize_time(lab.close_time)
            if end_time > lab_close:
                raise BusinessException(message="预约时间不能晚于实验室的关闭时间")
        except ValueError:
            logger.warning("实验室 close_time 格式异常: %s", lab.close_time)

    # equipment_id 不为空 则表示这次是预约的实验室设备
    if data.equipment_id is not None:
        equipment = (
            db.query(Equipment).filter(Equipment.id == data.equipment_id).first()
        )
        if not equipment:
            raise BusinessException(message="实验室设备不存在")
        # 设备必须属于所约实验室，否则会产生"实验室A的设备出现在实验室B日历"
        # 这类脏数据（冲突检测、统计、日历展示全部按 lab_id 关联）
        if equipment.lab_id != data.lab_id:
            raise BusinessException(message="该设备不属于所选实验室")
        if equipment.status != 1:
            raise BusinessException(message="实验室设备正在维修")

    # 冲突检测（父行锁已保证同一实验室写入串行，无需再锁结果集）
    query = db.query(Reservation).filter(
        Reservation.lab_id == data.lab_id,
        Reservation.date == data.date,
        Reservation.status.in_([0, 1]),
        Reservation.start_time < end_time,
        Reservation.end_time > start_time,
    )
    if data.equipment_id is not None:
        query = query.filter(Reservation.equipment_id == data.equipment_id)
    else:
        query = query.filter(Reservation.equipment_id.is_(None))
    if query.first():
        raise BusinessException(message="该时段已预约")

    reservation_model = Reservation(
        user_id=current_user.id,
        lab_id=data.lab_id,
        equipment_id=data.equipment_id,
        date=data.date,
        start_time=start_time,
        end_time=end_time,
        remark=data.remark,
        status=0,
    )
    db.add(reservation_model)
    db.commit()
    db.refresh(reservation_model)
    return reservation_model


def get_reservation_page_list(
    db: Session,
    current_user: User,
    page: int,
    page_size: int,
    status: int | None = None,
    keyword: str | None = None,
):
    """查询预约的记录"""
    page, page_size = normalize_page(page, page_size)
    query = db.query(Reservation)
    if current_user.role != "admin":
        query = query.filter(Reservation.user_id == current_user.id)
    if status is not None:
        query = query.filter(Reservation.status == status)
    if keyword:
        like = f"%{keyword}%"
        query = (
            query.join(Reservation.user)
            .join(Reservation.lab)
            .filter(
                or_(
                    User.username.ilike(like),
                    User.name.ilike(like),
                    Lab.name.ilike(like),
                )
            )
        )
    total = query.count()

    items = (
        query.order_by(Reservation.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    result = []
    for item in items:
        res = ReservationResponse.model_validate(item)
        res.user_name = item.user.name if item.user else None
        res.lab_name = item.lab.name if item.lab else None
        res.equipment_name = item.equipment.name if item.equipment else None
        res.type = "设备" if item.equipment_id else "实验室"
        result.append(res)
    return PageResponse(list=result, total=total)


def cancel_reservation(db: Session, current_user: User, reservation_id: int):
    """取消预约（状态机：0待审核→3已取消，1已通过→3已取消）

    加行锁的原因：取消与管理员审核可能并发（用户点取消的同时管理员点通过）。
    不加锁时两边都读到 status=0，后提交的一方覆盖前一方，会出现
    "已取消却收到审核通过通知" 这类状态与通知不一致的脏数据。
    """
    item = (
        db.query(Reservation)
        .filter(Reservation.id == reservation_id)
        .with_for_update()
        .first()
    )
    if not item:
        raise BusinessException(message="预约记录不存在")
    if item.user_id != current_user.id:
        raise BusinessException(message="无权限", code=403)
    if item.status not in (0, 1):
        raise BusinessException(message="当前状态无法取消")
    item.status = 3
    db.commit()


def audit_reservation(db: Session, reservation_id: int, status: int):
    """管理员审核预约

    同样加行锁：并发审核 / 与定时扫描（0→3）竞争时，后到者拿到锁后
    会读到最新状态并拒绝，避免重复发通知或把过期预约"复活"。
    """
    if status not in [1, 2]:
        raise BusinessException(message="审核状态错误")
    item = (
        db.query(Reservation)
        .filter(Reservation.id == reservation_id)
        .with_for_update()
        .first()
    )
    if not item:
        raise BusinessException(message="预约记录不存在")
    if item.status != 0:
        raise BusinessException(message="当前状态不支持审核")
    item.status = status
    # 审核结果推送给预约人
    from app.services import notification_service

    target = item.equipment.name if item.equipment else item.lab.name
    time_desc = f"{item.date} {item.start_time}~{item.end_time}"
    if status == 1:
        notification_service.create_notification(
            db, item.user_id,
            title="预约审核通过",
            content=f"您预约的「{target}」（{time_desc}）已通过审核，请按时使用。",
            type_="audit_pass", related_id=item.id,
        )
    else:
        notification_service.create_notification(
            db, item.user_id,
            title="预约审核未通过",
            content=f"您预约的「{target}」（{time_desc}）未通过审核，如有疑问请联系管理员。",
            type_="audit_reject", related_id=item.id,
        )
    db.commit()


def get_lab_calendar(db: Session, lab_id: int, start_date: str, end_date: str):
    """实验室日历视图：某日期区间内该实验室的占用情况"""
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")

    items = (
        db.query(Reservation)
        .filter(
            Reservation.lab_id == lab_id,
            Reservation.date >= start_date,
            Reservation.date <= end_date,
            Reservation.status.in_([0, 1]),
        )
        .order_by(Reservation.date, Reservation.start_time)
        .all()
    )
    return [
        {
            "id": item.id,
            "date": item.date,
            "start_time": item.start_time,
            "end_time": item.end_time,
            "status": item.status,
            "type": "设备" if item.equipment_id else "实验室",
            "equipment_name": item.equipment.name if item.equipment else None,
            "user_name": item.user.name if item.user else None,
            "remark": item.remark,
        }
        for item in items
    ]


def expire_pending_reservations():
    """到期扫描（APScheduler 周期调用，幂等）。

    状态机规则：
      0待审核 且已过期  → 3已取消（超时未审核）
      1已通过 且已过期  → 4已完成（爽约判定留给二期签到功能）
    多实例/多 worker 部署时用 MySQL 广播锁保证同一时刻只有一个实例执行。
    """
    db = SessionLocal()
    try:
        # GET_LOCK 立即返回：拿不到锁说明别的实例正在扫，本轮直接放弃
        if db.execute(text("SELECT GET_LOCK('lab_expire_scan', 0)")).scalar() != 1:
            return
        try:
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M")
            expired = or_(
                Reservation.date < today,
                and_(Reservation.date == today, Reservation.end_time <= time_str),
            )
            cancelled = (
                db.query(Reservation)
                .filter(Reservation.status == 0, expired)
                .update({"status": 3}, synchronize_session=False)
            )
            finished = (
                db.query(Reservation)
                .filter(Reservation.status == 1, expired)
                .update({"status": 4}, synchronize_session=False)
            )
            if cancelled or finished:
                db.commit()
                logger.info(
                    "到期扫描: %d 条待审核置为已取消, %d 条已通过置为已完成",
                    cancelled, finished,
                )
        finally:
            db.execute(text("SELECT RELEASE_LOCK('lab_expire_scan')"))
    finally:
        db.close()