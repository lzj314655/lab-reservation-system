import logging
import os

# 模型缓存完整时强制离线加载：跳过 HuggingFace 网络探测
# （国内网络下在线探测会超时重试甚至报 Unrecognized processing class）
# 首次部署无缓存时，请临时移除这两行或执行:
#   HF_ENDPOINT=https://hf-mirror.com python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')"
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions
import chromadb
from app.config import BASE_DIR

logger = logging.getLogger(__name__)

KB_DIR = BASE_DIR / "data" / "kb"
CHROMA_DIR = BASE_DIR / "data" / "chroma"
EMBEDDING_MODEL_NAME = "BAAI/bge-small-zh-v1.5"

_collection = None

_embedding_fn = None

def get_embedding_fn():
    global _embedding_fn
    if _embedding_fn is not None:
        return _embedding_fn
    _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL_NAME
    )
    return _embedding_fn

def get_collection() -> Collection:
    global _collection
    if _collection is not None:
        return _collection
    KB_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    col = client.get_or_create_collection(name="lab_kb",embedding_function=get_embedding_fn())
    if col.count() == 0:
        ids = []
        docs = []
        metas = []
        for path in sorted(KB_DIR.glob("*.md")):
            text = path.read_text(encoding="UTF-8").strip()
            if not text:
                continue
            docs.append(text)
            ids.append(path.stem)
            metas.append({"source": path.name})
        if docs:
            col.add(ids=ids, documents=docs, metadatas=metas)
    _collection = col
    return col

def warmup():
    """启动的时候初始化向量库  启动预热"""
    col = get_collection()
    if col.count() > 0:
        col.query(query_texts=["预热"], n_results=1)

def search_refs(query: str, k: int = 3) -> list:
    """向量检索：返回带来源与相关度分数的结构化结果（不截断、不过滤，
    供评测（Recall/MRR 需要完整排序）与引用来源展示使用）。"""
    col = get_collection()
    if col.count() == 0:
        return []
    limit = min(max(k, 1), col.count())
    res = col.query(query_texts=[query], n_results=limit)
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    refs = []
    for doc, meta, dist in zip(docs, metas, dists):
        score = 1 / (1 + dist)  # 距离转相关度，越大越相关
        refs.append(
            {
                "source": (meta or {}).get("source") or "",
                "content": doc,
                "snippet": doc[:160].strip(),
                "score": round(score, 4),
            }
        )
    return refs


def search(query: str, score_threshold: float = 0.7, top_n: int = 2) -> str:
    """Agent 问答用检索：阈值过滤后取 top_n 拼接为上下文。"""
    refs = search_refs(query, k=5)
    qualified = sorted(
        (r for r in refs if r["score"] >= score_threshold),
        key=lambda r: r["score"],
        reverse=True,
    )
    logger.debug("知识库检索结果: %s", [(r["source"], r["score"]) for r in refs])
    parts = [f"[{r['source']}]\n{r['content']}" for r in qualified[:top_n]]
    return "\n\n".join(parts)