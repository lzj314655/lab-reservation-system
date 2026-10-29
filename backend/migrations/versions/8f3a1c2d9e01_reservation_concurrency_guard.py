"""预约并发治理：生成列 + 活跃时段唯一索引 + 查询索引

Revision ID: 8f3a1c2d9e01
Revises:
Create Date: 2026-10-25

- active_marker: STORED 生成列，status 属于占用集合 {0,1} 时为 1，否则 NULL；
  利用 MySQL 唯一索引"多个 NULL 不冲突"的特性实现"仅活跃预约唯一"（部分索引的等价实现）
- equip_key: STORED 生成列，实验室级预约(equipment_id 为 NULL)映射为哨兵值 0；
  解决唯一索引中 equipment_id 的 NULL 永不冲突的语义漏洞
- uk_res_active_slot: 数据库层兜底，任何绕过应用锁的重复写入触发 1062
- ix_res_lab_date: 冲突检测查询索引
"""

from alembic import op
import sqlalchemy as sa

revision = "8f3a1c2d9e01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 1) 数据去重：活跃记录中"完全相同时段"的重复单，保留最早一条，其余置为已取消
    op.execute(
        """
        UPDATE reservations r
        JOIN (
            SELECT MIN(id) AS keep_id, lab_id, equipment_id, `date`, start_time, end_time
            FROM reservations
            WHERE status IN (0, 1)
            GROUP BY lab_id, equipment_id, `date`, start_time, end_time
            HAVING COUNT(*) > 1
        ) d ON r.id > d.keep_id
           AND r.lab_id = d.lab_id
           AND r.equipment_id <=> d.equipment_id
           AND r.`date` = d.`date`
           AND r.start_time = d.start_time
           AND r.end_time = d.end_time
        SET r.status = 3
        """
    )

    # 2) 生成列（MySQL 5.7+）
    op.add_column(
        "reservations",
        sa.Column(
            "active_marker",
            sa.Integer(),
            sa.Computed("IF(status IN (0, 1), 1, NULL)", persisted=True),
            nullable=True,
        ),
    )
    op.add_column(
        "reservations",
        sa.Column(
            "equip_key",
            sa.Integer(),
            sa.Computed("IF(equipment_id IS NULL, 0, equipment_id)", persisted=True),
            nullable=True,
        ),
    )

    # 3) 唯一兜底 + 冲突检测查询索引
    op.create_unique_constraint(
        "uk_res_active_slot",
        "reservations",
        ["lab_id", "equip_key", "date", "start_time", "end_time", "active_marker"],
    )
    op.create_index("ix_res_lab_date", "reservations", ["lab_id", "date"])


def downgrade():
    op.drop_index("ix_res_lab_date", table_name="reservations")
    op.drop_constraint("uk_res_active_slot", "reservations", type_="unique")
    op.drop_column("reservations", "equip_key")
    op.drop_column("reservations", "active_marker")
