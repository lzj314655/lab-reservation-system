"""pytest 全局夹具。

测试库选型说明（重要，勿改回 SQLite）：
- 必须用真实 MySQL：并发测试依赖 MySQL 特有行为——FOR UPDATE 锁语义、
  STORED 生成列、GET_LOCK、唯一索引 NULL 语义；SQLite 会静默跳过锁且
  不支持生成列，测出来的是假结果（假绿比没有测试更危险）。
- 事务回滚式夹具不适用：并发用例需要跨多个真实会话提交。
- 库选择：CI 里设 TEST_DB_URL 直接指定（GitHub Actions 的 mysql service）；
  本地默认把 DATABASE_URL 的库名替换为 lzjai_test，与真实库完全隔离。
"""

import os
import re

# ---- 必须在导入任何 app 模块之前完成测试库切换 ----
if "TEST_DB_URL" in os.environ:
    os.environ["DATABASE_URL"] = os.environ["TEST_DB_URL"]

TEST_DB_NAME = "lzjai_test"

import pytest  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.config import settings  # noqa: E402

# 本地模式：改写 settings（app.database 尚未导入，engine 建立时生效）
_TEST_DB_URL = settings.DATABASE_URL
if "TEST_DB_URL" not in os.environ:
    _TEST_DB_URL = re.sub(r"/[^/?]+(\?.*)?$", f"/{TEST_DB_NAME}", settings.DATABASE_URL)
    settings.DATABASE_URL = _TEST_DB_URL

from app.database import Base  # noqa: E402
# 导入全部模型，保证 create_all 建全表
from app.models.user import User  # noqa: E402
from app.models.lab import Lab  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    """会话级引擎：库不存在则创建，建全量表；会话结束断开连接"""
    server_url = re.sub(r"/[^/?]+(\?.*)?$", "", _TEST_DB_URL)
    server_engine = create_engine(server_url, pool_pre_ping=True)
    db_name = _TEST_DB_URL.rsplit("/", 1)[-1].split("?")[0]
    with server_engine.connect() as conn:
        conn.execute(
            text(f"CREATE DATABASE IF NOT EXISTS {db_name} DEFAULT CHARACTER SET utf8mb4")
        )
        conn.commit()
    server_engine.dispose()

    eng = create_engine(_TEST_DB_URL, pool_pre_ping=True, pool_size=30, max_overflow=10)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session_factory(engine):
    """每个测试前清空业务表，返回绑定测试库的 Session 工厂"""
    with engine.connect() as conn:
        for table in (
            "reservations", "notifications", "agent_audit_logs", "ai_messages",
            "ai_conversations", "equipments", "labs", "users",
        ):
            conn.execute(text(f"DELETE FROM {table}"))
        conn.commit()
    return sessionmaker(bind=engine, autoflush=False)


@pytest.fixture()
def seed(session_factory):
    """种子数据：2 个开放实验室 + 2 个学生 + 1 个管理员"""
    db = session_factory()
    lab = Lab(name="并发测试实验室A", status=1, capacity=30)
    lab_b = Lab(name="并发测试实验室B", status=1, capacity=30)
    alice = User(username="alice", password="x", name="Alice", role="student", status=1)
    bob = User(username="bob", password="x", name="Bob", role="student", status=1)
    admin = User(username="root", password="x", name="Root", role="admin", status=1)
    db.add_all([lab, lab_b, alice, bob, admin])
    db.commit()
    ids = {
        "lab_id": lab.id,
        "lab_b_id": lab_b.id,
        "alice_id": alice.id,
        "bob_id": bob.id,
        "admin_id": admin.id,
    }
    db.close()
    return ids


@pytest.fixture(scope="session")
def client():
    """API 层测试客户端。

    不使用 with 上下文：跳过 lifespan（不启动 APScheduler、不加载 embedding
    模型），保持测试轻量；请求处理本身不受影响。
    """
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


@pytest.fixture()
def auth(seed):
    """按用户 id 铸造 JWT 请求头（与生产同一条签名路径）"""

    def _make(user_id: int) -> dict:
        from app.utils.jwt import create_access_token

        return {"Authorization": f"Bearer {create_access_token(user_id)}"}

    return _make
