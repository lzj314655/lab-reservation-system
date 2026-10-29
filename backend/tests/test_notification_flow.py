"""通知生成与触达流程测试

覆盖:
- 审核通过/拒绝 → 通知生成（类型/接收人/内容锚点）
- AI 助手代预约成功 → 通知生成
- 已读流转：单条已读 / 全部已读 / 未读计数
- 隔离性：通知只能看到自己的
"""

from datetime import date, timedelta

from app.models.notification import Notification
from app.models.user import User
from app.schemas.reservation import ReservationCreateRequest
from app.services import notification_service, reservation_service
from app.services.agent_tools import build_tools

FUTURE = (date.today() + timedelta(days=5)).isoformat()


def _create(db, user, lab_id, **kw):
    payload = ReservationCreateRequest(
        lab_id=lab_id, equipment_id=None, date=kw.get("date", FUTURE),
        start_time=kw.get("start", "10:00"), end_time=kw.get("end", "11:00"),
        remark=kw.get("remark", "notify-test"),
    )
    return reservation_service.create_reservation(db, user, payload)


# ---------- 审核结果通知 ----------

def test_audit_pass_creates_notification(session_factory, seed):
    db = session_factory()
    alice = db.get(User, seed["alice_id"])
    item = _create(db, alice, seed["lab_id"])

    reservation_service.audit_reservation(db, item.id, 1)

    notes = db.query(Notification).filter(Notification.user_id == seed["alice_id"]).all()
    assert len(notes) == 1
    assert notes[0].type == "audit_pass"
    assert notes[0].related_id == item.id
    assert "已通过审核" in notes[0].content
    assert notification_service.unread_count(db, alice) == 1
    db.close()


def test_audit_reject_creates_notification(session_factory, seed):
    db = session_factory()
    alice = db.get(User, seed["alice_id"])
    item = _create(db, alice, seed["lab_id"])

    reservation_service.audit_reservation(db, item.id, 2)

    note = db.query(Notification).filter_by(user_id=seed["alice_id"]).one()
    assert note.type == "audit_reject"
    assert "未通过审核" in note.content
    db.close()


# ---------- AI 代预约通知 ----------

def test_ai_reservation_creates_notification(session_factory, seed):
    db = session_factory()
    alice = db.get(User, seed["alice_id"])
    tools = {t.name: t for t in build_tools(db, alice)}

    import json
    result = json.loads(
        tools["create_lab_reservation"].invoke({
            "lab_id": seed["lab_id"], "date": FUTURE,
            "start_time": "14:00", "end_time": "15:00", "remark": "AI约的",
        })
    )
    assert result["ok"] is True

    note = (
        db.query(Notification)
        .filter_by(user_id=seed["alice_id"], type="reservation")
        .one()
    )
    assert note.related_id == result["reservation_id"]
    assert "AI" in note.title
    db.close()


# ---------- 已读流转 ----------

def test_mark_read_and_read_all(session_factory, seed):
    db = session_factory()
    alice = db.get(User, seed["alice_id"])
    bob = db.get(User, seed["bob_id"])
    # alice 两条 + bob 一条
    for s in ("14:00", "16:00"):
        item = _create(db, alice, seed["lab_id"], start=s, end="17:00" if s == "16:00" else "15:00")
        reservation_service.audit_reservation(db, item.id, 1)
    item_b = _create(db, bob, seed["lab_id"], start="18:00", end="19:00")
    reservation_service.audit_reservation(db, item_b.id, 1)

    assert notification_service.unread_count(db, alice) == 2

    page = notification_service.get_page_list(db, alice, page=1, page_size=10)
    first_id = page.list[0]["id"]
    notification_service.mark_read(db, alice, first_id)
    assert notification_service.unread_count(db, alice) == 1

    notification_service.mark_all_read(db, alice)
    assert notification_service.unread_count(db, alice) == 0
    # bob 的不受影响
    assert notification_service.unread_count(db, bob) == 1
    db.close()


# ---------- 隔离性 ----------

def test_notification_list_is_isolated(session_factory, seed):
    db = session_factory()
    alice = db.get(User, seed["alice_id"])
    bob = db.get(User, seed["bob_id"])
    item = _create(db, bob, seed["lab_id"])
    reservation_service.audit_reservation(db, item.id, 1)

    page = notification_service.get_page_list(db, alice, page=1, page_size=10)
    assert page.total == 0  # alice 看不到 bob 的通知

    page_b = notification_service.get_page_list(db, bob, page=1, page_size=10)
    assert page_b.total == 1
    db.close()
