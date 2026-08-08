from github_ai_weekly.config import TOPICS
from github_ai_weekly.snapshot import (
    build_snapshot,
    discover_repos,
    load_snapshot,
    save_snapshot,
    validate_snapshot,
)
from github_ai_weekly.github_api import GitHubClient
from tests.test_github_api import FakeResponse, FakeSession, repo_item


class FakeClient:
    """测试用客户端：种子仓库逐个抓取，搜索固定返回两个发现仓库。"""

    def __init__(self, fail_full_names=()):
        self.fail_full_names = set(fail_full_names)

    def search_repos(self, query, per_page=100, max_results=100):
        return [
            repo_item("discovery/rag-one", 5000) | {"topics": ["rag", "llm"]},
            repo_item("discovery/agent-one", 3000) | {"topics": ["ai-agent"]},
        ]

    def fetch_repo(self, full_name):
        if full_name in self.fail_full_names:
            raise RuntimeError(f"boom {full_name}")
        return repo_item(full_name, 2000)

    @staticmethod
    def to_record(repo, category=None):
        return GitHubClient.to_record(repo, category)


class RecordingClient(FakeClient):
    def __init__(self):
        super().__init__()
        self.queries = []

    def search_repos(self, query, per_page=100, max_results=100):
        self.queries.append(query)
        return [repo_item("discovery/rag-one", 5000) | {"topics": ["rag"]}]


def test_discovery_uses_one_query_per_topic_without_or():
    client = RecordingClient()
    repos = discover_repos(client)
    assert len(client.queries) == len(TOPICS)
    assert all(" OR " not in q and q.startswith("topic:") and "stars:>1000" in q for q in client.queries)
    assert "discovery/rag-one" in repos


def test_build_snapshot_merges_seed_and_discovery():
    seed = [
        {"owner": "huggingface", "repo": "transformers", "category": "llm_framework"},
        {"owner": "openai", "repo": "whisper", "category": "multimodal"},
    ]
    snapshot = build_snapshot(FakeClient(), "2026-08-08", seed)
    assert snapshot["date"] == "2026-08-08"
    assert snapshot["source"] == "github-api"
    assert snapshot["repos"]["huggingface/transformers"]["category"] == "llm_framework"
    assert snapshot["repos"]["openai/whisper"]["category"] == "multimodal"
    assert snapshot["repos"]["discovery/rag-one"]["category"] == "rag"
    assert snapshot["repos"]["discovery/agent-one"]["category"] == "agent"


def test_build_snapshot_skips_failing_seed_repo():
    seed = [{"owner": "gone", "repo": "missing", "category": "eval"}]
    snapshot = build_snapshot(FakeClient(fail_full_names={"gone/missing"}), "2026-08-08", seed)
    assert "gone/missing" not in snapshot["repos"]


def test_validate_snapshot_ok():
    snapshot = {
        "date": "2026-08-08",
        "repos": {"a/b": {"stars": 10, "forks": 1, "description": "", "url": "u", "archived": False, "fork": False}},
    }
    assert validate_snapshot(snapshot) == []


def test_validate_snapshot_reports_errors():
    snapshot = {
        "date": "08/08/2026",
        "repos": {
            "bad-key": {"stars": -1, "forks": 1, "description": "", "url": "u", "archived": "yes", "fork": False}
        },
    }
    errors = validate_snapshot(snapshot)
    assert any("date" in e for e in errors)
    assert any("bad-key" in e and "stars" in e for e in errors)
    assert any("bad-key" in e and "archived" in e for e in errors)


def test_validate_snapshot_empty_repos():
    assert any("repos" in e for e in validate_snapshot({"date": "2026-08-08", "repos": {}}))


def test_save_load_roundtrip(tmp_path):
    snapshot = {
        "date": "2026-08-08",
        "repos": {
            "a/b": {
                "stars": 10,
                "forks": 1,
                "description": "desc",
                "url": "https://github.com/a/b",
                "category": "llm_framework",
                "archived": False,
                "fork": False,
            }
        },
    }
    path = save_snapshot(snapshot, directory=tmp_path)
    assert path.name == "2026-08-08.json"
    assert load_snapshot(path) == snapshot
