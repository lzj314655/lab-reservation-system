# syntax=docker/dockerfile:1

# ============================================================
# 阶段1: 依赖 —— 独立 venv，最大化层缓存（改代码不重装依赖）
# ============================================================
FROM python:3.12-slim AS deps
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
COPY requirements.txt .
RUN /opt/venv/bin/pip install -r requirements.txt

# ============================================================
# 阶段2: 模型缓存 —— bge-small-zh(~92MB) 烘焙进镜像
# 走 hf-mirror 镜像源（国内网络），产物为标准 HF 缓存目录。
# 备选方案：不烘焙，改为挂载命名卷 + 首次启动在线下载
# （镜像小 ~100MB，但首次启动依赖网络且慢，权衡后选择烘焙）。
# ============================================================
FROM python:3.12-slim AS model-cache
ENV HF_ENDPOINT=https://hf-mirror.com
RUN pip install --no-cache-dir sentence-transformers==6.0.1 \
    && python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')"

# ============================================================
# 阶段3: 运行时 —— 非 root、只带运行所需
# ============================================================
FROM python:3.12-slim AS runtime

RUN useradd --create-home --uid 1000 app

COPY --from=deps /opt/venv /opt/venv
# 模型缓存放到 app 用户的 HF 缓存目录
COPY --from=model-cache --chown=app /root/.cache/huggingface /home/app/.cache/huggingface

WORKDIR /app
COPY --chown=app app ./app
COPY --chown=app scripts ./scripts
COPY --chown=app migrations ./migrations
COPY --chown=app alembic.ini .
# 知识库语料烘焙进镜像（chroma 向量库运行时生成，挂卷持久化）
COPY --chown=app data/kb ./data/kb
# 预建可写目录（命名卷首次挂载会继承属主）
RUN mkdir -p /app/data/chroma /app/uploads && chown -R app:app /app/data /app/uploads

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

USER app
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status==200 else 1)"

# 幂等建表 + alembic 标记，然后起服务（单副本部署足够；多副本时应移到一次性 job）
CMD ["sh", "-c", "python scripts/bootstrap_db.py && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
