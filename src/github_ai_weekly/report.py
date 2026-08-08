"""HTML 周报生成：上下文构建 + 模板渲染（自包含单文件）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import CATEGORY_LABELS, REPORT_TEMPLATE
from .ranking import (
    category_label,
    category_rankings,
    compute_deltas,
    main_ranking,
    new_faces,
    star_history,
    summary_stats,
)

TREND_COLORS = ["#22C55E", "#3B82F6", "#F59E0B", "#8B5CF6", "#F43F5E"]
TREND_DASHES = ["", "6 4", "2 4", "6 2 2 2", "2 2"]


def _fmt(value: int | None) -> str:
    if value is None:
        return "—"
    return f"{value:,}"


def _enrich(item: dict[str, Any], max_gain: int | None) -> dict[str, Any]:
    """补充模板展示字段：分类标签、条形图宽度、日增/总星格式化。"""
    gain = item["weekly_gain"]
    bar_pct = 0
    if gain is not None and max_gain and max_gain > 0:
        bar_pct = round(gain / max_gain * 100, 1)
    item = dict(item)
    item["category_label"] = category_label(item["record"].get("category"))
    item["bar_pct"] = bar_pct
    item["stars_fmt"] = _fmt(item["record"]["stars"])
    item["gain_fmt"] = _fmt(gain)
    item["daily_fmt"] = _fmt(item["daily_est"])
    return item


def _build_trend(history: dict[str, list[dict[str, Any]]], max_series: int = 5) -> dict[str, Any] | None:
    if not history:
        return None
    names = list(history.keys())[:max_series]
    all_stars = [point["stars"] for name in names for point in history[name]]
    y_min, y_max = min(all_stars), max(all_stars)
    span = (y_max - y_min) or 1
    pad = span * 0.1
    y_lo, y_hi = y_min - pad, y_max + pad
    n = max(len(history[name]) for name in names)
    width, height = 760, 240
    margin = 24

    def x_of(index: int) -> float:
        if n == 1:
            return width / 2
        return margin + index * (width - 2 * margin) / (n - 1)

    def y_of(stars: int) -> float:
        return height - margin - (stars - y_lo) / (y_hi - y_lo) * (height - 2 * margin)

    dates = [{"label": point["date"][5:], "x": x_of(i)} for i, point in enumerate(history[names[0]])]
    series = []
    for idx, name in enumerate(names):
        points = history[name]
        line = (
            " ".join(
                f"{'M' if i == 0 else 'L'}{x_of(i):.1f} {y_of(p['stars']):.1f}"
                for i, p in enumerate(points)
            )
            if len(points) > 1
            else ""
        )
        dots = [{"cx": x_of(i), "cy": y_of(p["stars"]), "stars": p["stars"]} for i, p in enumerate(points)]
        series.append(
            {
                "name": name,
                "color": TREND_COLORS[idx % len(TREND_COLORS)],
                "dash": TREND_DASHES[idx % len(TREND_DASHES)],
                "line": line,
                "dots": dots,
                "latest": points[-1]["stars"],
                "delta": points[-1]["stars"] - points[0]["stars"],
            }
        )

    y_ticks = [
        {
            "y": y_of(round(y_lo + k * (y_hi - y_lo) / 3)),
            "value": _fmt(round(y_lo + k * (y_hi - y_lo) / 3)),
        }
        for k in range(4)
    ]
    trend_table = {
        "dates": [point["date"] for point in history[names[0]]],
        "rows": [
            {"name": name, "points": [p["stars"] for p in history[name]]} for name in names
        ],
    }
    return {
        "width": width,
        "height": height,
        "total_height": height + 40,
        "dates": dates,
        "series": series,
        "y_ticks": y_ticks,
        "table": trend_table,
        "summary": f"近 {n} 周 star 变化趋势（按本周涨幅前 {len(names)} 名）",
    }


def auto_commentary(
    stats: dict[str, Any],
    main: list[dict[str, Any]],
    has_previous: bool,
) -> list[str]:
    """基于数据规则生成可复现的结构化点评草稿。"""
    bullets: list[str] = []
    if stats["top_gainer"] and stats["top_gain"] is not None:
        bullets.append(f"本周涨幅最大的仓库是 {stats['top_gainer']}（+{stats['top_gain']:,} 星）。")
    if stats["new_count"]:
        top_new = next((item for item in main if item["is_new"]), None)
        if top_new:
            bullets.append(
                f"本周有 {stats['new_count']} 个新上榜仓库，其中 {top_new['full_name']} 以 {top_new['record']['stars']:,} 星居首。"
            )
    if stats["total_gain"]:
        bullets.append(f"上榜仓库合计 {stats['repo_count']} 个，总星标 {stats['total_stars']:,}，本周合计新增 {stats['total_gain']:,} 星。")
    if not has_previous:
        bullets.append("本期为首次运行，暂按总星标排序；下期起将展示周增量排名。")
    return bullets


def build_context(
    current: dict[str, Any],
    previous: dict[str, Any] | None = None,
    snapshots: list[dict[str, Any]] | None = None,
    extra_commentary: list[str] | None = None,
) -> dict[str, Any]:
    """汇总排名、趋势与点评，产出模板上下文。"""
    deltas = compute_deltas(current, previous)
    stats = summary_stats(deltas)
    ranked = main_ranking(deltas)
    max_gain = max((item["weekly_gain"] for item in ranked if item["weekly_gain"] is not None), default=None)
    main = [_enrich(item, max_gain) for item in ranked]
    faces = [_enrich(item, max_gain) for item in new_faces(deltas)]

    by_category = category_rankings(deltas)
    ordered_categories: list[tuple[str, list[dict[str, Any]]]] = []
    for key in list(CATEGORY_LABELS) + ["uncategorized"]:
        if key in by_category:
            ordered_categories.append((category_label(key), [_enrich(item, max_gain) for item in by_category[key]]))

    history = star_history(snapshots or [current], [item["full_name"] for item in ranked])
    trend = _build_trend(history)

    commentary = auto_commentary(stats, main, previous is not None)
    if extra_commentary:
        commentary.extend(extra_commentary)

    stats_cards = [
        {"label": "上榜仓库", "value": f"{stats['repo_count']}"},
        {"label": "总星标", "value": _fmt(stats["total_stars"])},
        {"label": "本周新增", "value": f"+{_fmt(stats['total_gain'])}" if stats["total_gain"] else "—"},
        {"label": "新上榜", "value": f"{stats['new_count']}"},
    ]
    return {
        "title": "GitHub AI 周榜",
        "date": current["date"],
        "previous_date": previous["date"] if previous else None,
        "stats_cards": stats_cards,
        "main_note": (
            "按本周新增 star 排序；日均估算 = 周增量 ÷ 7。"
            if previous
            else "首次运行：暂按总星标排序，暂无周增量数据。"
        ),
        "main": main,
        "new_faces": faces,
        "categories": ordered_categories,
        "trend": trend,
        "commentary": commentary,
    }


def render_report(context: dict[str, Any], output_path: Path, template_path: Path = REPORT_TEMPLATE) -> Path:
    """渲染自包含 HTML 报告（确定性输出，相同输入产出相同字节）。"""
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=select_autoescape(["html", "xml", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["fmt"] = _fmt
    html = env.get_template(template_path.name).render(**context)
    output_path.write_text(html, encoding="utf-8")
    return output_path
