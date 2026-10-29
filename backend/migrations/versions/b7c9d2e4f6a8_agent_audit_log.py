"""Agent 安全加固：工具调用审计日志表

Revision ID: b7c9d2e4f6a8
Revises: 8f3a1c2d9e01
Create Date: 2026-10-25
"""

from alembic import op
import sqlalchemy as sa

revision = "b7c9d2e4f6a8"
down_revision = "8f3a1c2d9e01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agent_audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
            comment="操作人(来自JWT，不信任LLM参数)",
        ),
        sa.Column("conversation_id", sa.Integer(), comment="所属AI会话"),
        sa.Column("tool_name", sa.String(50), nullable=False, comment="工具名"),
        sa.Column("args_json", sa.String(2000), comment="工具入参快照(JSON)"),
        sa.Column(
            "result", sa.String(20), nullable=False,
            comment="结果: ok-成功, denied-被拒绝, error-执行异常",
        ),
        sa.Column("detail", sa.String(500), comment="结果摘要或拒绝原因"),
        sa.Column("reservation_id", sa.Integer(), comment="关联预约单ID"),
        sa.Column(
            "risk_flag", sa.String(50),
            comment="风险标记: injection_suspected/quota_exceeded/param_rejected/unauthorized_cancel",
        ),
        sa.Column("ip", sa.String(50), comment="来源IP(预留)"),
        sa.Column("create_time", sa.DateTime(), comment="创建时间Id"),
        sa.Column("updatetime", sa.DateTime(), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
    )


def downgrade():
    op.drop_table("agent_audit_logs")
