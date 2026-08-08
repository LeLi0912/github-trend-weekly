import pytest
import requests
import json

from github_ai_weekly.github_api import GitHubClient


class FakeResponse:
    def __init__(self, payload, status_code=200, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, routes):
        self.routes = routes
        self.headers = {}
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        key = (url, json.dumps(params or {}, sort_keys=True))
        if key in self.routes:
            value = self.routes[key]
            if isinstance(value, list):
                return value.pop(0)
            return value
        raise AssertionError(f"unexpected request: {key}")


def route(url, params):
    return (url, json.dumps(params or {}, sort_keys=True))


def repo_item(full_name, stars):
    return {
        "full_name": full_name,
        "stargazers_count": stars,
        "forks_count": stars // 10,
        "description": f"desc {full_name}",
        "language": "Python",
        "topics": ["llm"],
        "html_url": f"https://github.com/{full_name}",
        "archived": False,
        "fork": False,
        "is_template": False,
        "pushed_at": "2026-08-01T00:00:00Z",
    }


def test_to_record_maps_fields():
    raw = repo_item("openai/whisper", 5000)
    record = GitHubClient.to_record(raw, category="multimodal")
    assert record["stars"] == 5000
    assert record["forks"] == 500
    assert record["category"] == "multimodal"
    assert record["url"] == "https://github.com/openai/whisper"
    assert record["archived"] is False
    assert record["is_template"] is False


def test_search_repos_single_page():
    params = {"q": "topic:llm", "sort": "stars", "order": "desc", "per_page": 100, "page": 1}
    session = FakeSession(
        {route("https://api.github.com/search/repositories", params): FakeResponse({"total_count": 1, "items": [repo_item("a/b", 10)]})}
    )
    client = GitHubClient(session=session)
    items = client.search_repos("topic:llm")
    assert len(items) == 1
    assert items[0]["full_name"] == "a/b"


def test_search_repos_paginates_until_total():
    p1 = {"q": "topic:ai", "sort": "stars", "order": "desc", "per_page": 100, "page": 1}
    p2 = {"q": "topic:ai", "sort": "stars", "order": "desc", "per_page": 100, "page": 2}
    session = FakeSession(
        {
            route("https://api.github.com/search/repositories", p1): FakeResponse({"total_count": 3, "items": [repo_item("a/1", 3), repo_item("a/2", 2)]}),
            route("https://api.github.com/search/repositories", p2): FakeResponse({"total_count": 3, "items": [repo_item("a/3", 1)]}),
        }
    )
    client = GitHubClient(session=session)
    items = client.search_repos("topic:ai")
    assert [i["full_name"] for i in items] == ["a/1", "a/2", "a/3"]


def test_search_repos_respects_max_results():
    p1 = {"q": "topic:ai", "sort": "stars", "order": "desc", "per_page": 100, "page": 1}
    session = FakeSession(
        {
            route("https://api.github.com/search/repositories", p1): FakeResponse(
                {"total_count": 5, "items": [repo_item(f"a/{i}", 100 - i) for i in range(5)]}
            )
        }
    )
    client = GitHubClient(session=session)
    items = client.search_repos("topic:ai", max_results=3)
    assert len(items) == 3


def test_rate_limit_retry_then_succeeds():
    params = {"q": "topic:llm", "sort": "stars", "order": "desc", "per_page": 100, "page": 1}
    api_route = route("https://api.github.com/search/repositories", params)
    session = FakeSession(
        {
            api_route: [
                FakeResponse(
                    {"total_count": 1, "items": [repo_item("a/b", 10)]},
                    status_code=403,
                    headers={"Retry-After": "0"},
                ),
                FakeResponse({"total_count": 1, "items": [repo_item("a/b", 10)]}),
            ]
        }
    )
    client = GitHubClient(session=session)
    items = client.search_repos("topic:llm")
    assert len(items) == 1
    assert len(session.calls) == 2


def test_fetch_repo_raises_on_404():
    session = FakeSession(
        {route("https://api.github.com/repos/gone/missing", None): FakeResponse({"message": "Not Found"}, status_code=404)}
    )
    client = GitHubClient(session=session)
    with pytest.raises(requests.HTTPError):
        client.fetch_repo("gone/missing")
