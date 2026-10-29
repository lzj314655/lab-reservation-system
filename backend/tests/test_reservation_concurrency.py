"""预约并发正确性测试

核心断言：同一时段 N 个并发请求，有且只有 1 条成功落库（零超订）。

分层验证：
- L2 父行锁：20 线程 Barrier 对齐后并发抢同一空档
- L3 唯一索引：绕过应用锁直接 INSERT 重复活跃记录（含 equipment_id=NULL 的哨兵键语义）
- 状态机：0→1→3 合法流转、终态拒绝、取消后槽位释放
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.common.exceptions import BusinessException
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.reservation import ReservationCreateRequest
from app.services import reservation_service

CONCURRENCY = 20
FUTURE = (date.today() + timedelta(days=7)).isoformat()

CONFLICT_MSGS = ("该时段已预约", "手慢了，该时段刚被他人预约")


def _payload(lab_id, start="10:00", end="12:00", d=FUTURE):
    return ReservationCreateRequest(
        lab_id=lab_id, equipment_id=None, date=d,
        start_time=start, end_time=end, remark="pytest",
    )


# ============================================================
# L2：父行锁 + 区间检测，同一空档并发抢约
# ============================================================

def test_concurrent_same_slot_exactly_one_winner(session_factory, seed):
    """20 线程同时抢同一实验室同一空档：恰好 1 成功 / 19 业务冲突 / 0 异常"""

    def worker(_):
        db = session_factory()
        try:
            user = db.get(User, seed["alice_id"])
            barrier.wait()  # 所有线程对齐后同时发起，最大化竞态窗口
            reservation_service.create_reservation(db, user, _payload(seed["lab_id"]))
            return "ok"
        except BusinessException as e:
            if e.message in CONFLICT_MSGS:
                return "conflict"
            return f"unexpected-business:{e.message}"
        except Exception as e:  # noqa: BLE001
            return f"unexpected:{type(e).__name__}:{e}"
        finally:
            db.close()

    barrier = threading.Barrier(CONCURRENCY)
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        results = list(pool.map(worker, range(CONCURRENCY)))

    ok = results.count("ok")
    conflict = results.count("conflict")
    unexpected = [r for r in results if r.startswith("unexpected")]

    assert unexpected == [], f"出现非预期异常: {unexpected}"
    assert ok == 1, f"同一时段应恰好 1 条成功，实际 {ok} 条 → 超订或漏订"
    assert conflict == CONCURRENCY - 1

    # 数据库层复核：活跃记录确实只有一条
    db = session_factory()
    rows = (
        db.query(Reservation)
        .filter(Reservation.lab_id == seed["lab_id"], Reservation.date == FUTURE)
        .all()
    )
    try:
        assert len(rows) == 1
        assert rows[0].status == 0
        assert rows[0].active_marker == 1  # 生成列语义正确
    finally:
        db.close()


def test_concurrent_different_labs_no_interference(session_factory, seed):
    """并发预约不同实验室互不干扰：两个实验室各抢各的，均成功"""

    def worker(lab_id):
        db = session_factory()
        try:
            user = db.get(User, seed["alice_id"])
            barrier.wait()
            reservation_service.create_reservation(db, user, _payload(lab_id))
            return "ok"
        except Exception as e:  # noqa: BLE001
            return f"unexpected:{type(e).__name__}:{e}"
        finally:
            db.close()

    barrier = threading.Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, [seed["lab_id"], seed["lab_b_id"]]))

    assert results == ["ok", "ok"], results


# ============================================================
# L3：唯一索引兜底（绕过应用层直接插库）
# ============================================================

def test_unique_index_rejects_duplicate_active_row(session_factory, seed):
    """两条完全相同时段的活跃记录，第二条 INSERT 被 1062 拒绝
    （equipment_id 均为 NULL —— 同时验证 equip_key 哨兵列堵住了
    唯一索引中 NULL 永不冲突的语义漏洞）"""
    db1, db2 = session_factory(), session_factory()

    def _row():
        return Reservation(
            user_id=seed["alice_id"], lab_id=seed["lab_id"], equipment_id=None,
            date=FUTURE, start_time="14:00", end_time="16:00",
            remark="pytest-uk", status=0,
        )

    db1.add(_row())
    db1.commit()

    db2.add(_row())
    with pytest.raises(IntegrityError) as ei:
        db2.commit()
    # pymysql: InternalError(1062, "Duplicate entry ...")
    assert 1062 in getattr(ei.value.orig, "args", []), ei.value
    db2.rollback()
    db1.close()
    db2.close()


def test_unique_index_releases_slot_after_cancel(session_factory, seed):
    """记录取消后 active_marker 置 NULL，同时段可再次插入（唯一键自动让位）"""
    db1 = session_factory()
    first = Reservation(
        user_id=seed["alice_id"], lab_id=seed["lab_id"], equipment_id=None,
        date=FUTURE, start_time="18:00", end_time="20:00",
        remark="pytest-release", status=0,
    )
    db1.add(first)
    db1.commit()
    assert first.active_marker == 1

    first.status = 3  # 取消
    db1.commit()
    db1.refresh(first)
    assert first.active_marker is None  # 生成列随状态自动翻转

    db2 = session_factory()
    db2.add(Reservation(
        user_id=seed["bob_id"], lab_id=seed["lab_id"], equipment_id=None,
        date=FUTURE, start_time="18:00", end_time="20:00",
        remark="pytest-release-2", status=0,
    ))
    db2.commit()  # 不再抛 IntegrityError
    db1.close()
    db2.close()


# ============================================================
# 状态机：合法流转与终态拒绝
# ============================================================

def test_state_machine_create_audit_cancel_rebook(session_factory, seed):
    """0→1（审核）→3（取消已通过）→ 重新预约成功；终态再取消被拒"""
    db = session_factory()
    alice = db.get(User, seed["alice_id"])

    item = reservation_service.create_reservation(db, alice, _payload(seed["lab_id"]))
    assert item.status == 0

    # 未审核前取消（0→3）
    reservation_service.cancel_reservation(db, alice, item.id)
    db.refresh(item)
    assert item.status == 3

    # 终态再取消被拒
    with pytest.raises(BusinessException):
        reservation_service.cancel_reservation(db, alice, item.id)

    # 重新预约同一时段成功，再走 0→1→3 全链路
    item2 = reservation_service.create_reservation(db, alice, _payload(seed["lab_id"]))
    reservation_service.audit_reservation(db, item2.id, 1)  # 管理员通过
    db.refresh(item2)
    assert item2.status == 1

    # 已通过后取消（新放开的 1→3）
    reservation_service.cancel_reservation(db, alice, item2.id)
    db.refresh(item2)
    assert item2.status == 3

    # 取消释放后又能预约
    item3 = reservation_service.create_reservation(db, alice, _payload(seed["lab_id"]))
    assert item3.id is not None
    db.close()
