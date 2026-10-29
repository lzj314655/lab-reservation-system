"""容器启动前的数据库引导（幂等，可重复执行）。

- 全新数据库：create_all 建全量表结构（含生成列/索引），并将 alembic 标记到 head
- 已有数据库：create_all 对已存在的表不做任何事；alembic_version 已存在时 INSERT IGNORE 无副作用

注意：已有"老结构"的数据库请走 `alembic upgrade head` 正式迁移，
不要依赖本脚本做表结构升级（create_all 不会 ALTER 已有表）。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.database import Base, engine  # noqa: E402
# 导入全部模型，注册元数据
from app.models.user import User  # noqa: E402,F401
from app.models.lab import Lab  # noqa: E402,F401
from app.models.equipment import Equipment  # noqa: E402,F401
from app.models.reservation import Reservation  # noqa: E402,F401
from app.models.ai import AIConversation, AIMessage  # noqa: E402,F401
from app.models.notification import Notification  # noqa: E402,F401
from app.models.agent_audit import AgentAuditLog  # noqa: E402,F401

# 当前迁移头（与 migrations/versions 一致；新增迁移后更新此处）
ALEMBIC_HEAD = "b7c9d2e4f6a8"


def main():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS alembic_version "
                "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )
        )
        conn.execute(
            text("INSERT IGNORE INTO alembic_version (version_num) VALUES (:v)"),
            {"v": ALEMBIC_HEAD},
        )
        conn.commit()
    print("数据库引导完成: 表结构已就绪, alembic 标记 =", ALEMBIC_HEAD)


if __name__ == "__main__":
    main()
