"""GitHub REST API 客户端：搜索发现 + 仓库详情抓取。"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

GITHUB_API = "https://api.github.com"
log = logging.getLogger(__name__)


class GitHubClient:
    """轻量 GitHub API 客户端，带鉴权、重试与限流退避。"""

    def __init__(
        self,
        token: str | None = None,
        timeout: int = 30,
        session: requests.Session | None = None,
    ) -> None:
        self.token = token
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{GITHUB_API}{path}"
        for attempt in range(3):
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code in (403, 429):
                retry_after = resp.headers.get("Retry-After", "")
                wait = int(retry_after) if retry_after.isdigit() else 60 * (attempt + 1)
                log.warning("GitHub API 限流 (HTTP %s)，等待 %s 秒后重试", resp.status_code, wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError(f"GitHub API 限流持续超时：{path}")

    def search_repos(
        self,
        query: str,
        per_page: int = 100,
        max_results: int = 100,
    ) -> list[dict[str, Any]]:
        """按 query 搜索仓库（按 star 数倒序），返回完整仓库对象列表。"""
        items: list[dict[str, Any]] = []
        page = 1
        while len(items) < max_results:
            batch = self._get(
                "/search/repositories",
                {
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": per_page,
                    "page": page,
                },
            )
            page_items = batch.get("items") or []
            items.extend(page_items)
            total = int(batch.get("total_count", 0))
            if not page_items or len(items) >= total or page >= 10:
                break
            page += 1
        return items[:max_results]

    def fetch_repo(self, full_name: str) -> dict[str, Any]:
        """抓取单个仓库详情。"""
        return self._get(f"/repos/{full_name}")

    @staticmethod
    def to_record(repo: dict[str, Any], category: str | None = None) -> dict[str, Any]:
        """把 GitHub API 仓库对象规整为快照记录。"""
        full_name = repo.get("full_name", "")
        return {
            "stars": int(repo.get("stargazers_count") or 0),
            "forks": int(repo.get("forks_count") or 0),
            "description": repo.get("description") or "",
            "language": repo.get("language"),
            "topics": repo.get("topics") or [],
            "url": repo.get("html_url") or f"https://github.com/{full_name}",
            "category": category,
            "archived": bool(repo.get("archived", False)),
            "fork": bool(repo.get("fork", False)),
            "is_template": bool(repo.get("is_template", False)),
            "pushed_at": repo.get("pushed_at"),
        }
