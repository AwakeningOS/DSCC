#!/usr/bin/env python3
"""Generate configuration snippets; never modify installed client settings."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    home = str(a.home.expanduser().resolve())
    root = Path(__file__).resolve().parents[1]
    # Preserve a venv executable symlink; resolving it could select system Python.
    executable = str(Path(sys.executable).absolute())
    arguments = ["-m", "dscc", "--home", home, "mcp"]
    entry = {"command": executable, "args": arguments, "env": {"PYTHONPATH": str(root / "src")}}
    a.out.mkdir(parents=True, exist_ok=True)
    with (a.out / "lmstudio.mcp.json").open("x", encoding="utf-8") as f:
        json.dump({"mcpServers": {"dscc": entry}}, f, ensure_ascii=False, indent=2)
    text = ("[mcp_servers.dscc]\ncommand = " + json.dumps(executable, ensure_ascii=False) + "\nargs = "
            + json.dumps(arguments, ensure_ascii=False) + "\n\n[mcp_servers.dscc.env]\nPYTHONPATH = "
            + json.dumps(str(root / "src"), ensure_ascii=False) + "\n")
    with (a.out / "codex.config.toml").open("x", encoding="utf-8") as f:
        f.write(text)
    print(f"Configuration snippets created in {a.out}. Merge entries; do not overwrite existing settings.")


if __name__ == "__main__":
    main()
