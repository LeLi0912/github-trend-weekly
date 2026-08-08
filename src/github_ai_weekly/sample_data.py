"""离线演示数据：三周确定性快照，用于无网络/无 token 时验证全链路。"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

# (full_name, category, 语言, 描述, 第 1 周星标, 第 2 周星标, 第 3 周星标)
SAMPLE_REPOS: list[tuple[str, str, str, str, int, int, int]] = [
    ("huggingface/transformers", "llm_framework", "Python", "Transformer 模型库与工具链", 140000, 142000, 143500),
    ("vllm-project/vllm", "inference", "Python", "高吞吐 LLM 推理与服务引擎", 60000, 62000, 65000),
    ("browser-use/browser-use", "agent", "Python", "让 AI Agent 操控浏览器的工具", 30000, 35000, 41000),
    ("infiniflow/ragflow", "rag", "TypeScript", "基于深度文档理解的开源 RAG 引擎", 28000, 31000, 34000),
    ("qdrant/qdrant", "vector_db", "Rust", "面向 AI 的向量搜索引擎", 26000, 27000, 27800),
    ("unslothai/unsloth", "training", "Python", "更快的 LLM 微调加速框架", 30000, 33000, 36000),
    ("promptfoo/promptfoo", "eval", "TypeScript", "LLM 提示词与应用的评测工具", 14000, 15000, 16000),
    ("langfuse/langfuse", "mlops", "TypeScript", "LLM 应用的观测与追踪平台", 15000, 16500, 17800),
    ("comfyanonymous/ComfyUI", "multimodal", "Python", "节点式图像生成工作流界面", 90000, 92000, 93500),
    ("openai/openai-agents-python", "agent", "Python", "OpenAI 官方 Agents SDK", 20000, 25000, 31000),
    ("microsoft/markitdown", "llm_framework", "Python", "把各类文档转成 LLM 友好 Markdown", 18000, 21000, 24000),
    ("mem0ai/mem0", "agent", "Python", "AI Agent 的记忆层", 28000, 31000, 34500),
]


def _record(stars: int, category: str, language: str, description: str) -> dict[str, Any]:
    return {
        "stars": stars,
        "forks": stars // 20,
        "description": description,
        "language": language,
        "topics": [],
        "url": "https://github.com/example",
        "category": category,
        "archived": False,
        "fork": False,
        "is_template": False,
        "pushed_at": None,
    }


def build_sample_snapshots(today: date | None = None) -> list[dict[str, Any]]:
    """生成最近三周（周、上两周）的确定性演示快照。"""
    today = today or date.today()
    snapshots: list[dict[str, Any]] = []
    for offset in (14, 7, 0):
        snapshot_date = (today - timedelta(days=offset)).isoformat()
        week_index = 2 - offset // 7
        repos = {
            full_name: _record(values[week_index], category, language, description)
            for full_name, category, language, description, *values in SAMPLE_REPOS
        }
        snapshots.append({"date": snapshot_date, "source": "sample", "repos": repos})
    return snapshots
