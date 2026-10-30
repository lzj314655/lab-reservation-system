# 技术栈详解

> 版本快照：2026-10-30 ｜ 版本以 [`backend/requirements.txt`](../backend/requirements.txt)、[`frontend/package-lock.json`](../frontend/package-lock.json)、Dockerfile 和 CI 配置为准。
>
> 本文只记录**代码里实际使用**的技术与版本，不包含规划中的选型；未使用的依赖不会出现在矩阵里。

## 1. 一页总览

| 层级 | 技术 | 作用 |
| --- | --- | --- |
| 接入层 | nginx（alpine） | 托管 Vue 构建产物；反代 `/api`、`/uploads`；为 SSE 关闭代理缓冲 |
| 前端 | Vue 3 + Vite + Element Plus + ECharts + Axios | SPA、管理后台组件、图表、REST/SSE 请求 |
| 应用层 | FastAPI + Uvicorn + Pydantic 2 | REST API、参数校验、SSE 流式响应、OpenAPI 文档 |
| 业务层 | Service 模块（预约/审核/通知/统计/Agent） | 领域规则、事务边界、状态机 |
| Agent | LangGraph + langchain-openai | ReAct 循环、工具调用、多轮对话编排 |
| 检索增强 | ChromaDB + sentence-transformers + bge-small-zh-v1.5 | 本地向量库与中文嵌入模型 |
| 数据层 | MySQL 8.0 + SQLAlchemy 2.0 + PyMySQL + Alembic | 持久化、行锁并发控制、生成列唯一索引、迁移 |
| 调度 | APScheduler 3.x | 每分钟扫描过期预约，`GET_LOCK` 做多实例互斥 |
| 鉴权 | PyJWT（HS256）+ bcrypt | 无状态登录态、密码哈希 |
| 部署 | Docker 多阶段构建 + Docker Compose | 后端/前端/MySQL 一键启动 |
| 质量 | ruff + pytest + pytest-cov + Locust + GitHub Actions | 静态检查、37 个后端测试、压测、CI |

```mermaid
flowchart TB
    subgraph Client["浏览器"]
        V["Vue 3 SPA<br/>Element Plus + ECharts"]
    end

    subgraph Edge["接入层"]
        N["nginx :8080<br/>静态资源 / 反向代理"]
    end

    subgraph App["应用层（FastAPI :8000）"]
        F["API 路由层"]
        S["Service 业务层"]
        G["LangGraph Agent"]
    end

    subgraph Data["数据与模型"]
        M[("MySQL 8.0")]
        C[("ChromaDB<br/>lab_kb")]
        E["bge-small-zh<br/>嵌入模型"]
        L["OpenAI 兼容 LLM"]
    end

    V --> N
    N -->|"/api · /uploads"| F
    F --> S
    S --> M
    F --> G
    G --> S
    G --> C
    C --> E
    G --> L
```

## 2. 版本矩阵

### 2.1 运行时与基础设施

| 组件 | 项目基线 | 本地/镜像实测 | 说明 |
| --- | --- | --- | --- |
| Python | **3.12**（`.python-version`、Docker、CI） | 本地 3.14.7 | 代码兼容 3.12+；部署以 3.12 为准 |
| Node.js | **22.18**（`.node-version`、CI `node:22`） | 本地 25.2.1 | `package.json` 的 `engines` 允许 `^22.18 || >=24.12` |
| npm | 随 Node 22 提供 | 本地 11.6.2 | 使用 `npm ci` 保证 lock 一致 |
| MySQL | **8.0**（`mysql:8.0` 镜像） | 本地 8.0.43 | 依赖生成列、`SELECT ... FOR UPDATE`、`GET_LOCK` |
| nginx | `nginx:alpine` | — | 生产前端镜像运行时 |
| Docker | Docker Compose v2 | Engine 29.6.2 / Compose 5.3.1 | 单机部署，不引入 K8s |
| CI | GitHub Actions `ubuntu-latest` | — | 后端、前端、Docker 三段流水线 |

### 2.2 后端依赖（直接依赖，全部精确锁定）

| 依赖 | 版本 | 用途 | 关键点 |
| --- | --- | --- | --- |
| fastapi | `0.115.13` | Web 框架 | 原生 async、`StreamingResponse` 做 SSE、自动 OpenAPI |
| uvicorn | `0.34.0` | ASGI Server | 生产/本地启动入口 |
| sqlalchemy | `2.0.41` | ORM | 2.0 风格 `Mapped` / `mapped_column`、`select`、事务 |
| pymysql | `1.1.1` | MySQL 驱动 | 同步驱动；SQLAlchemy 连接 MySQL |
| pydantic-settings | `2.7.1` | 配置管理 | 从 `.env` 读取 `DATABASE_URL`、JWT、LLM、CORS |
| bcrypt | `5.0.0` | 密码哈希 | 注册/改密；不保存明文 |
| PyJWT | `2.13.0` | JWT | HS256；`exp` 过期校验 |
| python-multipart | `0.0.32` | 文件上传 | 解析 `UploadFile` |
| cryptography | `50.0.2` | 加密基础库 | 为后续 RS256/HTTPS 场景预留；当前 HS256 不直接调用 |
| openai | `3.31.0` | LLM SDK | 由 `langchain-openai` 使用；锁定版本避免协议漂移 |
| langgraph | `1.2.15` | Agent 编排 | `StateGraph` + `ToolNode` + `tools_condition` |
| langchain-openai | `1.7.2` | Chat 模型适配 | `ChatOpenAI`，兼容 OpenAI 协议的服务端 |
| langchain-core | `1.6.11` | 消息/工具抽象 | `HumanMessage`、`AIMessage`、`@tool` |
| chromadb | `1.5.9` | 本地向量库 | `PersistentClient`，零额外服务 |
| sentence-transformers | `6.0.1` | 嵌入模型运行时 | 加载 `BAAI/bge-small-zh-v1.5` |
| alembic | `1.20.1` | 数据库迁移 | 版本化 schema；`bootstrap_db.py` 负责全新库 |
| APScheduler | `3.11.3` | 进程内定时任务 | 60s 扫描；`coalesce`、`jitter`、`max_instances=1` |

### 2.3 关键传递依赖（由上述依赖解析）

| 依赖 | 本机/构建时版本 | 说明 |
| --- | --- | --- |
| starlette | `0.46.2` | FastAPI 底层；SSE/中间件 |
| pydantic | `2.14.x` | 请求/响应模型、校验 |
| torch | Docker **`2.15.0+cpu`**；本机 `2.14.1` | Dockerfile 显式装 CPU wheel，避免 CUDA 依赖 |
| transformers | 本机 `5.20.0`；Docker 构建时 `5.21.x` | 由 sentence-transformers 约束，未直接锁定 |
| tokenizers | `0.23.3` | 分词 |
| onnxruntime | `1.31.x` | Chroma 默认嵌入/推理相关依赖 |
| numpy | `2.5.4` | 数值计算 |
| langgraph-checkpoint | `4.3.x` | LangGraph 状态持久化依赖（本项目未启用 checkpointer） |
| langgraph-prebuilt | `1.1.1` | `ToolNode` 等预置组件 |

> 说明：直接依赖全部固定版本；传递依赖由 pip 解析，本机与 Linux 镜像可能差一个小版本（例如 transformers）。需要完全可复现时，可按 `requirements.in` 的说明用 `pip-compile` 生成含传递依赖的完整锁。

### 2.4 前端依赖

| 依赖 | 版本（lock 解析） | 用途 |
| --- | --- | --- |
| vue | `3.5.43` | 前端框架，Composition API + `<script setup>` |
| vue-router | `5.4.0` | 路由、登录/角色守卫 |
| element-plus | `2.14.7` | 管理后台组件库（深青主题定制） |
| @element-plus/icons-vue | `2.3.2` | 图标 |
| echarts | `6.1.0` | 首页统计图（趋势、排行、状态分布） |
| axios | `1.20.0` | REST 请求、统一拦截器、401 处理 |
| vite | `8.3.4` | 开发服务器与生产构建 |
| @vitejs/plugin-vue | `6.0.10` | Vue SFC 编译 |
| vite-plugin-vue-devtools | `8.2.1` | 开发期调试 |
| prettier | `3.9.6` | 代码格式化 |

前端**没有**使用 Pinia/Vuex：页面状态以组件内 `ref/reactive` 为主，登录态放 `localStorage`（`token`、`userInfo`）。这是当前规模下的简化，不是通用最佳实践。

### 2.5 测试、质量与压测

| 工具 | 版本 | 用途 |
| --- | --- | --- |
| pytest | `9.1.1` | 后端测试（真实 MySQL） |
| pytest-cov | `7.1.0` | 覆盖率统计（CI 上传 XML，暂未设阈值） |
| ruff | `0.17.2` | 静态检查（E4/E7/E9/F，line-length 100） |
| locust | `2.47.0` | 预约并发压测脚本 |
| GitHub Actions | — | ruff + pytest + 迁移检查 + 前端构建 + Docker 构建 |
| PowerShell / Makefile | — | 本地一键脚本：`bootstrap` / `check` / `dev` |

## 3. 后端技术栈与实现

### 3.1 分层结构

| 目录 | 技术职责 |
| --- | --- |
| `backend/app/api/` | FastAPI 路由、依赖注入、HTTP/SSE 边界 |
| `backend/app/services/` | 业务规则：预约冲突、审核状态机、通知、统计、Agent 工具 |
| `backend/app/models/` | SQLAlchemy 2.0 ORM 模型与索引/约束 |
| `backend/app/schemas/` | Pydantic 请求/响应模型（含日期、长度校验） |
| `backend/app/common/` | 统一响应 `{code,message,data}`、异常处理、分页归一化 |
| `backend/app/dependencies/` | JWT 登录态、管理员权限依赖 |
| `backend/app/utils/` | bcrypt 密码、JWT 编解码 |
| `backend/app/config.py` | pydantic-settings 读取 `.env` 与 CORS 配置 |
| `backend/app/main.py` | FastAPI 装配、异常处理器、静态 `/uploads`、`/health`、lifespan |
| `backend/app/scheduler.py` | APScheduler 生命周期与任务注册 |
| `backend/migrations/` | Alembic 环境与版本脚本 |

### 3.2 鉴权与安全

- **JWT**：`HS256`，默认 24 小时过期；token 同时用于 REST 与 SSE。前端 `axios` 拦截器统一加 `Authorization: Bearer`，401 清理本地登录态并跳登录页。
- **密码**：`bcrypt` 哈希；登录失败按 `(IP, 用户名)` 限流，15 分钟 5 次，成功即清零（进程内实现，多 worker 不共享）。
- **角色**：`student` / `admin`；管理接口通过 `get_current_admin` 二次校验，前端路由守卫只做体验层的提前拦截。
- **上传**：必须登录；后缀白名单（图片/PDF/Office/ZIP）；流式写入，单文件 100 MB；UUID 重命名；`/uploads` 静态托管。
- **CORS**：`CORS_ORIGINS` 环境变量，逗号分隔；默认覆盖 Vite 5173。
- **Agent**：身份不通过工具参数传入，而是 `build_tools(db, current_user)` 的闭包变量；参数、配额、审计见第 4 节。

### 3.3 数据层与并发控制

- **MySQL 8.0 特性**：
  - `SELECT ... FROM labs WHERE id=? FOR UPDATE` 父行锁，让同一实验室的预约写入串行；
  - `active_marker` STORED 生成列（`status IN (0,1)` 时为 1，否则 NULL），配合唯一索引实现"仅活跃预约唯一"；
  - `equip_key` 生成列把实验室级预约的 `equipment_id=NULL` 映射为 0，堵住 NULL 不参与唯一冲突的漏洞；
  - `uk_res_active_slot` 唯一索引兜底；`ix_res_lab_date` 支撑冲突查询；
  - `GET_LOCK('lab_expire_scan', 0)` 做多实例定时任务互斥。
- **事务与重试**：1213（死锁）/1205（锁等待超时）指数退避，最多 3 次；1062 唯一键冲突转业务提示。
- **状态机**：0 待审核、1 已通过、2 已拒绝、3 已取消、4 已完成、5 爽约（预留）；审核/取消使用 `FOR UPDATE`，避免与定时扫描/并发审核互相覆盖。
- **日期与时间**：`date` 为 `YYYY-MM-DD` 字符串，`start_time/end_time` 为 `HH:MM` 字符串；入口用 Pydantic 校验格式，服务层再归一化，保证字典序比较正确。
- **迁移**：Alembic 版本化；全新库走 `scripts/bootstrap_db.py`（`create_all` + stamp），已有库走 `alembic upgrade head`。

详细设计与压测数据见 [预约并发防超订](reservation-concurrency.md)。

### 3.4 API 约定

- 统一前缀 `/api`，模块：`auth`、`user`、`lab`、`equipment`、`reservation`、`files`、`ai`、`notification`、`stats`。
- 统一响应：`{ "code": 200, "message": "...", "data": ... }`；业务异常返回 HTTP 200 + 业务 `code`（如 403/429），参数校验返回 422，未认证返回 401。
- 分页参数服务层统一收敛：`page >= 1`、`1 <= page_size <= 100`，避免负 OFFSET 与全表拉取。
- 健康检查：`GET /health` 执行 `SELECT 1`，供 Docker healthcheck 与编排依赖使用。

## 4. AI 技术栈

### 4.1 模型接入

- 使用 `langchain_openai.ChatOpenAI`，对接任意 **OpenAI 兼容**服务；配置项为 `LLM_API_KEY`、`LLM_MODEL`、`LLM_BASE_URL`。
- 关键参数：`temperature=0`、`streaming=True`、`max_tokens=1024`、`timeout=60`、`max_retries=1`、`bind_tools(...)`。
- 单轮图执行 `recursion_limit=10`，单轮工具调用预算 8 次；超出即中断并返回提示，防注入/循环空转。

### 4.2 LangGraph 编排

```mermaid
flowchart LR
    START([用户消息]) --> A["agent 节点<br/>ChatOpenAI.bind_tools"]
    A -->|"有 tool_calls"| T["ToolNode<br/>执行工具"]
    T --> A
    A -->|"无 tool_calls"| DONE([流式回复])
```

- 图：`StateGraph(MessagesState)`；节点 `agent`、`tools`；边 `START → agent`、`agent → tools_condition`、`tools → agent`。
- 对话历史由前端随请求携带，后端 `_build_history` 做角色白名单（仅 user/assistant）、最多 20 条、单条 2000 字截断；不使用 LangGraph checkpointer，历史落库在 `ai_conversations` / `ai_messages`。
- 流式：`agent.astream_events(version="v2")` 转 SSE，前端 `fetch + ReadableStream` 解析（不能用 `EventSource`，因为需要自定义 `Authorization` 头）。

### 4.3 工具集与硬约束

| 工具 | 作用 | 关键约束 |
| --- | --- | --- |
| `search_lab_docs` | 检索知识库 | 返回 `context + refs`，`<kb_docs>` 包裹；检索结果视为数据而非指令 |
| `list_open_labs` | 查开放实验室 | 分页上限 10 |
| `list_lab_equipments` | 查实验室设备 | 分页上限 10 |
| `create_lab_reservation` | 创建预约 | 日期今起 30 天内、单次 ≤4 小时、备注 ≤100 字、待审核 ≤10 条 |
| `cancel_lab_reservation` | 取消预约 | 服务层强制校验归属；越权单独打审计标记 |
| `get_today` | 今天日期 | 供"明天/后天"换算 |

- 工具身份来自 JWT 闭包，LLM 无法指定 `user_id`；
- 所有写操作记录 `agent_audit_logs`（独立会话提交，业务回滚不丢审计）；
- 每日 AI 限额 200 条**用户提问**（assistant 回复不占额度）。

详细威胁模型见 [Agent 安全加固](agent-security.md)。

### 4.4 RAG 链路

- 语料：`backend/data/kb/*.md`（预约规则、安全规范、开放时间、设备使用）。
- 向量库：ChromaDB `PersistentClient`，持久化目录 `backend/data/chroma`，集合名 `lab_kb`；首次启动懒加载并向量化，启动后台线程预热。
- 嵌入模型：`BAAI/bge-small-zh-v1.5`（中文小模型，CPU 可跑）；Docker 构建期预热，运行时 `HF_HUB_OFFLINE=1`。
- 检索：`search_refs(query, k=3)`；相关度 `score = 1 / (1 + distance)`；返回 `source`、`content`、`snippet`、`score`，前端展示引用来源。
- 评测：`backend/scripts/eval_rag.py` + `data/kb/eval.jsonl`（Recall/MRR），`eval_report.md` 记录结果。

### 4.5 SSE 事件协议

| 事件 | 含义 |
| --- | --- |
| `meta` | 会话 ID（新建会话时下发） |
| `status` | "正在思考..." 等状态 |
| `tool_start` / `tool_end` | 工具调用开始/结束（前端展示进度） |
| `kb_refs` | 知识库引用来源 |
| `token` | 逐字回复 |
| `done` | 本轮结束 |
| `error` | 业务/系统错误 |

## 5. 前端技术栈与实现

- **框架**：Vue 3 Composition API + `<script setup>`；页面在 `src/views/`，主框架在 `src/layout/Layout.vue`。
- **组件库**：Element Plus；`ReserveDialog` 作为预约弹窗复用组件；主题变量在 `src/assets/css/global.css`。
- **图表**：ECharts 6.1.0；首页趋势、实验室排行、审核通过率、个人状态分布。
- **请求**：Axios 实例统一 `baseURL`、超时 30s、请求头注入 token；响应拦截器统一处理 401 与错误消息。
- **SSE**：`fetch` + `TextDecoder` + 手写事件分帧；逐字渲染、工具进度、知识库引用、停止生成（`AbortController`）。
- **路由**：`vue-router` 5.x；`beforeEach` 做登录态与管理员路径守卫（`ADMIN_PATHS`）。
- **构建**：Vite 8；开发时 `/api`、`/uploads` 代理到 `127.0.0.1:8000`；生产构建 `VITE_API_BASE_URL` 留空，由 nginx 同源反代。
- **代码风格**：Prettier；当前没有 ESLint/Vitest（见第 8 节）。

## 6. 部署与工程化

### 6.1 Docker 拓扑

配置文件：[`backend/Dockerfile`](../backend/Dockerfile)、[`frontend/Dockerfile`](../frontend/Dockerfile)、[`docker-compose.yml`](../docker-compose.yml)、[`docker-compose.hostdb.yml`](../docker-compose.hostdb.yml)、[`nginx.conf`](../frontend/nginx.conf)。

| 服务 | 镜像/构建 | 端口 | 说明 |
| --- | --- | --- | --- |
| `mysql` | `mysql:8.0` | 宿主 `3307 → 3306` | utf8mb4；健康检查；数据卷 `mysql-data` |
| `backend` | `backend/Dockerfile` 多阶段 | `8000` | 非 root `app` 用户；启动前 `bootstrap_db.py`；卷 `chroma-data`、`uploads` |
| `frontend` | `frontend/Dockerfile` 多阶段 | `8080 → 80` | Node 构建，nginx 托管 + 反代；健康检查 wget |
| `redis` | `redis:7-alpine`（profile `redis`） | — | **未使用**；保留 profile，不参与启动 |

后端 Dockerfile 的关键优化：

- **CPU-only torch**：`torch==2.15.0+cpu` 从 PyTorch CPU index 安装，避免默认 CUDA/cuDNN 依赖把镜像从约 8 GB 压到约 **2.8 GB**；
- 依赖与模型预热合并到同一构建阶段，torch 只安装一次；
- bge-small 模型构建期下载并复制到运行用户 HF 缓存，运行时离线；
- 最终镜像只带 `app/`、`scripts/`、`migrations/`、`data/kb/`，不带测试与虚拟环境。

### 6.2 nginx

- SPA 路由回退：`try_files $uri $uri/ /index.html`；
- `/api/` 反代 `backend:8000`；`/uploads/` 反代后端静态目录；
- SSE：`proxy_buffering off`、`proxy_cache off`、`read/send_timeout 300s`；
- 静态资源长缓存（Vite 哈希产物）。

### 6.3 CI 流水线

配置文件：[`.github/workflows/ci.yml`](../.github/workflows/ci.yml)。

| Job | 内容 |
| --- | --- |
| Backend | 安装锁定依赖；`ruff check`；全新库 `bootstrap_db.py` + `alembic check`；`pytest --cov` 并上传覆盖率 |
| Frontend | `npm ci` + `npm run build` |
| Docker | 构建 backend/frontend 镜像（依赖前两个 Job） |

### 6.4 本地开发

- `scripts/bootstrap.ps1`：创建/复用 venv、安装锁定依赖、生成 `.env`、可选拉起 MySQL、执行 `bootstrap_db.py`。
- `scripts/check.ps1`：ruff + pytest（+ 前端 build）。
- `scripts/dev.ps1`：两个窗口启动 uvicorn `--reload` 与 Vite。
- `Makefile`：`make bootstrap` / `dev` / `check` 的薄封装。
- `.gitattributes` 统一 LF；`.editorconfig` 统一 UTF-8/缩进；`.gitignore` 排除 `.env`、`.venv`、`.ssh`、`node_modules`、`dist`、`uploads`、`data/chroma`。

### 6.5 配置项

| 变量 | 用途 |
| --- | --- |
| `DATABASE_URL` | `mysql+pymysql://user:pass@host:3306/db` |
| `JWT_SECRET_KEY` / `JWT_EXPIRE_HOURS` / `JWT_ALGORITHM` | 登录态签名与过期 |
| `LLM_API_KEY` / `LLM_MODEL` / `LLM_BASE_URL` | OpenAI 兼容模型接入 |
| `CORS_ORIGINS` | 允许跨域的前端地址，逗号分隔 |
| `MYSQL_ROOT_PASSWORD` / `MYSQL_DATABASE` | Compose 内 MySQL 与后端连接串插值 |

## 7. 选型权衡

| 决策 | 备选 | 选择理由 | 代价/边界 |
| --- | --- | --- | --- |
| FastAPI | Flask / Django | 原生 async 与 SSE、Pydantic 校验、自动 OpenAPI；适合 API + Agent 流式 | 生态不如 Django 全；需要自己搭分层 |
| SQLAlchemy 2.0 | 原生 SQL / Django ORM | 类型化模型、关系加载、事务与锁表达清晰 | 学习曲线；复杂查询仍需手写 SQL |
| MySQL 8.0 | PostgreSQL | 现有环境是 MySQL；生成列 + 唯一索引可模拟部分索引；`GET_LOCK` 现成 | 无部分索引，需要生成列技巧；字符串存日期 |
| 父行锁 + 唯一索引 | Redis 分布式锁 | 单库事务内解决，锁顺序全局一致，无额外组件；DB 约束最终兜底 | 单实验室写入串行，吞吐约百级 TPS |
| LangGraph | 直接 function calling / CrewAI | 显式状态图、ToolNode、递归/工具预算可控；便于讲清 Agent 流程 | 多一层抽象；版本升级需关注 API |
| ChromaDB 嵌入式 | Milvus / pgvector | 语料只有 4 篇 Markdown，嵌入式零运维、构建简单 | 不适合大规模/多进程并发；扩展需替换 |
| sentence-transformers + bge-small | OpenAI Embeddings | 本地 CPU 可跑、中文效果好、无额外 API 成本 | 镜像变大（CPU torch）；首启需模型缓存 |
| Element Plus | Ant Design Vue / Naive UI | 后台组件齐全、主题可定制、团队熟悉 | 包体较大；样式定制需覆盖变量 |
| ECharts | Chart.js | 中文文档、图表类型丰富、适配仪表盘 | 包体较大；按需引入尚未做 |
| 无 Pinia | Pinia / Vuex | 页面状态简单，组件内状态 + localStorage 足够 | 跨页共享复杂后需引入 |
| 无 Redis/Celery | Redis + Celery | 定时任务只是每分钟幂等 SQL；单机部署 | 多实例靠 `GET_LOCK`；任务重试/延迟能力弱 |
| JWT 无状态 | Session + Redis | API/SSE 友好、无需会话存储 | 无法主动吊销单个 token；改密后旧 token 仍有效至过期 |
| Docker Compose | Kubernetes | 单机部署，成本最低 | 无自动扩缩容/滚动发布 |

## 8. 兼容性与已知限制

### 8.1 版本兼容

- **Python**：部署/CI 为 3.12，本机为 3.14.7。代码未使用 3.13/3.14 独有语法；提交前以 CI 的 3.12 行为为准。
- **torch**：Docker 固定 `2.15.0+cpu`，本机为 2.14.1（Windows）。应用只用 CPU embedding，测试不加载模型；升级 `sentence-transformers` 时需同步检查 `TORCH_VERSION` 构建参数。
- **Node**：CI 为 22，本机为 25.2.1；`engines` 允许 `^22.18 || >=24.12`。Vite 8 要求较新的 Node，保持 22.18+。
- **MySQL**：必须 8.0+（生成列、`GET_LOCK`）；SQLite 无法覆盖并发测试，测试明确使用真实 MySQL。
- **换行/编码**：仓库统一 LF、UTF-8；Windows 下避免 `core.autocrlf` 改写。

### 8.2 已知限制

- **迁移 baseline**：首条迁移假设表已存在，`alembic upgrade head` 不能从零建库；全新库走 `bootstrap_db.py`。因此 `alembic check` 只能校验 `env.py` 元数据完整性，检测不了"模型改了但没写迁移"。
- **覆盖率**：当前 37 个用例，`pytest --cov=app` 覆盖率约 **59%**；CI 上传覆盖率但未设阈值，建议逐步提高到 70%。
- **前端质量门禁**：只有 Prettier；没有 ESLint、Vitest/组件测试。
- **限流**：登录失败限流是进程内计数，多 worker 不共享；AI 每日限额直接查数据库，天然共享。
- **Chroma/调度**：Chroma 为嵌入式单进程；APScheduler 每个 worker 都会注册，但 `GET_LOCK` 保证同一时刻只有一个执行。
- **SSE 超时**：nginx `proxy_read_timeout 300s`；超长生成会被切断。
- **LLM**：依赖外部 OpenAI 兼容服务；无离线降级；Key 通过环境变量注入。
- **部署**：单机 Compose，无自动扩缩容；标准 compose 需要能拉取 `mysql:8.0`，受限网络可用 `docker-compose.hostdb.yml` 复用宿主 MySQL。
- **包体**：未做 ECharts/Element Plus 按需引入；前端首屏资源可进一步优化。

## 9. 升级指南

### 9.1 后端依赖

1. 修改 [`backend/requirements.in`](../backend/requirements.in)（直接依赖）；
2. 可选：`pip-compile requirements.in -o requirements.txt` 生成完整锁；
3. 在 Python 3.12 环境安装并跑 `pytest` / `ruff`；
4. 如果升级 `sentence-transformers` 或 `torch`，同步调整 Dockerfile 的 `ARG TORCH_VERSION` 并重建镜像；
5. 更新 `requirements-dev.txt` 中测试工具版本。

### 9.2 前端依赖

1. 修改 `package.json` 后在 Node 22 环境执行 `npm install`，提交 `package-lock.json`；
2. 跑 `npm run build`；后续接入 ESLint/Vitest 后一并跑；
3. 确认 `engines` 与 `.node-version` 一致。

### 9.3 数据库

1. `alembic revision --autogenerate -m "..."`；
2. 人工 review 生成脚本（生成列、唯一索引、数据回填尤其要检查）；
3. 更新 `backend/scripts/bootstrap_db.py` 的 `ALEMBIC_HEAD`；
4. 在全新库上验证 `bootstrap_db.py` + `alembic check`；
5. 已有库执行 `alembic upgrade head` 前先备份。

### 9.4 嵌入模型/知识库

- 更换嵌入模型需要重建向量库：删除 `backend/data/chroma`（Docker 为 `lab-reservation_chroma-data` 卷）后重启，或提供重建脚本；
- 语料更新（`data/kb/*.md`）后需重新向量化，当前没有管理端重建接口。

## 10. 一页速查

> **FastAPI + SQLAlchemy 2.0 + MySQL 8.0** 做业务与并发控制；**Vue 3 + Element Plus + ECharts** 做管理端；**LangGraph + ChromaDB + bge-small-zh** 做 RAG Agent；**Docker Compose + nginx + GitHub Actions** 做部署与质量门禁。

关键数字：**37 个后端测试**、**50 并发 / 10,040 次请求 0 超订 0 死锁 0 5xx**、**后端镜像约 2.8 GB**、**AI 单轮工具预算 8 次、每日 200 条用户提问**。
