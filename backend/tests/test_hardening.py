"""本轮加固的回归测试（每个用例对应一条已修复的缺陷）。

覆盖：
- 上传接口必须登录（原先匿名可上传 → 磁盘打满）
- 预约入口参数校验：日期格式 / 备注长度（schema 层，REST 与 Agent 同一套）
- 设备必须属于所约实验室（防止跨实验室脏数据）
- 分页边界：page=0 不再触发 MySQL 1064 → 500
- 审核并发：同一预约两人同时通过，只有一个生效、只发一条通知
- AI 每日额度只统计用户提问，assistant 回复不占额度
- 登录失败限流
"""

import threading
from datetime import date, timedelta

import pytest

from app.api.ai import _check_daily_limit
from app.common.exceptions import BusinessException
from app.config import UPLOAD_DIR
from app.models.ai import AIConversation, AIMessage
from app.models.equipment import Equipment
from app.models.notification import Notification
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.reservation import ReservationCreateRequest
from app.services import lab_service, login_guard, reservation_service

FUTURE = (date.today() + timedelta(days=3)).isoformat()


def _reservation(lab_id: int, **kw) -> ReservationCreateRequest:
    return ReservationCreateRequest(
        lab_id=lab_id,
        equipment_id=kw.get("equipment_id"),
        date=kw.get("date", FUTURE),
        start_time=kw.get("start", "10:00"),
        end_time=kw.get("end", "11:00"),
        remark=kw.get("remark"),
    )


# ============================================================
# 1. 上传接口鉴权
# ============================================================


def test_upload_requires_auth(client, seed):
    resp = client.post(
        "/api/files/upload",
        files={"file": ("cover.png", b"hello", "image/png")},
    )
    assert resp.status_code == 401


def test_upload_with_auth_succeeds(client, seed, auth):
    resp = client.post(
        "/api/files/upload",
        files={"file": ("cover.png", b"hello", "image/png")},
        headers=auth(seed["alice_id"]),
    )
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["size"] == 5
    assert body["data"]["url"].startswith("/uploads/")

    saved = UPLOAD_DIR / body["data"]["disk_name"]
    assert saved.exists()
    saved.unlink()


# ============================================================
# 2. 预约参数校验（HTTP 入口）
# ============================================================


def test_invalid_date_rejected_with_422(client, seed, auth):
    resp = client.post(
        "/api/reservation",
        json={
            "lab_id": seed["lab_id"],
            "date": "2026-99-99",
            "start_time": "10:00",
            "end_time": "11:00",
        },
        headers=auth(seed["alice_id"]),
    )
    assert resp.status_code == 422
    assert "日期" in resp.json()["message"]


def test_too_long_remark_rejected_with_422(client, seed, auth):
    resp = client.post(
        "/api/reservation",
        json={
            "lab_id": seed["lab_id"],
            "date": FUTURE,
            "start_time": "10:00",
            "end_time": "11:00",
            "remark": "注" * 256,
        },
        headers=auth(seed["alice_id"]),
    )
    assert resp.status_code == 422


# ============================================================
# 3. 设备归属校验
# ============================================================


def test_equipment_must_belong_to_selected_lab(session_factory, seed):
    db = session_factory()
    alice = db.get(User, seed["alice_id"])
    other_lab_equipment = Equipment(
        lab_id=seed["lab_b_id"], name="B实验室显微镜", quantity=1, status=1
    )
    db.add(other_lab_equipment)
    db.commit()

    with pytest.raises(BusinessException, match="不属于"):
        reservation_service.create_reservation(
            db,
            alice,
            _reservation(seed["lab_id"], equipment_id=other_lab_equipment.id),
        )

    assert db.query(Reservation).count() == 0
    db.close()


# ============================================================
# 4. 分页边界
# ============================================================


def test_page_zero_returns_422_not_500(client, seed, auth):
    resp = client.get("/api/lab/list?page=0", headers=auth(seed["alice_id"]))
    assert resp.status_code == 422


def test_page_size_over_limit_returns_422(client, seed, auth):
    resp = client.get(
        "/api/lab/list?page_size=100000", headers=auth(seed["alice_id"])
    )
    assert resp.status_code == 422


def test_service_normalizes_illegal_pagination(session_factory, seed):
    """服务层兜底：内部调用（Agent/脚本）传非法值也不会拼出负数 OFFSET"""
    db = session_factory()
    page = lab_service.get_lab_page_list(db, page=0, page_size=100000)
    assert page.total >= 1
    assert len(page.list) <= 100
    db.close()


# ============================================================
# 5. 审核并发
# ============================================================


def test_concurrent_audit_only_one_wins(session_factory, seed):
    db = session_factory()
    alice = db.get(User, seed["alice_id"])
    item = reservation_service.create_reservation(db, alice, _reservation(seed["lab_id"]))
    item_id = item.id
    db.close()

    results = []
    barrier = threading.Barrier(2)
    results_lock = threading.Lock()

    def worker(status: int):
        session = session_factory()
        try:
            barrier.wait(timeout=10)
            reservation_service.audit_reservation(session, item_id, status)
            with results_lock:
                results.append(("ok", status))
        except BusinessException as exc:
            with results_lock:
                results.append(("rejected", exc.message))
        finally:
            session.close()

    threads = [threading.Thread(target=worker, args=(s,)) for s in (1, 2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    ok = [r for r in results if r[0] == "ok"]
    rejected = [r for r in results if r[0] == "rejected"]
    assert len(ok) == 1, f"应恰好一个审核成功，实际: {results}"
    assert len(rejected) == 1
    assert "不支持审核" in rejected[0][1]

    session = session_factory()
    assert session.get(Reservation, item_id).status == ok[0][1]
    # 只有成功的那次写了通知，不会出现"审核两次发两条"
    assert session.query(Notification).filter_by(related_id=item_id).count() == 1
    session.close()


# ============================================================
# 6. AI 每日额度口径
# ============================================================


def test_daily_limit_counts_user_messages_only(session_factory, seed):
    db = session_factory()
    alice = db.get(User, seed["alice_id"])
    conv = AIConversation(user_id=alice.id, title="额度口径测试")
    db.add(conv)
    db.commit()

    # 200 条 assistant 回复：不占额度
    db.add_all(
        AIMessage(conversation_id=conv.id, role="assistant", content="回复")
        for _ in range(200)
    )
    db.commit()
    _check_daily_limit(db, alice)  # 不应抛异常

    # 再补 200 条用户提问：达到上限
    db.add_all(
        AIMessage(conversation_id=conv.id, role="user", content="提问")
        for _ in range(200)
    )
    db.commit()
    with pytest.raises(BusinessException, match="上限"):
        _check_daily_limit(db, alice)
    db.close()


# ============================================================
# 7. 登录失败限流
# ============================================================


def test_login_locked_after_repeated_failures(client, session_factory, seed):
    from app.utils.password import hash_password

    # seed 里的用户密码是明文占位，不能用于登录校验，这里建一个真实 bcrypt 账号
    db = session_factory()
    db.add(
        User(
            username="lock_user",
            password=hash_password("correct-pwd"),
            name="限流测试",
            role="student",
            status=1,
        )
    )
    db.commit()
    db.close()

    login_guard.reset_all()
    try:
        # 正确密码可登录，且会把失败计数清零
        ok = client.post(
            "/api/auth/login", json={"username": "lock_user", "password": "correct-pwd"}
        )
        assert ok.json()["code"] == 200

        for _ in range(login_guard.MAX_FAILURES):
            resp = client.post(
                "/api/auth/login", json={"username": "lock_user", "password": "wrong"}
            )
            assert resp.json()["code"] == 500
            assert resp.json()["message"] == "账号密码错误"

        # 第 6 次直接限流；锁定期内即使密码正确也被拒绝
        resp = client.post(
            "/api/auth/login", json={"username": "lock_user", "password": "wrong"}
        )
        assert resp.json()["code"] == 429
        assert "次数过多" in resp.json()["message"]

        resp = client.post(
            "/api/auth/login", json={"username": "lock_user", "password": "correct-pwd"}
        )
        assert resp.json()["code"] == 429
    finally:
        login_guard.reset_all()
