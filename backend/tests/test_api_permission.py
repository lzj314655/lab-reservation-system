"""API 层权限越权测试（HTTP 视角，覆盖鉴权依赖与路由守卫）

覆盖:
- 未登录 401 / 伪造 token 401
- 学生访问管理员接口 → 业务码 403（实验室/用户/审核）
- 越权读取他人 AI 会话 → 404（不泄露存在性）
- 管理员正常访问（对照，防误杀）
"""

from app.models.ai import AIConversation


def _body(resp):
    return resp.json()


# ---------- 未认证 ----------

def test_no_token_rejected(client, seed):
    resp = client.get("/api/user/info")
    assert resp.status_code == 401


def test_invalid_token_rejected(client, seed):
    resp = client.get("/api/user/info", headers={"Authorization": "Bearer not.a.jwt"})
    assert resp.status_code == 401


# ---------- 学生越权访问管理接口 ----------

def test_student_cannot_create_lab(client, seed, auth):
    resp = client.post(
        "/api/lab",
        json={"name": "hack", "capacity": 10, "status": 1},
        headers=auth(seed["alice_id"]),
    )
    assert resp.status_code == 200
    assert _body(resp)["code"] == 403


def test_student_cannot_delete_user(client, seed, auth):
    resp = client.delete(f"/api/user/{seed['bob_id']}", headers=auth(seed["alice_id"]))
    assert _body(resp)["code"] == 403


def test_student_cannot_list_users(client, seed, auth):
    resp = client.get("/api/user/list", headers=auth(seed["alice_id"]))
    assert _body(resp)["code"] == 403


def test_student_cannot_audit_reservation(client, seed, auth):
    resp = client.put(
        "/api/reservation/1/audit",
        json={"status": 1},
        headers=auth(seed["alice_id"]),
    )
    assert _body(resp)["code"] == 403


# ---------- 数据级越权 ----------

def test_student_cannot_read_others_conversation(client, seed, auth, session_factory):
    # bob 的一条会话
    db = session_factory()
    db.add(AIConversation(user_id=seed["bob_id"], title="bob的私聊"))
    db.commit()
    conv_id = db.query(AIConversation).first().id
    db.close()

    # alice 访问 → 404（不提示"无权限"，避免探测他人会话是否存在）
    resp = client.get(f"/api/ai/conversations/{conv_id}", headers=auth(seed["alice_id"]))
    assert resp.status_code == 404
    # 本人访问正常
    resp = client.get(f"/api/ai/conversations/{conv_id}", headers=auth(seed["bob_id"]))
    assert resp.status_code == 200


# ---------- 管理员对照（防权限规则误杀） ----------

def test_admin_can_create_lab(client, seed, auth):
    resp = client.post(
        "/api/lab",
        json={"name": "管理员新建", "capacity": 10, "status": 1},
        headers=auth(seed["admin_id"]),
    )
    assert _body(resp)["code"] == 200
    assert _body(resp)["data"]["name"] == "管理员新建"


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["db"] == "up"
