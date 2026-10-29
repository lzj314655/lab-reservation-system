"""迁移元数据一致性检查（纯静态，不需要数据库）。

为什么需要：
- 迁移链一旦出现多个 head，`alembic upgrade head` 会直接报错，属于上线级故障；
- `scripts/bootstrap_db.py` 用硬编码的 ALEMBIC_HEAD 给全新库打标，
  新增迁移后忘记同步该常量，会让新库被标记成旧版本，后续升级跑错迁移。

注意：这里检查的是"迁移脚本自身的元数据"，不是"模型与迁移的漂移"
（后者需要先建立 baseline 迁移，见 README 的迁移章节）。
"""

import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from scripts.bootstrap_db import ALEMBIC_HEAD  # noqa: E402


def _script_directory() -> ScriptDirectory:
    config = Config()
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return ScriptDirectory.from_config(config)


def test_single_migration_head():
    heads = _script_directory().get_heads()
    assert len(heads) == 1, f"迁移链存在多个 head，需要先合并：{heads}"


def test_bootstrap_head_matches_latest_revision():
    heads = _script_directory().get_heads()
    assert ALEMBIC_HEAD in heads, (
        f"bootstrap_db.ALEMBIC_HEAD={ALEMBIC_HEAD} 已过期（实际 head={heads[0]}）；"
        "新增迁移后请同步更新 backend/scripts/bootstrap_db.py 里的常量"
    )
