"""命令行入口：抓取快照、生成周报、离线演示。"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date
from pathlib import Path

from .config import ARCHIVE_DIR, INDEX_HTML, SNAPSHOT_DIR
from .github_api import GitHubClient
from .report import build_context, render_report
from .sample_data import build_sample_snapshots
from .snapshot import build_snapshot, load_snapshot, save_snapshot

log = logging.getLogger(__name__)


def _list_snapshots(directory: Path = SNAPSHOT_DIR) -> list[dict]:
    files = sorted(directory.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].json"))
    return [load_snapshot(path) for path in files]


def cmd_fetch(args: argparse.Namespace) -> int:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("错误：抓取需要 GITHUB_TOKEN 环境变量（GitHub REST API 限流）。", file=sys.stderr)
        return 2
    snapshot_date = args.date or date.today().isoformat()
    client = GitHubClient(token=token)
    snapshot = build_snapshot(client, snapshot_date)
    path = save_snapshot(snapshot)
    print(f"快照已保存：{path}（{len(snapshot['repos'])} 个仓库）")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    snapshots = _list_snapshots()
    if not snapshots:
        print("错误：data/snapshots 中没有快照，请先运行 fetch 或用 sample 演示。", file=sys.stderr)
        return 2
    current = snapshots[-1]
    previous = snapshots[-2] if len(snapshots) >= 2 else None
    context = build_context(current, previous, snapshots[-8:], extra_commentary=args.notes)
    index_path = render_report(context, INDEX_HTML)
    archive_path = ARCHIVE_DIR / f"{current['date']}.html"
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive_path.write_text(index_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"最新周报：{index_path}")
    print(f"历史存档：{archive_path}")
    return 0


def cmd_sample(args: argparse.Namespace) -> int:
    out_dir = Path("demo")
    snapshots = build_sample_snapshots()
    snap_dir = out_dir / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    for snapshot in snapshots:
        save_snapshot(snapshot, directory=snap_dir)
    current = snapshots[-1]
    previous = snapshots[-2]
    context = build_context(current, previous, snapshots, extra_commentary=args.notes)
    index_path = out_dir / "index.html"
    render_report(context, index_path)
    archive = out_dir / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    (archive / f"{current['date']}.html").write_text(index_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"演示周报已生成：{index_path.resolve()}（快照见 {snap_dir.resolve()}）")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="github-ai-weekly", description="GitHub AI 周榜：抓取快照并生成 HTML 周报")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="从 GitHub 抓取本周快照")
    fetch.add_argument("--date", help="快照日期 YYYY-MM-DD（默认今天）")
    fetch.set_defaults(func=cmd_fetch)

    report = sub.add_parser("report", help="由最近快照生成 index.html 与 archive 存档")
    report.add_argument("--notes", nargs="*", default=[], help="附加人工点评（可选）")
    report.set_defaults(func=cmd_report)

    sample = sub.add_parser("sample", help="离线生成演示快照与周报（无需 token/网络）")
    sample.add_argument("--notes", nargs="*", default=[], help="附加人工点评（可选）")
    sample.set_defaults(func=cmd_sample)
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    return args.func(args)
