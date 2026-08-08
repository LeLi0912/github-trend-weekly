from github_ai_weekly.ranking import (
    category_rankings,
    compute_deltas,
    filter_repos,
    main_ranking,
    new_faces,
    star_history,
    summary_stats,
)


def record(stars, category="llm_framework", archived=False, fork=False, is_template=False, description="d"):
    return {
        "stars": stars,
        "forks": stars // 10,
        "description": description,
        "url": f"https://github.com/x/y",
        "category": category,
        "archived": archived,
        "fork": fork,
        "is_template": is_template,
        "topics": [],
        "language": "Python",
        "pushed_at": None,
    }


def snapshot(date, pairs):
    return {"date": date, "repos": {name: record(*meta) for name, meta in pairs.items()}}


def test_filter_repos_applies_thresholds():
    snap = snapshot(
        "2026-08-08",
        {
            "a/low": (500,),
            "a/archived": (5000, "llm_framework", True),
            "a/fork": (5000, "llm_framework", False, True),
            "a/template": (5000, "llm_framework", False, False, True),
            "a/ok": (1000,),
        },
    )
    filtered = filter_repos(snap)
    assert list(filtered) == ["a/ok"]


def test_compute_deltas_and_main_ranking():
    current = snapshot(
        "2026-08-08",
        {
            "a/gain20": (1020,),
            "a/gain30": (1030,),
            "a/new": (2000, "agent"),
            "a/same": (5000,),
        },
    )
    previous = snapshot(
        "2026-08-01",
        {
            "a/gain20": (1000,),
            "a/gain30": (1000,),
            "a/same": (5000,),
        },
    )
    deltas = compute_deltas(current, previous)
    assert deltas["a/gain20"]["weekly_gain"] == 20
    assert deltas["a/gain20"]["daily_est"] == 3
    assert deltas["a/same"]["weekly_gain"] == 0
    assert deltas["a/new"]["is_new"] is True

    ranked = main_ranking(deltas)
    assert [item["full_name"] for item in ranked] == ["a/gain30", "a/gain20", "a/same", "a/new"]
    assert ranked[0]["rank"] == 1


def test_main_ranking_without_previous_sorts_by_stars():
    current = snapshot(
        "2026-08-08",
        {
            "a/big": (5000,),
            "a/small": (1000,),
        },
    )
    ranked = main_ranking(compute_deltas(current, None))
    assert [item["full_name"] for item in ranked] == ["a/big", "a/small"]
    assert all(item["weekly_gain"] is None for item in ranked)


def test_tiebreak_by_stars_then_name():
    current = snapshot(
        "2026-08-08",
        {
            "z/repo": (1100,),
            "a/repo": (1000,),
            "b/repo": (1000,),
        },
    )
    previous = snapshot(
        "2026-08-01",
        {"z/repo": (1000,), "a/repo": (1000,), "b/repo": (1000,)},
    )
    ranked = main_ranking(compute_deltas(current, previous))
    assert [item["full_name"] for item in ranked] == ["z/repo", "a/repo", "b/repo"]


def test_new_faces_and_category_rankings():
    current = snapshot(
        "2026-08-08",
        {
            "x/a": (2000, "agent"),
            "x/b": (1500, "agent"),
            "x/c": (1800, "rag"),
            "x/d": (1000, "rag"),
            "x/e": (3000, None),
        },
    )
    previous = snapshot("2026-08-01", {"x/c": (1500, "rag"), "x/d": (500, "rag")})
    deltas = compute_deltas(current, previous)

    faces = new_faces(deltas)
    # x/d 上周 500 星（未达门槛），本周 1000 星跨入榜单，也应算新上榜
    assert [item["full_name"] for item in faces] == ["x/e", "x/a", "x/b", "x/d"]

    by_category = category_rankings(deltas)
    assert [item["full_name"] for item in by_category["agent"]] == ["x/a", "x/b"]
    assert [item["full_name"] for item in by_category["rag"]] == ["x/c", "x/d"]
    assert "uncategorized" in by_category


def test_category_rankings_caps_at_top_n():
    current = snapshot(
        "2026-08-08",
        {f"c/r{i:02d}": (1000 + i, "eval") for i in range(15)},
    )
    previous = snapshot("2026-08-01", {f"c/r{i:02d}": (1000, "eval") for i in range(15)})
    deltas = compute_deltas(current, previous)
    assert len(category_rankings(deltas)["eval"]) == 10


def test_summary_stats():
    current = snapshot(
        "2026-08-08",
        {"a/one": (1100,), "b/two": (2000, "agent"), "c/three": (3000, "rag")},
    )
    previous = snapshot("2026-08-01", {"a/one": (1000,), "c/three": (2000, "rag")})
    stats = summary_stats(compute_deltas(current, previous))
    assert stats["repo_count"] == 3
    assert stats["total_stars"] == 6100
    assert stats["total_gain"] == 1100
    assert stats["new_count"] == 1
    assert stats["top_gainer"] == "c/three"
    assert stats["top_gain"] == 1000


def test_star_history_collects_points_across_snapshots():
    s1 = snapshot("2026-07-25", {"a/x": (1000,), "a/y": (900,) + (None,) * 0})
    s1["repos"]["a/y"] = record(900)
    s2 = snapshot("2026-08-01", {"a/x": (1100,)})
    s3 = snapshot("2026-08-08", {"a/x": (1300,)})
    history = star_history([s1, s2, s3], ["a/x", "a/y"])
    assert [p["date"] for p in history["a/x"]] == ["2026-07-25", "2026-08-01", "2026-08-08"]
    assert [p["stars"] for p in history["a/x"]] == [1000, 1100, 1300]
    assert [p["stars"] for p in history["a/y"]] == [900]
