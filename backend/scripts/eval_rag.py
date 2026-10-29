"""RAG 检索评测脚本

用法（backend 目录下、后端 venv）:
    python scripts/eval_rag.py                # 跑当前配置
    python scripts/eval_rag.py --tag baseline # 给报告打标签（改造前后对比用）

指标口径:
    Recall@K   = 前 K 条检索结果中包含期望文档的样本占比（命中=期望 source 出现在 top-K）
    HitRate@K  与 Recall@K 同义（单期望文档场景）
    MRR        = 期望文档首次出现位次的倒数均值（1/rank，未命中记 0）
    Latency    = 单条检索平均耗时

说明: 当前语料为整文件入向量库（4 个文档），排序深度上限为 4，故 K>4 无区分度；
chunk 化改造后 K 的评测才有完整意义（这也是先建评测再改造的意义——数字可比）。
"""

import argparse
import json
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))  # 允许直接 python scripts/eval_rag.py 运行

EVAL_FILE = BACKEND_DIR / "data" / "kb" / "eval.jsonl"
REPORT_FILE = BACKEND_DIR / "scripts" / "eval_report.md"


def load_eval_set() -> list:
    items = []
    with open(EVAL_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def evaluate(items: list, ks=(1, 3, 5)):
    from app.services import kb_service

    rows = []
    for item in items:
        t0 = time.perf_counter()
        refs = kb_service.search_refs(item["question"], k=max(ks))
        latency_ms = (time.perf_counter() - t0) * 1000
        ranked = [r["source"] for r in refs]
        first_rank = next(
            (i + 1 for i, src in enumerate(ranked) if src == item["expected_source"]), None
        )
        rows.append(
            {
                **item,
                "ranked": ranked,
                "first_rank": first_rank,
                "mrr": 1 / first_rank if first_rank else 0.0,
                "hit": {k: (first_rank is not None and first_rank <= k) for k in ks},
                "latency_ms": latency_ms,
            }
        )
    return rows


def summarize(rows: list, ks=(1, 3, 5)):
    def _group(rs):
        n = len(rs)
        return {
            "n": n,
            **{f"R@{k}": sum(r["hit"][k] for r in rs) / n for k in ks},
            "MRR": sum(r["mrr"] for r in rs) / n,
            "latency": sum(r["latency_ms"] for r in rs) / n,
        }

    groups = {"overall": _group(rows)}
    for diff in ("easy", "medium", "hard"):
        rs = [r for r in rows if r["difficulty"] == diff]
        if rs:
            groups[diff] = _group(rs)
    return groups


def fmt_table(groups: dict, ks) -> str:
    header = "| 分组 | 样本数 | " + " | ".join(f"Recall@{k}" for k in ks) + " | MRR | 平均延迟(ms) |"
    sep = "| --- | --- | " + " | ".join("---" for _ in ks) + " | --- | --- |"
    lines = [header, sep]
    for name, g in groups.items():
        cells = " | ".join(f"{g[f'R@{k}'] * 100:.1f}%" for k in ks)
        lines.append(
            f"| {name} | {g['n']} | {cells} | {g['MRR']:.3f} | {g['latency']:.1f} |"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="current", help="报告标签，如 baseline / chunked")
    args = parser.parse_args()

    items = load_eval_set()
    print(f"加载评测集: {len(items)} 条（来自 {EVAL_FILE.name}）")
    print("正在初始化向量库（首次需加载 embedding 模型）...")

    rows = evaluate(items)
    groups = summarize(rows)

    table = fmt_table(groups, ks=(1, 3, 5))
    print("\n" + table)

    misses = [r for r in rows if r["first_rank"] is None]
    if misses:
        print("\n未命中样本:")
        for r in misses:
            print(f"  [#{r['id']}][{r['difficulty']}] {r['question']}  实际排序: {r['ranked']}")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(
            f"# RAG 检索评测报告（{args.tag}）\n\n"
            f"> 时间: {time.strftime('%Y-%m-%d %H:%M')} | 样本: {len(items)} | 语料: data/kb/*.md（整文件入向量库）\n\n"
            f"{table}\n\n"
        )
        if misses:
            f.write("## 未命中样本\n\n")
            for r in misses:
                f.write(
                    f"- [#{r['id']}][{r['difficulty']}] {r['question']}（期望 {r['expected_source']}，"
                    f"实际排序 {r['ranked']}）\n"
                )
    print(f"\n报告已写入: {REPORT_FILE}")


if __name__ == "__main__":
    main()
