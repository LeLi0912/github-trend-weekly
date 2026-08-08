from datetime import date
import argparse

from github_ai_weekly.cli import cmd_sample
from github_ai_weekly.sample_data import build_sample_snapshots
from github_ai_weekly.snapshot import load_snapshot, validate_snapshot


def test_sample_snapshots_are_valid_and_increasing():
    snapshots = build_sample_snapshots(date(2026, 8, 8))
    assert [s["date"] for s in snapshots] == ["2026-07-25", "2026-08-01", "2026-08-08"]
    assert all(validate_snapshot(s) == [] for s in snapshots)
    for full_name in snapshots[0]["repos"]:
        stars = [s["repos"][full_name]["stars"] for s in snapshots]
        assert stars == sorted(stars)


def test_cmd_sample_generates_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    args = argparse.Namespace(notes=[])
    assert cmd_sample(args) == 0
    assert (tmp_path / "demo" / "index.html").is_file()
    snap_files = list((tmp_path / "demo" / "snapshots").glob("*.json"))
    assert len(snap_files) == 3
    html = (tmp_path / "demo" / "index.html").read_text(encoding="utf-8")
    assert "GitHub AI 周榜" in html
    assert load_snapshot(snap_files[1])["source"] == "sample"
