"""全局配置：路径、榜单参数、分类与 topic 发现规则。"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
ARCHIVE_DIR = REPO_ROOT / "archive"
SEED_FILE = DATA_DIR / "seed_repos.json"
INDEX_HTML = REPO_ROOT / "index.html"
REPORT_TEMPLATE = Path(__file__).resolve().parent / "templates" / "report.html.j2"

# 榜单参数
MIN_STARS = 1000
TOP_N = 30
CATEGORY_TOP_N = 10

# 分类标签（报告展示用）
CATEGORY_LABELS = {
    "llm_framework": "LLM 框架",
    "agent": "Agent 框架",
    "rag": "RAG 与检索",
    "vector_db": "向量数据库",
    "inference": "推理与部署",
    "training": "训练与微调",
    "eval": "评测与安全",
    "mlops": "MLOps / LLMOps",
    "multimodal": "多模态与生成",
}

# topic 发现规则：GitHub Search API 的 OR 只作用于文本词、不作用于 qualifier，
# 因此每个 topic 单独查询一次再合并去重；每个 topic 取前 DISCOVER_TOP_N 个（按总星）。
DISCOVER_TOP_N = 30
TOPICS: list[str] = [
    "llm",
    "large-language-model",
    "generative-ai",
    "ai",
    "artificial-intelligence",
    "machine-learning",
    "deep-learning",
    "ai-agent",
    "agents",
    "autonomous-agents",
    "agent-framework",
    "rag",
    "retrieval-augmented-generation",
    "vector-database",
    "vector-search",
    "embeddings",
    "llm-inference",
    "model-serving",
    "multimodal",
    "text-to-image",
    "diffusion-models",
    "llm-evaluation",
    "prompt-evaluation",
    "ai-safety",
    "fine-tuning",
    "llm-training",
    "distributed-training",
    "mlops",
]

# 由仓库自身 topics 推断分类（discovery 结果没有预设分类时使用）
TOPIC_TO_CATEGORY: dict[str, str] = {
    "llm": "llm_framework",
    "large-language-model": "llm_framework",
    "ai-agent": "agent",
    "agents": "agent",
    "autonomous-agents": "agent",
    "agent-framework": "agent",
    "rag": "rag",
    "retrieval-augmented-generation": "rag",
    "vector-database": "vector_db",
    "vector-search": "vector_db",
    "embeddings": "vector_db",
    "llm-inference": "inference",
    "inference-engine": "inference",
    "model-serving": "inference",
    "multimodal": "multimodal",
    "text-to-image": "multimodal",
    "diffusion-models": "multimodal",
    "speech-recognition": "multimodal",
    "llm-evaluation": "eval",
    "prompt-evaluation": "eval",
    "ai-safety": "eval",
    "red-team": "eval",
    "fine-tuning": "training",
    "llm-training": "training",
    "distributed-training": "training",
    "mlops": "mlops",
    "llmops": "mlops",
    "observability": "mlops",
}


def category_from_topics(topics: list[str]) -> str | None:
    """根据仓库 topics 推断分类；无命中返回 None（报告显示为"未分类"）。"""
    for topic in topics:
        lowered = topic.lower()
        if lowered in TOPIC_TO_CATEGORY:
            return TOPIC_TO_CATEGORY[lowered]
    return None
