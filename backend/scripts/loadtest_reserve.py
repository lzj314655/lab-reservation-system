"""预约创建接口压测脚本（Locust）

用法（在 backend 目录、后端 venv 下）:
    python -m locust -f scripts/loadtest_reserve.py --host http://127.0.0.1:8000
    # 打开 http://localhost:8089 配置并发数

无界面模式（出 CSV 报告）:
    python -m locust -f scripts/loadtest_reserve.py --headless \\
        -u 50 -r 10 -t 2m --host http://127.0.0.1:8000 --csv loadtest_report

流量模型:
    - 随机时段(70%): 随机实验室+未来40天内随机时段 —— 干净路径，测 QPS/P95
    - 热门时段(30%): 固定实验室+固定时段 —— 首单后全部走冲突路径，测锁排队与拒绝吞吐

关注指标:
    - QPS / P95（分接口看 "随机时段" 与 "热门时段" 两条 name）
    - 冲突率 = conflict / (success + conflict)，热门时段任务应接近 100% 且全部为业务提示
    - 错误数（HTTP 500 或非预期业务码）必须为 0
    - 死锁重试次数: 服务端日志 grep -c "预约写入遇到锁冲突"（父行锁方案下预期为 0）
    - DB 侧: SHOW GLOBAL STATUS LIKE 'Innodb_row_lock%'; SHOW ENGINE INNODB STATUS 的
      LATEST DETECTED DEADLOCK 段应为空

说明: token 直接用后端 JWT 工具铸造（压测聚焦预约链路，认证层不在本次基准范围）；
      压测产生的预约 remark 均以 "loadtest" 开头，结束后可按前缀清理。
"""

import random
from datetime import date, timedelta

from locust import HttpUser, between, events, task

from app.utils.jwt import create_access_token

# 压测使用的学生账号 user_id（对应库中 bbb）
LOADTEST_USER_ID = 2

STATS = {"success": 0, "conflict": 0, "error": 0}

CONFLICT_MSGS = ("该时段已预约", "手慢了，该时段刚被他人预约")


def _to_minutes(hhmm):
    h, m = str(hhmm).split(":")[:2]
    return int(h) * 60 + int(m)


def _fmt(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


@events.test_stop.add_listener
def _summary(environment, **_kwargs):
    total = STATS["success"] + STATS["conflict"] + STATS["error"]
    if total == 0:
        return
    conflict_rate = STATS["conflict"] / total * 100
    print(
        f"\n===== 预约压测汇总 =====\n"
        f"总请求:   {total}\n"
        f"预约成功: {STATS['success']}\n"
        f"业务冲突: {STATS['conflict']} (冲突率 {conflict_rate:.1f}%)\n"
        f"错误:     {STATS['error']} (必须为 0)\n"
        f"死锁重试: 请查看服务端日志 grep -c '预约写入遇到锁冲突'\n"
    )


class ReserveUser(HttpUser):
    wait_time = between(0.05, 0.2)

    def on_start(self):
        token = create_access_token(LOADTEST_USER_ID)
        self.client.headers = {"Authorization": f"Bearer {token}"}
        with self.client.get(
            "/api/lab/list?page=1&page_size=50", catch_response=True
        ) as resp:
            body = resp.json()
            rows = (body.get("data") or {}).get("list") or []
            self.lab_ids = [r["id"] for r in rows] or [6]
            # 各实验室开放窗口(分钟)，随机时段必须完整落在窗口内，避免被业务校验拒绝
            self.lab_windows = {
                r["id"]: (
                    _to_minutes(r.get("open_time") or "08:00"),
                    _to_minutes(r.get("close_time") or "22:00"),
                )
                for r in rows
            }

    def _book(self, name, payload):
        with self.client.post(
            "/api/reservation", json=payload, catch_response=True, name=name
        ) as resp:
            try:
                body = resp.json()
            except Exception:  # noqa: BLE001
                STATS["error"] += 1
                resp.failure(f"HTTP {resp.status_code}: 响应非 JSON")
                return
            if body.get("code") == 200:
                STATS["success"] += 1
                resp.success()
            elif body.get("message") in CONFLICT_MSGS:
                # 冲突是正常业务结果，计入响应统计但单独计数
                STATS["conflict"] += 1
                resp.success()
            else:
                STATS["error"] += 1
                resp.failure(f"code={body.get('code')} msg={body.get('message')}")

    @task(7)
    def book_random_slot(self):
        """干净路径：随机实验室 + 开放窗口内的随机 1 小时时段"""
        d = (date.today() + timedelta(days=random.randint(1, 40))).isoformat()
        lab_id = random.choice(self.lab_ids)
        open_m, close_m = self.lab_windows.get(lab_id, (8 * 60, 22 * 60))
        start = random.randrange(open_m, max(open_m + 60, close_m - 60 + 1), 30)
        self._book(
            "POST /api/reservation [随机时段]",
            {
                "lab_id": lab_id,
                "date": d,
                "start_time": _fmt(start),
                "end_time": _fmt(start + 60),
                "remark": "loadtest-rand",
            },
        )

    @task(3)
    def book_hot_slot(self):
        """争抢路径：固定实验室 + 固定热门时段，首单后全部冲突"""
        d = (date.today() + timedelta(days=7)).isoformat()
        self._book(
            "POST /api/reservation [热门时段]",
            {
                "lab_id": self.lab_ids[0],
                "date": d,
                "start_time": "10:00",
                "end_time": "12:00",
                "remark": "loadtest-hot",
            },
        )
