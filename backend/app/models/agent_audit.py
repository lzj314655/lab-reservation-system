from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AgentAuditLog(Base):
    """Agent 工具调用审计日志

    记录每一次写操作类工具的调用（无论成败），用于：
    - 事后追溯：谁在什么时候通过 Agent 创建/取消了什么
    - 攻击检测：denied 记录聚集 = 疑似注入/越权尝试
    - 行为画像：quota_exceeded 频发 = 刷单尝试
    """
    __tablename__ = "agent_audit_logs"
    __table_args__ = {"comment": "Agent工具调用审计日志"}

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), comment="操作人(来自JWT，不信任LLM参数)", nullable=False
    )
    conversation_id: Mapped[int | None] = mapped_column(
        Integer, comment="所属AI会话"
    )
    tool_name: Mapped[str] = mapped_column(String(50), comment="工具名", nullable=False)
    args_json: Mapped[str] = mapped_column(
        String(2000), comment="工具入参快照(JSON)"
    )
    result: Mapped[str] = mapped_column(
        String(20), comment="结果: ok-成功, denied-被拒绝, error-执行异常"
    )
    detail: Mapped[str] = mapped_column(
        String(500), comment="结果摘要或拒绝原因(不含内部错误细节)"
    )
    reservation_id: Mapped[int | None] = mapped_column(
        Integer, comment="关联预约单ID(如有)"
    )
    risk_flag: Mapped[str | None] = mapped_column(
        String(50),
        comment="风险标记: injection_suspected/quota_exceeded/param_rejected/unauthorized_cancel",
    )
    ip: Mapped[str | None] = mapped_column(String(50), comment="来源IP(预留)")
