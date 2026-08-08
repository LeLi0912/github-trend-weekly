"""排名计算：过滤、周增量、主榜、新面孔、分类榜与趋势历史。"""

from __future__ import annotations

from typing import Any

from .config import CATEGORY_LABELS, CATEGORY_TOP_N, MIN_STARS, TOP_N


def filter_repos(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """应用榜单口径：总星 >= MIN_STARS，排除 fork / 归档 / 模板仓库。"""
    filtered: dict[str, dict[str, Any]] = {}
    for full_name, record in snapshot["repos"].items():
        if record["stars"] < MIN_STARS:
            continue
        if record["archived"] or record["fork"] or record["is_template"]:
            continue
        filtered[full_name] = record
    return filtered


def compute_deltas(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    """计算每个仓库相对上一快照的周增量；无历史时 weekly_gain 为 None。"""
    prev_repos = filter_repos(previous) if previous else {}
    deltas: dict[str, dict[str, Any]] = {}
    for full_name, record in filter_repos(current).items():
        prev = prev_repos.get(full_name)
        gain = record["stars"] - prev["stars"] if prev else None
        deltas[full_name] = {
            "full_name": full_name,
            "name": full_name.split("/", 1)[1],
            "owner": full_name.split("/", 1)[0],
            "record": record,
            "previous": prev,
            "weekly_gain": gain,
            "daily_est": round(gain / 7) if gain is not None else None,
            "is_new": prev is None,
        }
    return deltas


def _sort_key(item: dict[str, Any]) -> tuple:
    gain = item["weekly_gain"]
    return (
        gain is None,  # 无增量排最后
        -(gain if gain is not None else 0),
        -item["record"]["stars"],
        item["full_name"],
    )


def main_ranking(deltas: dict[str, dict[str, Any]], top_n: int = TOP_N) -> list[dict[str, Any]]:
    """主榜：周增量降序（无历史时按总星），取前 top_n。"""
    ranked = sorted(deltas.values(), key=_sort_key)
    return [dict(item, rank=i + 1) for i, item in enumerate(ranked[:top_n])]


def new_faces(deltas: dict[str, dict[str, Any]], top_n: int = 10) -> list[dict[str, Any]]:
    """新面孔：上一快照不存在、且当前快照满足过滤条件的仓库，按总星降序。"""
    fresh = [item for item in deltas.values() if item["is_new"]]
    fresh.sort(key=lambda item: (-item["record"]["stars"], item["full_name"]))
    return [dict(item, rank=i + 1) for i, item in enumerate(fresh[:top_n])]


def category_rankings(
    deltas: dict[str, dict[str, Any]],
    top_n: int = CATEGORY_TOP_N,
) -> dict[str, list[dict[str, Any]]]:
    """分类子榜：按分类分组，各取周增量前 top_n（无历史时按总星）。"""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in deltas.values():
        category = item["record"].get("category") or "uncategorized"
        grouped.setdefault(category, []).append(item)
    result: dict[str, list[dict[str, Any]]] = {}
    for category, items in grouped.items():
        items.sort(key=_sort_key)
        result[category] = [
            dict(item, rank=i + 1) for i, item in enumerate(items[:top_n])
        ]
    return result


def summary_stats(deltas: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """摘要指标：上榜总数、总星、周增量合计、新面孔数、最大涨幅。"""
    total_stars = sum(item["record"]["stars"] for item in deltas.values())
    gains = [item["weekly_gain"] for item in deltas.values() if item["weekly_gain"] is not None]
    total_gain = sum(gains)
    new_count = sum(1 for item in deltas.values() if item["is_new"])
    with_gain = [item for item in deltas.values() if item["weekly_gain"] is not None]
    if with_gain:
        top_gainer = max(with_gain, key=lambda item: (item["weekly_gain"], item["record"]["stars"]))
    elif deltas:
        top_gainer = max(deltas.values(), key=lambda item: (item["record"]["stars"], item["full_name"]))
    else:
        top_gainer = None
    return {
        "repo_count": len(deltas),
        "total_stars": total_stars,
        "total_gain": total_gain,
        "new_count": new_count,
        "top_gainer": top_gainer["full_name"] if top_gainer else None,
        "top_gain": top_gainer["weekly_gain"] if top_gainer else None,
    }


def star_history(
    snapshots: list[dict[str, Any]],
    full_names: list[str],
) -> dict[str, list[dict[str, int]]]:
    """按快照日期收集指定仓库的 star 数历史，供趋势图使用。"""
    history: dict[str, list[dict[str, int]]] = {name: [] for name in full_names}
    for snapshot in snapshots:
        snapshot_date = snapshot["date"]
        for full_name in full_names:
            record = snapshot["repos"].get(full_name)
            if record:
                history[full_name].append({"date": snapshot_date, "stars": record["stars"]})
    return {name: points for name, points in history.items() if points}


def category_label(category: str | None) -> str:
    return CATEGORY_LABELS.get(category or "", "未分类")
