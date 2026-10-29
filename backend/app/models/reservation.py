from sqlalchemy import Computed, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.models.user import User

class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        # 数据库层兜底：仅"活跃"预约（active_marker=1）参与唯一约束，
        # 取消/完成/爽约后 active_marker 变 NULL 自动释放（MySQL 唯一索引允许多个 NULL）
        UniqueConstraint(
            "lab_id", "equip_key", "date", "start_time", "end_time", "active_marker",
            name="uk_res_active_slot",
        ),
        # 冲突检测查询索引
        Index("ix_res_lab_date", "lab_id", "date"),
        {"comment": "预约信息"},
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), comment="预约人", nullable=False
    )
    lab_id: Mapped[int] = mapped_column(
        ForeignKey("labs.id"), comment="实验室", nullable=False
    )
    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipments.id"), comment="设备，空表示预约实验室", nullable=True
    )
    date: Mapped[str] = mapped_column(String(20), comment="预约日期", nullable=False)
    start_time: Mapped[str] = mapped_column(
        String(20), comment="开始时间", nullable=False
    )
    end_time: Mapped[str] = mapped_column(
        String(20), comment="结束时间", nullable=False
    )
    remark: Mapped[str] = mapped_column(String(255), comment="备注", nullable=True)
    status: Mapped[int] = mapped_column(
        comment="预约状态 0待审核, 1已通过, 2已拒绝, 3已取消, 4已完成, 5爽约", default=0
    )
    # STORED 生成列：status 属于占用集合 {0,1} 时为 1，否则 NULL（应用层不可写入）
    active_marker: Mapped[int | None] = mapped_column(
        Integer,
        Computed("IF(status IN (0, 1), 1, NULL)", persisted=True),
        comment="活跃标记(生成列)",
    )
    # STORED 生成列：实验室级预约(equipment_id 为 NULL)映射为哨兵值 0，
    # 解决唯一索引中 NULL 永不冲突的语义漏洞
    equip_key: Mapped[int] = mapped_column(
        Integer,
        Computed("IF(equipment_id IS NULL, 0, equipment_id)", persisted=True),
        comment="设备哨兵键(生成列)",
    )

    user: Mapped[User] = relationship()
    lab: Mapped[Lab] = relationship()
    equipment: Mapped[Equipment] = relationship()