from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.lab import Lab
from app.models.notification import Notification
from app.models.reservation import Reservation
from app.models.user import User


def get_overview(db: Session, current_user: User):
    """首页统计卡数据（管理员看全局，学生看自己）"""
    is_admin = current_user.role == "admin"

    open_labs = db.query(Lab).filter(Lab.status == 1).count()

    pending_query = db.query(Reservation).filter(Reservation.status == 0)
    if not is_admin:
        pending_query = pending_query.filter(Reservation.user_id == current_user.id)
    pending = pending_query.count()

    total_query = db.query(Reservation)
    if not is_admin:
        total_query = total_query.filter(Reservation.user_id == current_user.id)
    total = total_query.count()

    # 本周（周一至今）
    monday = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    today = date.today().isoformat()
    week_query = db.query(Reservation).filter(
        Reservation.date >= monday, Reservation.date <= today
    )
    if not is_admin:
        week_query = week_query.filter(Reservation.user_id == current_user.id)
    week_count = week_query.count()

    unread = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read == 0)
        .count()
    )

    data = {
        "open_labs": open_labs,
        "pending": pending,
        "total": total,
        "week_count": week_count,
        "unread": unread,
        "role": current_user.role,
    }

    if is_admin:
        data["users"] = db.query(User).count()
        approved = (
            db.query(Reservation).filter(Reservation.status == 1).count()
        )
        rejected = (
            db.query(Reservation).filter(Reservation.status == 2).count()
        )
        data["pass_rate"] = (
            round(approved / (approved + rejected) * 100, 1)
            if (approved + rejected) > 0
            else None
        )

    return data


def get_trend(db: Session, current_user: User, days: int = 30):
    """近 N 天每日预约量趋势"""
    days = max(1, min(days, 90))
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    today = date.today().isoformat()

    query = (
        db.query(Reservation.date, func.count(Reservation.id))
        .filter(Reservation.date >= start, Reservation.date <= today)
        .group_by(Reservation.date)
    )
    if current_user.role != "admin":
        query = query.filter(Reservation.user_id == current_user.id)
    rows = {d: c for d, c in query.all()}

    result = []
    for i in range(days):
        d = (date.today() - timedelta(days=days - 1 - i)).isoformat()
        result.append({"date": d, "count": rows.get(d, 0)})
    return result


def get_lab_usage(db: Session, limit: int = 8):
    """实验室预约量排行（管理员视角）"""
    limit = max(1, min(limit, 20))
    rows = (
        db.query(Reservation.lab_id, func.count(Reservation.id))
        .filter(Reservation.status.in_([0, 1]))
        .group_by(Reservation.lab_id)
        .order_by(func.count(Reservation.id).desc())
        .limit(limit)
        .all()
    )
    lab_names = {lab.id: lab.name for lab in db.query(Lab).all()}
    return [
        {"lab_id": lab_id, "lab_name": lab_names.get(lab_id, f"实验室{lab_id}"), "count": cnt}
        for lab_id, cnt in rows
    ]


def get_my_status(db: Session, current_user: User):
    """学生自己的预约状态分布"""
    rows = (
        db.query(Reservation.status, func.count(Reservation.id))
        .filter(Reservation.user_id == current_user.id)
        .group_by(Reservation.status)
        .all()
    )
    status_map = {0: "待审核", 1: "已通过", 2: "已拒绝", 3: "已取消"}
    counts = {status_map.get(s, str(s)): c for s, c in rows}
    return [{"name": k, "value": v} for k, v in counts.items()]
