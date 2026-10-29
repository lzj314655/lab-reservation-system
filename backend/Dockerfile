# syntax=docker/dockerfile:1

# ============================================================
# 阶段1: 依赖 + 嵌入模型缓存
# 说明: 显式安装 CPU 版 torch。PyPI 默认的 torch 会拉入 CUDA/cuDNN/
# cuBLAS（约 3GB），而本项目只做 CPU embedding，CPU wheel 能把镜像
# 从 ~8GB 压到 ~2GB，构建时间也大幅缩短。
# ============================================================
FROM python:3.12-slim AS deps
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
# 与 sentence-transformers 6.0.1 的 torch>=2.2 兼容；升级依赖时同步调整
ARG TORCH_VERSION=2.15.0+cpu

RUN python -m venv /opt/venv
COPY requirements.txt .
RUN /opt/venv/bin/pip install \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        "torch==${TORCH_VERSION}" \
    && /opt/venv/bin/pip install -r requirements.txt

# 构建期预热 bge-small 模型（国内走 hf-mirror），运行时离线复用
ENV HF_ENDPOINT=https://hf-mirror.com
RUN /opt/venv/bin/python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')"

# ============================================================
# 阶段2: 运行时 —— 非 root、只带运行所需
# ============================================================
FROM python:3.12-slim AS runtime

RUN useradd --create-home --uid 1000 app

COPY --from=deps /opt/venv /opt/venv
COPY --from=deps --chown=app /root/.cache/huggingface /home/app/.cache/huggingface

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
