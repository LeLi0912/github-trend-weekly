from github_ai_weekly.report import build_context, render_report


def record(stars, category, description="desc", archived=False):
    return {
        "stars": stars,
        "forks": stars // 10,
        "description": description,
        "language": "Python" if category != "agent" else "TypeScript",
        "topics": [],
        "url": f"https://github.com/x/{category}",
        "category": category,
        "archived": archived,
        "fork": False,
        "is_template": False,
        "pushed_at": None,
    }


def snapshot(date, pairs):
    return {"date": date, "source": "github-api", "repos": {name: record(*meta) for name, meta in pairs.items()}}


CURRENT = snapshot(
    "2026-08-08",
    {
        "ai/ragflow": (12000, "rag", "RAG 引擎"),
        "ai/agentkit": (11000, "agent"),
        "ai/vector": (10500, "vector_db"),
        "ai/newcomer": (2000, "eval"),
        "ai/low": (900, "rag"),
        "ai/archived": (15000, "rag", "archived", True),
    },
)
PREVIOUS = snapshot(
    "2026-08-01",
    {
        "ai/ragflow": (10000, "rag"),
        "ai/agentkit": (9000, "agent"),
        "ai/vector": (10500, "vector_db"),
        "ai/oldface": (5000, "rag"),
    },
)
EARLIER = snapshot(
    "2026-07-25",
    {
        "ai/ragflow": (8000, "rag"),
        "ai/agentkit": (7000, "agent"),
        "ai/vector": (10000, "vector_db"),
    },
)


def test_build_context_structure():
    context = build_context(CURRENT, PREVIOUS, [EARLIER, PREVIOUS, CURRENT])
    assert context["date"] == "2026-08-08"
    assert context["previous_date"] == "2026-08-01"
    assert [item["full_name"] for item in context["main"]] == [
        "ai/ragflow",
        "ai/agentkit",
        "ai/vector",
        "ai/newcomer",
    ]
    assert context["main"][0]["weekly_gain"] == 2000
    assert context["main"][0]["bar_pct"] == 100.0
    assert [item["full_name"] for item in context["new_faces"]] == ["ai/newcomer"]
    labels = [label for label, _ in context["categories"]]
    assert labels == ["Agent 框架", "RAG 与检索", "向量数据库", "评测与安全"]
    assert context["trend"]["series"][0]["name"] == "ai/ragflow"
    assert [d["label"] for d in context["trend"]["dates"]] == ["07-25", "08-01", "08-08"]
    assert any("ragflow" in c and "+2,000" in c for c in context["commentary"])


def test_render_is_deterministic(tmp_path):
    context = build_context(CURRENT, PREVIOUS, [EARLIER, PREVIOUS, CURRENT])
    out1 = tmp_path / "a.html"
    out2 = tmp_path / "b.html"
    render_report(context, out1)
    render_report(context, out2)
    assert out1.read_bytes() == out2.read_bytes()


def test_render_contains_expected_markers(tmp_path):
    context = build_context(CURRENT, PREVIOUS, [EARLIER, PREVIOUS, CURRENT])
    out = tmp_path / "report.html"
    render_report(context, out)
    html = out.read_text(encoding="utf-8")
    assert '<html lang="zh-CN" data-theme="dark">' in html
    assert "GitHub AI 周榜" in html
    assert "2026-08-08" in html
    assert "ai/ragflow" in html
    assert 'id="theme-toggle"' in html
    assert 'class="skip-link"' in html
    assert "<svg" in html
    assert "本周探讨" in html


def test_render_escapes_html_in_descriptions(tmp_path):
    evil = snapshot("2026-08-08", {"ai/xss": (10000, "mlops", "<script>alert('x')</script>")})
    context = build_context(evil, None, [evil])
    out = tmp_path / "report.html"
    render_report(context, out)
    html = out.read_text(encoding="utf-8")
    assert "&lt;script&gt;alert(&#39;x&#39;)&lt;/script&gt;" in html
    assert "<script>alert" not in html


def test_first_run_degrades_gracefully(tmp_path):
    context = build_context(CURRENT, None, [CURRENT])
    assert "首次运行" in context["main_note"]
    assert all(item["weekly_gain"] is None for item in context["main"])
    assert context["stats_cards"][2]["value"] == "—"
    assert context["trend"]["series"][0]["dots"]  # 单快照也有数据点
    out = tmp_path / "first.html"
    render_report(context, out)
    assert "首次运行" in out.read_text(encoding="utf-8")
