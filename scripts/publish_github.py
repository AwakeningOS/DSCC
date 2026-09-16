#!/usr/bin/env python3
"""Owner-run GitHub publication helper. Preview by default, private by default."""
from __future__ import annotations
import argparse
import re
import shlex
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = ["README.md", "AGENTS.md", "CONTRIBUTING.md", "SECURITY.md", "LICENSE",
           "CITATION.cff", "pyproject.toml", ".gitignore", ".github", "src", "tests",
           "scripts", "docs", "schemas", "examples", "reports"]


def run(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=ROOT, check=check, capture_output=True, text=True)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--public", action="store_true", help="Explicitly publish publicly; default is private")
    p.add_argument("--execute", action="store_true")
    a = p.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", a.repo):
        p.error("--repo must be owner/name")
    visibility = "--public" if a.public else "--private"
    create = ["gh", "repo", "create", a.repo, visibility, "--source", str(ROOT),
              "--remote", "origin", "--push", "--description",
              "DSCC Desktop: local-first shared scientific assets and voluntary compute"]
    print("Target:", a.repo, "Visibility:", "public" if a.public else "private")
    print("Planned commands (existing remote/repository will cause refusal):")
    for args in (["git", "init", "-b", "main"], ["git", "add", "--", *ALLOWED],
                 ["git", "commit", "-m", "Initial DSCC Desktop foundation"], create):
        print(shlex.join(args))
    if not a.execute:
        print("Preview only. Review the source tree, then rerun with --execute.")
        return
    if not shutil.which("git") or not shutil.which("gh"):
        p.error("Install Git and GitHub CLI, then authenticate gh on your own computer")
    if run(["gh", "auth", "status"], check=False).returncode:
        p.error("GitHub CLI is not authenticated. Run gh auth login locally; do not paste a token into chat")
    if run(["gh", "repo", "view", a.repo, "--json", "nameWithOwner"], check=False).returncode == 0:
        p.error("Repository already exists; refusing to overwrite or assume it is empty")
    if not (ROOT / ".git").exists():
        run(["git", "init", "-b", "main"])
    if run(["git", "remote"], check=False).stdout.strip():
        p.error("A remote already exists. Review and push manually instead of replacing it")
    if run(["git", "rev-parse", "--abbrev-ref", "HEAD"], check=False).stdout.strip() not in ("main", "HEAD", ""):
        p.error("Current branch is not main; refusing to switch it")
    # Prevent accidental publishing of live node state even when force-added by another tool.
    tracked = run(["git", "ls-files"], check=False).stdout.splitlines()
    if any(x.endswith((".key", ".pem", ".sqlite3")) or "/.dscc/" in f"/{x}" for x in tracked):
        p.error("Sensitive-looking tracked files found; inspect repository before publishing")
    run(["git", "add", "--", *ALLOWED])
    if run(["git", "diff", "--cached", "--quiet"], check=False).returncode != 0:
        try:
            run(["git", "commit", "-m", "Initial DSCC Desktop foundation"])
        except subprocess.CalledProcessError as exc:
            raise SystemExit("Commit failed. Set your local Git author identity and review git status.\n" + exc.stderr)
    result = run(create, check=False)
    print(result.stdout)
    if result.returncode:
        raise SystemExit("Creation or push failed. A repository may have been partially created; inspect GitHub before retrying.\n" + result.stderr)


if __name__ == "__main__":
    main()
