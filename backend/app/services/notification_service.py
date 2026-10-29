from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.pagination import normalize_page
from app.common.response import PageResponse
from app.models.notification import Notification
from app.models.user import User


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    content: str,
    type_: str = "info",
    related_id: int | None = None,
):
    """写入一条站内通知（跟随调用方的事务一起提交）"""
    db.add(
        Notification(
            user_id=user_id,
            title=title,
            content=content,
            type=type_,
            related_id=related_id,
        )
    )


def get_page_list(
    db: Session,
    current_user: User,
    page: int,
    page_size: int,
    unread_only: bool = False,
):
    page, page_size = normalize_page(page, page_size)
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read == 0)
    total = query.count()
    items = (
        query.order_by(Notification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PageResponse(
        list=[
            {
                "id": item.id,
                "title": item.title,
                "content": item.content,
                "type": item.type,
                "related_id": item.related_id,
                "is_read": item.is_read,
                "create_time": item.create_time.strftime("%Y-%m-%d %H:%M")
                if item.create_time
                else None,
            }
            for item in items
        ],
        total=total,
    )


def unread_count(db: Session, current_user: User) -> int:
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read == 0)
        .count()
    )


def mark_read(db: Session, current_user: User, notification_id: int):
    item = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
        .first()
    )
    if not item:
        raise BusinessException(message="通知不存在")
    item.is_read = 1
    db.commit()


def mark_all_read(db: Session, current_user: User):
    db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.is_read == 0
    ).update({"is_read": 1})
    db.commit()
