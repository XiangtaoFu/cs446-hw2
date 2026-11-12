"""One-command VS Code setup for the course AI assistant.

    python student_setup.py --key sk-your-key

Works on Windows, macOS and Linux. Merges the course models into VS Code's model
configuration without disturbing anything already there, and backs the file up first.

Hand-editing chatLanguageModels.json across a whole class produces a predictable stream of
"it says invalid JSON" emails. This does the edit for them and validates the endpoint
before they ever open the chat panel.
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

GROUP_NAME = "Course Gateway"

# The gateway address is the same for the whole class -- only the key differs -- so it is
# baked in rather than asked for. A URL typed forty times is forty chances to typo it, and
# a mistyped host produces a connection error that looks nothing like its cause.
#
# Jetstream2 derives this from the instance name (`gateway`), so it changes only if that
# instance is renamed or replaced. If that happens, edit this one line and every student
# re-runs the script; --url overrides it in the meantime.
GATEWAY_URL = "https://gateway.cis261803.projects.jetstream-cloud.org/v1"

# Kept in one place so a single edit re-publishes the roster to everyone.
# Context limits are deliberately below the server's own ceiling: VS Code counts tokens
# differently, and hitting the server limit mid-session shows up as an opaque 400.
#
# The gateway also lists course-model-offline for student keys -- the fixed reply it gives
# while the GPU is off -- which is deliberately not offered here: nobody should pick it,
# it only stands in when the real model is down.
MODELS = [
    {"id": "Nemotron-Cascade-2-30B-A3B", "name": "Nemotron-Cascade-2-30B-A3B",
     "toolCalling": True, "vision": False,
     "maxInputTokens": 120000, "maxOutputTokens": 8000},
    {"id": "qwen-3.8-27b", "name": "Qwen 3.8 27B",
     "toolCalling": True, "vision": False,
     "maxInputTokens": 120000, "maxOutputTokens": 8000},
    {"id": "muse-glimmer", "name": "Muse Glimmer",
     "toolCalling": True, "vision": False,
     "maxInputTokens": 120000, "maxOutputTokens": 8000},
]

MIN_VSCODE = (1, 122)


def config_path() -> Path:
    """VS Code stores this per user, in a different place on each OS."""
    system = platform.system()
    if system == "Windows":
        base = Path.home() / "AppData" / "Roaming" / "Code" / "User"
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support" / "Code" / "User"
    else:
        base = Path.home() / ".config" / "Code" / "User"
    return base / "chatLanguageModels.json"


def check_endpoint(url: str, key: str) -> list[str]:
    """Confirm the gateway answers and report which models it offers.

    Done before touching any config: a wrong URL or a mistyped key is by far the most
    common failure, and finding out here is much clearer than a red error inside the chat
    panel later.
    """
    models_url = url.rstrip("/").removesuffix("/chat/completions").rstrip("/") + "/models"
    req = urllib.request.Request(models_url, headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return [m["id"] for m in json.load(r).get("data", [])]
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise SystemExit(
                f"The server rejected your API key (HTTP {e.code}).\n"
                f"Copy it again -- a missing character or a trailing space is the usual cause."
            )
        raise SystemExit(f"The server answered HTTP {e.code} at {models_url}")
    except urllib.error.URLError as e:
        raise SystemExit(
            f"Could not reach {models_url}\n  {e.reason}\n"
            f"Check the URL, and that you are on a network that can reach it."
        )


def completions_url(url: str) -> str:
    u = url.rstrip("/")
    return u if u.endswith("/chat/completions") else u + "/chat/completions"


def merge(existing: list, url: str, available: list[str]) -> list:
    """Replace our group, leave every other provider untouched.

    Students may already have Ollama or something else configured; wiping that would be
    rude and would also make this script unsafe to re-run.
    """
    kept = [g for g in existing if g.get("name") != GROUP_NAME]
    models = [
        {**m, "url": completions_url(url)}
        for m in MODELS
        if not available or m["id"] in available
    ]
    if not models:
        raise SystemExit(
            f"None of the course models are offered by that server.\n"
            f"It offers: {', '.join(available) or '(nothing)'}"
        )
    kept.append({
        "name": GROUP_NAME,
        "vendor": "customendpoint",
        "apiType": "chat-completions",
        "models": models,
    })
    return kept


def main() -> int:
    ap = argparse.ArgumentParser(description="Set up the course AI assistant in VS Code")
    ap.add_argument("--key", required=True, help="your personal API key (sk-...)")
    ap.add_argument("--url", default=GATEWAY_URL, help=f"gateway URL (default: {GATEWAY_URL})")
    ap.add_argument("--dry-run", action="store_true", help="show what would change, write nothing")
    args = ap.parse_args()

    print(f"Checking {args.url} ...")
    available = check_endpoint(args.url, args.key)
    print(f"  reachable, offers: {', '.join(available)}")

    path = config_path()
    print(f"\nVS Code config: {path}")

    existing = []
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                existing = []
        except json.JSONDecodeError:
            print("  (existing file is not valid JSON; it will be replaced, "
                  "a backup is written first)")
            existing = []

    merged = merge(existing, args.url, available)
    added = next(g for g in merged if g["name"] == GROUP_NAME)

    print(f"\nModels to add under '{GROUP_NAME}':")
    for m in added["models"]:
        print(f"  {m['id']:16} -> {m['url']}")
    others = [g["name"] for g in merged if g["name"] != GROUP_NAME]
    if others:
        print(f"Leaving alone: {', '.join(others)}")

    if args.dry_run:
        print("\nDry run; nothing was written.")
        return 0

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name(f"{path.stem}.backup-{datetime.now():%Y%m%d-%H%M%S}.json")
        shutil.copy2(path, backup)
        print(f"\nBacked up to {backup.name}")

    path.write_text(json.dumps(merged, indent="\t") + "\n", encoding="utf-8")
    print(f"Wrote {path}")

    print(f"""
Done. In VS Code:

  1. Reload the window:  Ctrl+Shift+P  ->  Developer: Reload Window
     (Cmd+Shift+P on a Mac)
  2. Open the Chat view:  Ctrl+Alt+I   (Ctrl+Cmd+I on a Mac)
  3. Click 'Models' at the bottom of the chat box and pick
     '{added['models'][0]['name']}'
  4. Add your API key to the models: click the + on the right, find the
     '{GROUP_NAME}' models, right-click  ->  Update API Key, and paste your key.

If 'Custom Endpoint' is missing, VS Code is older than {MIN_VSCODE[0]}.{MIN_VSCODE[1]};
update it (Help -> About shows the version).
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
