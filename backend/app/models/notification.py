from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = {"comment": "站内通知"}

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), comment="接收人", nullable=False
    )
    title: Mapped[str] = mapped_column(String(100), comment="标题", nullable=False)
    content: Mapped[str] = mapped_column(String(500), comment="内容", nullable=False)
    type: Mapped[str] = mapped_column(
        String(20), default="info",
        comment="类型: audit_pass-审核通过, audit_reject-审核拒绝, reservation-预约提交, info-系统通知",
    )
    related_id: Mapped[int | None] = mapped_column(Integer, comment="关联业务ID")
    is_read: Mapped[int] = mapped_column(
        default=0, comment="是否已读: 0-未读, 1-已读"
    )
