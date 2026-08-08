"""周快照：构建、读写、校验。"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

from .config import DISCOVER_TOP_N, SEED_FILE, SNAPSHOT_DIR, TOPICS, category_from_topics
from .github_api import GitHubClient

log = logging.getLogger(__name__)


def load_seed(path: Path = SEED_FILE) -> list[dict[str, str]]:
    """加载精选种子清单：[{owner, repo, category}, ...]"""
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def discover_repos(
    client: GitHubClient,
    per_topic: int = DISCOVER_TOP_N,
) -> dict[str, dict[str, Any]]:
    """按 topic 逐个搜索发现仓库（Search API 的 OR 不支持 qualifier）；单个 topic 失败不阻塞整体。"""
    merged: dict[str, dict[str, Any]] = {}
    for topic in TOPICS:
        query = f"topic:{topic} stars:>1000"
        try:
            items = client.search_repos(query, per_page=100, max_results=per_topic)
        except Exception as exc:  # noqa: BLE001 - 单组失败继续
            log.warning("topic 发现查询失败 (%s)：%s", topic, exc)
            continue
        for item in items:
            full_name = item.get("full_name", "")
            if not full_name:
                continue
            record = client.to_record(item)
            if record["category"] is None:
                record["category"] = category_from_topics(record["topics"])
            merged[full_name] = record
    return merged


def build_snapshot(
    client: GitHubClient,
    snapshot_date: str,
    seed: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """构建某周快照：种子仓库详情 + topic 发现结果合并。"""
    seed = seed if seed is not None else load_seed()
    repos: dict[str, dict[str, Any]] = discover_repos(client)

    for entry in seed:
        owner = entry.get("owner", "")
        repo_name = entry.get("repo", "")
        category = entry.get("category")
        full_name = f"{owner}/{repo_name}"
        if not owner or not repo_name:
            continue
        try:
            record = client.to_record(client.fetch_repo(full_name), category)
        except Exception as exc:  # noqa: BLE001 - 单个仓库失败不阻塞
            log.warning("种子仓库抓取失败 %s：%s", full_name, exc)
            continue
        repos[full_name] = record

    return {"date": snapshot_date, "source": "github-api", "repos": repos}


def validate_snapshot(snapshot: dict[str, Any]) -> list[str]:
    """校验快照结构，返回错误列表；空列表表示合法。"""
    errors: list[str] = []
    snapshot_date = snapshot.get("date", "")
    try:
        date.fromisoformat(snapshot_date)
    except (TypeError, ValueError):
        errors.append(f"date 不是合法 YYYY-MM-DD：{snapshot_date!r}")

    repos = snapshot.get("repos")
    if not isinstance(repos, dict) or not repos:
        errors.append("repos 必须是非空字典")
        return errors

    for full_name, record in repos.items():
        if "/" not in full_name:
            errors.append(f"仓库 key 必须是 owner/repo：{full_name!r}")
        for field in ("stars", "forks"):
            value = record.get(field)
            if not isinstance(value, int) or value < 0:
                errors.append(f"{full_name}.{field} 必须是非负整数：{value!r}")
        for field in ("description", "url"):
            if not isinstance(record.get(field), str):
                errors.append(f"{full_name}.{field} 必须是字符串")
        if not isinstance(record.get("archived", False), bool) or not isinstance(record.get("fork", False), bool):
            errors.append(f"{full_name}.archived/fork 必须是布尔值")
    return errors


def save_snapshot(snapshot: dict[str, Any], directory: Path = SNAPSHOT_DIR) -> Path:
    """保存快照到 data/snapshots/YYYY-MM-DD.json。"""
    errors = validate_snapshot(snapshot)
    if errors:
        raise ValueError("快照校验失败：" + "; ".join(errors))
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{snapshot['date']}.json"
    path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def load_snapshot(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def latest_snapshot(directory: Path = SNAPSHOT_DIR) -> dict[str, Any] | None:
    """返回日期最新的快照；目录为空返回 None。"""
    files = sorted(directory.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].json"))
    if not files:
        return None
    return load_snapshot(files[-1])
