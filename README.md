# 智能实验室预约系统

<p>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Vue-3.5-4FC08D?logo=vuedotjs&logoColor=white" alt="Vue">
  <img src="https://img.shields.io/badge/LangGraph-Agent-1C3C3C" alt="LangGraph">
  <img src="https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white" alt="MySQL">
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white" alt="Docker">
</p>

一个基于 **FastAPI + Vue 3 + LangGraph Agent** 的实验室预约管理系统：实验室 / 设备预约与审核、周视图日历、站内通知、数据统计，内置基于 RAG 的 AI 智能助手，一句话完成查规则、查空闲、提交预约。

[快速开始](#quickstart) · [界面预览](#screenshots) · [系统架构](#architecture) · [功能总览](#features) · [技术深潜](#docs)

![首页仪表盘](docs/screenshots/dashboard.png)

## 核心亮点

- **0 超订 / 0 死锁**：预约写入走 MySQL 父行锁，配合 STORED 生成列唯一索引兜底与 1213/1205 退避重试；Locust 50 并发 10,040 次请求，0 超订、0 死锁、0 个 5xx。
- **Agent 六层防护**：身份取自 JWT 闭包、历史消息清洗、参数校验、Agent 配额、提示词注入防护、工具调用审计；越权取消 / 注入用例均有确定性测试。
- **完整业务闭环**：注册登录 → 实验室 / 设备预约 → 管理员审核 → 日历占用 → 站内通知 → 统计看板 → AI 代预约，配个人中心与文件上传。
- **工程化底座**：37 个后端测试、ruff、Alembic 迁移、Docker Compose 一键启动、GitHub Actions CI，另附两篇技术深潜文档。

<a name="screenshots"></a>
## 界面预览

<p align="center">
  <img src="docs/screenshots/login.png" width="49%" alt="登录页">
  <img src="docs/screenshots/lab-calendar.png" width="49%" alt="预约日历">
</p>
<p align="center">
  <img src="docs/screenshots/lab-list.png" width="49%" alt="实验室列表">
  <img src="docs/screenshots/ai-chat.png" width="49%" alt="AI 智能助手">
</p>

<a name="architecture"></a>
## 系统架构

```mermaid
flowchart LR
    U["浏览器<br/>Vue 3 + Element Plus"] --> N["nginx :8080"]
    N -->|"静态资源"| U
    N -->|"/api · /uploads"| B["FastAPI :8000"]
    B --> S["Service 层<br/>并发控制 · 通知 · 统计"]
    S --> M[("MySQL 8.0")]
    S --> C[("ChromaDB<br/>知识库")]
    B --> A["LangGraph Agent<br/>ReAct + ToolNode"]
    A --> T["工具集<br/>查实验室 / 查设备 / 建预约 / 取消 / 检索"]
    T --> S
    A --> L["OpenAI 兼容 LLM<br/>SSE 流式输出"]
```

> 详细设计见 [预约并发防超订](docs/reservation-concurrency.md) 与 [Agent 安全加固](docs/agent-security.md)。

<a name="features"></a>
## 功能总览

| 模块 | 说明 |
| --- | --- |
| 用户认证 | 注册 / 登录，JWT 鉴权，bcrypt 密码加密，student / admin 两种角色；登录失败限流（同一账号 + IP 15 分钟内 5 次） |
| 实验室管理 | 实验室增删改查（管理员），封面图上传、开放时间、容量、开放状态 |
| 设备管理 | 按实验室管理设备台账，型号 / 数量 / 维修状态（管理员） |
| 预约与审核 | 学生预约实验室或设备，管理员审核通过 / 拒绝；时段冲突检测（含并发行锁）、开放时间校验、过期自动置为已取消 |
| 预约日历 | 周视图时间轴直观查看某实验室的占用情况，点击空时段直接带入预约弹窗 |
| 站内通知 | 审核结果、AI 代预约结果实时推送，顶栏铃铛 + 未读角标，支持一键已读 |
| 数据统计 | 首页真实数据统计卡 + ECharts 图表（预约趋势、实验室使用排行、审核通过率、我的预约状态分布） |
| AI 智能助手 | LangGraph Agent + RAG 知识库问答，流式输出（SSE），支持工具调用真实落库：查实验室 / 查设备 / 创建预约 / 取消预约，多轮会话历史保存 |
| 个人中心 | 资料修改、头像上传、修改密码 |

## 技术栈

### 后端（`backend/`）

| 技术 | 用途 |
| --- | --- |
| Python 3.10+ / FastAPI | Web 框架，RESTful API |
| SQLAlchemy 2.0 | ORM（MySQL，pymysql 驱动） |
| PyJWT + bcrypt | 登录态与密码加密 |
| pydantic-settings | 配置管理（`.env`） |
| LangGraph + langchain-openai | Agent 编排（ReAct 循环 + ToolNode） |
| ChromaDB + sentence-transformers | 向量知识库（嵌入模型 `BAAI/bge-small-zh-v1.5`） |
| uvicorn | ASGI 服务器 |

### 前端（`frontend/`）

| 技术 | 用途 |
| --- | --- |
| Vue 3（Composition API）+ Vite | 前端框架与构建工具 |
| Element Plus | UI 组件库（深青墨色定制主题） |
| ECharts 5 | 统计图表 |
| Axios | HTTP 请求（统一拦截器、401 处理） |
| Vue Router 4 | 路由 + 登录/角色守卫 |

### AI 架构说明

```
用户消息
   │
   ▼
LangGraph Agent（系统提示词 + 多轮历史）
   │  需要事实时调用工具
   ├── search_lab_docs        检索知识库（ChromaDB 向量检索）
   ├── list_open_labs         查询开放实验室
   ├── list_lab_equipments    查询实验室设备
   ├── create_lab_reservation 创建预约（真实落库 + 站内通知）
   ├── cancel_lab_reservation 取消预约
   └── get_today              获取今天日期（换算"明天/后天"）
   │
   ▼
SSE 流式返回（思考状态 / 工具调用过程 / 逐字回复）
```

知识库语料为 `backend/data/kb/*.md`（预约规则、安全规范、开放时间、设备使用），首次启动自动向量化并入库。

## 目录结构

```
AgentProject/
├── backend/
│   ├── app/
│   │   ├── api/            # 路由层: auth/user/lab/equipment/reservation/files/ai/notification/stats
│   │   ├── services/       # 业务层: 预约冲突检测、Agent 工具、RAG 检索、统计、通知...
│   │   ├── models/         # SQLAlchemy 模型
│   │   ├── schemas/        # Pydantic 请求/响应模型
│   │   ├── common/         # 统一响应与全局异常处理
│   │   ├── dependencies/   # 登录态/管理员鉴权依赖
│   │   └── utils/          # JWT、密码加密
│   ├── data/kb/            # RAG 知识库语料（Markdown）
│   ├── uploads/            # 上传文件存储
│   ├── requirements.txt
│   └── .env                # 环境变量（需自行创建）
└── frontend/
    ├── src/
    │   ├── api/            # 接口封装
    │   ├── views/          # 页面（登录/首页/日历/实验室/设备/用户/预约/AI聊天...）
    │   ├── layout/         # 主框架（深色侧边栏 + 通知铃铛）
    │   ├── components/     # 预约弹窗等公共组件
    │   ├── router/         # 路由与守卫
    │   └── utils/          # axios 拦截器、登录态存储
    └── package.json
```

<a name="quickstart"></a>
## 快速开始

> 最快路径（Windows）：`.\scripts\bootstrap.ps1` → `.\scripts\dev.ps1`，详见下文「工程化与本地开发」。

### 环境要求

- Python 3.10+
- Node.js 18+（建议 22）
- MySQL 5.7+ / 8.0

### 1. 启动后端

```bash
cd backend

# 创建并激活虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

在 `backend/` 下创建 `.env`（参考格式）：

```env
DATABASE_URL=mysql+pymysql://root:你的密码@127.0.0.1:3306/lzjai
JWT_SECRET_KEY=一串随机字符串
JWT_EXPIRE_HOURS=24
JWT_ALGORITHM=HS256
LLM_API_KEY=你的大模型API Key
LLM_MODEL=模型名称
LLM_BASE_URL=https://xxx/v1
# 可选：允许跨域的前端地址（逗号分隔），默认已覆盖 Vite 5173
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

> 仓库根目录已提供 `.gitignore`：`backend/.env`、`.venv`、`node_modules`、`uploads`、`data/chroma` 等都不会被提交。

初始化数据库（任选其一）：

```sql
CREATE DATABASE lzjai DEFAULT CHARACTER SET utf8mb4;
```

启动服务（首次启动会自动建表、加载并向量化知识库）：

```bash
uvicorn app.main:app --reload --port 8000
```

接口文档自动生成：<http://127.0.0.1:8000/docs>

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 <http://localhost:5173>。

前端通过 `frontend/.env.development` 中的 `VITE_API_BASE_URL` 指向后端地址（默认 `http://127.0.0.1:8000`），跨域已由后端 CORS 配置放行。

### 3. 创建管理员账号

注册页注册的账号默认为 `student` 角色。将某账号提升为管理员：

```sql
UPDATE users SET role = 'admin' WHERE username = '你的账号';
```

## 工程化与本地开发

### 一键脚本（Windows PowerShell）

```powershell
.\scripts\bootstrap.ps1             # 建 venv、装锁定依赖、生成 .env、初始化数据库结构
.\scripts\bootstrap.ps1 -WithDocker # 额外拉起 compose 里的 MySQL 并等待健康检查
.\scripts\dev.ps1                   # 两个窗口分别启动后端 8000 + 前端 5173
.\scripts\check.ps1                 # 本地质量门禁：ruff + pytest（+ 前端 build）
.\scripts\check.ps1 -BackendOnly    # 只跑后端检查（没装前端依赖时用）
```

装了 `make` 时等价命令：`make bootstrap` / `make dev` / `make check`（默认调用 `powershell`，用 PowerShell 7 时加 `make PS=pwsh`）。

若系统执行策略拦截脚本，用：`powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1`。

### Docker 运行

标准方式（需要能访问 Docker Hub 拉取 `mysql:8.0`）：

```powershell
docker compose up -d --build
```

- 前端：<http://localhost:8080>（nginx 反代 `/api`、`/uploads` 到后端）
- 后端接口文档：<http://localhost:8000/docs>
- MySQL 暴露在宿主机 **3307**，避免与本地 3306 冲突
- 停止：`docker compose down`；`docker compose down -v` 会连数据卷一起删

如果 Docker Hub 不可用（代理未启动/镜像仓库被墙），但宿主机已有 MySQL 8.0，可复用宿主库、跳过 mysql 容器：

```powershell
docker compose -f docker-compose.yml -f docker-compose.hostdb.yml up -d --no-deps backend frontend
```

说明：Docker Desktop 会把 `host.docker.internal` 的流量转成宿主 loopback，MySQL 看到的来源是 `localhost`，因此沿用 `root@localhost`；库名与密码取根目录 `.env` 的 `MYSQL_DATABASE` / `MYSQL_ROOT_PASSWORD`。

镜像说明：后端 Dockerfile 显式安装 **CPU 版 torch**（约 200MB），避免默认 CUDA 依赖把镜像撑到 8GB；bge-small 嵌入模型在构建期预热并烘焙进镜像，运行时离线加载。当前镜像体积约 2.8GB。

### 版本与依赖基线

- **Python 3.12** 是部署/CI 基线（`.python-version`）；本地 3.14 也能跑，但提交前以 CI 行为为准。
- **Node 22** 是 CI 版本（`.node-version`），`package.json` 的 `engines` 同时允许 24+。
- 依赖分两层：`backend/requirements.in` 是"我要什么"（直接依赖），`backend/requirements.txt` 锁定精确版本；升级流程为
  `改 requirements.in → pip-compile 重新生成 → 跑 pytest → 一起提交`。
- `.gitattributes` 统一 LF，`.editorconfig` 统一 UTF-8 与缩进，避免 Windows/Linux 换行与编码差异。
- 根目录 `.gitignore` 已排除 `.env`、`.venv`、`node_modules`、`dist`、`uploads`、`data/chroma`；密钥只提交 `.env.example`。

### 数据库迁移

- **全新库**：`cd backend` 后执行 `python scripts/bootstrap_db.py`（`create_all` 建表 + 写入 alembic head）。
- **已有库**：只走 `alembic upgrade head`；不要用 `create_all` 改结构（它不会 ALTER 已有表）。
- CI 会在全新库上执行 `bootstrap_db.py` 并跑 `alembic check`，校验 `migrations/env.py` 的模型导入完整性。
- 已知限制：当前迁移链缺少 baseline（首条迁移假设表已存在），所以还不能用 `alembic upgrade head` 从零建库，也无法检测"模型改了但没写迁移"的漂移。补一条 baseline 迁移后即可开启 `alembic check` 漂移门禁。

## 使用说明

### 学生端

1. **预约日历**：选择实验室 → 周视图中点击任意空白时段 → 弹窗自动带入日期和时间 → 确认提交（青色块为已通过预约，虚线块为待审核）
2. **实验室列表**：浏览实验室卡片，可查看设备详情、从卡片发起预约
3. **我的预约记录**：查看待审核 / 已通过 / 已拒绝 / 已取消，待审核的可以取消
4. **AI 智能助手**：直接对话，例如
   - "明天上午有哪些实验室开放？"
   - "帮我预约后天 9 点到 11 点的网络工程实验室"
   - "预约实验室需要遵守什么规则？"（RAG 检索知识库回答）
   - 确认信息后 AI 会真实创建预约，并在铃铛通知里收到结果
5. **通知**：顶栏铃铛查看审核结果，点击通知跳转到预约记录

### 管理员端

1. **实验室管理 / 设备列表管理**：维护实验室与设备信息（含图片上传、开放时间、状态）
2. **预约审核管理**：按状态 / 申请人 / 实验室关键字筛选，通过或拒绝待审核预约（审核结果自动推送给学生）
3. **用户管理**：新增用户、调整角色与状态
4. **首页仪表盘**：真实统计数据与趋势图表

## 常见问题

- **AI 助手不回复**：检查 `.env` 中 `LLM_API_KEY / LLM_BASE_URL / LLM_MODEL` 是否可用
- **首次启动较慢**：正在下载 `bge-small-zh-v1.5` 嵌入模型并构建向量库，之后会复用本地缓存
- **删除实验室/设备/用户提示"存在关联记录"**：系统会阻止删除已有预约或设备关联的数据，保证数据完整性
- **token 过期**：前端会自动清理登录态并跳转登录页（默认 24 小时有效）

<a name="docs"></a>
## 技术深潜文档

- [预约并发防超订：设计、改造与验证记录](docs/reservation-concurrency.md) —— 三方案对比、父行锁+生成列唯一索引四层设计、预约状态机、APScheduler+GET_LOCK 定时扫描、pytest 并发测试与 Locust 压测数据（50 并发 1 万请求 0 超订 0 死锁）
- [Agent 安全加固：风险清单、分层防护与验证](docs/agent-security.md) —— 8 项风险与攻击示例、六层防护（JWT 身份闭包/输入清洗/参数校验/配额/提示词防注入/审计日志）、提示词注入测试用例
