"""登录失败限流（进程内实现）。

为什么需要：`/api/auth/login` 之前没有任何失败次数限制，配合 bcrypt 虽然单次
验证较慢，但仍可被脚本持续爆破，也会白烧 CPU。

实现取舍：
- 进程内计数足够单实例部署；多 worker / 多实例时各进程独立计数，
  全局生效需要换 Redis 计数器（接口不变，替换存储即可）。
- 只记录"账号密码错误"，登录成功立即清零；按 (IP, 用户名) 维度计数，
  避免 A 用户输错把 B 用户锁死。
"""

import threading
import time

MAX_FAILURES = 5           # 窗口内允许的失败次数
WINDOW_SECONDS = 15 * 60   # 计数窗口
_MAX_KEYS = 10_000         # 防内存无限增长的上限

_lock = threading.Lock()
_failures: dict[str, list[float]] = {}


def _key(ip: str, username: str) -> str:
    return f"{ip or '-'}|{(username or '').strip().lower()}"


def _prune(stamps: list[float], now: float) -> list[float]:
    return [t for t in stamps if now - t < WINDOW_SECONDS]


def is_blocked(ip: str, username: str) -> bool:
    """该 (IP, 用户名) 是否已触发限流"""
    now = time.monotonic()
    with _lock:
        key = _key(ip, username)
        stamps = _prune(_failures.get(key, []), now)
        if stamps:
            _failures[key] = stamps
        else:
            _failures.pop(key, None)
        return len(stamps) >= MAX_FAILURES


def record_failure(ip: str, username: str) -> None:
    now = time.monotonic()
    with _lock:
        key = _key(ip, username)
        if key not in _failures and len(_failures) >= _MAX_KEYS:
            # 极端情况下清理一轮过期键，避免被随机用户名打爆内存
            for k in [k for k, v in _failures.items() if not _prune(v, now)]:
                _failures.pop(k, None)
        stamps = _prune(_failures.get(key, []), now)
        stamps.append(now)
        _failures[key] = stamps


def reset(ip: str, username: str) -> None:
    with _lock:
        _failures.pop(_key(ip, username), None)


def reset_all() -> None:
    """测试用：清空所有计数"""
    with _lock:
        _failures.clear()
