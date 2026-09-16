#!/usr/bin/env python3
"""Create prepared development issues using the owner's gh session."""
from __future__ import annotations
import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--execute", action="store_true")
    a = p.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", a.repo):
        p.error("expected owner/name")
    items = json.loads((ROOT / "docs/issues.json").read_text(encoding="utf-8"))
    if not a.execute:
        for i in items:
            print(i["title"])
        print("Preview only. Add --execute after the repository exists.")
        return
    if not shutil.which("gh"):
        p.error("GitHub CLI is required")
    existing = subprocess.run(["gh", "issue", "list", "--repo", a.repo, "--state", "all",
                               "--limit", "1000", "--json", "title"], check=True, capture_output=True, text=True)
    titles = {i["title"] for i in json.loads(existing.stdout)}
    for item in items:
        if item["title"] in titles:
            print("Already exists:", item["title"])
            continue
        with tempfile.TemporaryDirectory(prefix="dscc-issue-") as t:
            body = Path(t) / "body.md"
            body.write_text(item["body"], encoding="utf-8")
            subprocess.run(["gh", "issue", "create", "--repo", a.repo,
                            "--title", item["title"], "--body-file", str(body)], check=True)
    print("Issue seeding finished. No agents were started and no issues were auto-assigned.")


if __name__ == "__main__":
    main()
