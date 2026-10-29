"""分页参数归一化（所有列表接口共用）。

为什么需要：
- MySQL 不接受负数 OFFSET（`LIMIT 10 OFFSET -10` 直接 1064 语法错误），
  而 FastAPI 的 `page: int = 1` 不做边界校验，`?page=0` 会打到 500；
- `page_size` 无上限时，一次请求可以把整张表拉出来（慢查询 + 内存放大）。

约定：API 层用 `Query(ge=..., le=...)` 做显式校验（OpenAPI 可见、返回 422），
服务层再兜一层，保证内部调用（Agent 工具、脚本、测试）也不会拼出非法 SQL。
"""

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 10


def normalize_page(page: int | None, page_size: int | None) -> tuple[int, int]:
    """把任意输入收敛为 (page >= 1, 1 <= page_size <= MAX_PAGE_SIZE)。"""
    try:
        page = int(page) if page is not None else 1
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(page_size) if page_size is not None else DEFAULT_PAGE_SIZE
    except (TypeError, ValueError):
        page_size = DEFAULT_PAGE_SIZE
    return max(1, page), min(max(1, page_size), MAX_PAGE_SIZE)
