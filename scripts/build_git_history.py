#!/usr/bin/env python3
"""Build the git history page from the Workout Logger repository's branches.

Run it from inside a full clone of the Workout Logger repository:
    python3 path/to/build_git_history.py OUTPUT_DIR
"""

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json
import re
import subprocess
import sys


# Only branches pushed to GitHub are shown. Reading refs/remotes/origin keeps the
# page the same whether it is built on the Actions runner or on a laptop, where
# local-only branches would otherwise leak in.
REMOTE = "refs/remotes/origin/"
TEMPLATE = Path(__file__).resolve().parent.parent / "page" / "template.html"


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True)


def read_commits() -> list[dict]:
    # \x1e separates commits and \x1f separates fields, so commit messages can
    # contain any normal character. --numstat adds per-file line counts.
    out = git(
        "log", "--remotes=origin", "--date-order", "--numstat",
        f"--decorate-refs={REMOTE}", f"--decorate-refs-exclude={REMOTE}HEAD",
        "--format=\x1e%h\x1f%H\x1f%p\x1f%aI\x1f%an\x1f%s\x1f%D",
    )
    commits = []
    for record in out.split("\x1e")[1:]:
        header, *stat_lines = record.split("\n")
        short_hash, full_hash, parents, date, author, subject, refs = header.split("\x1f")
        added = removed = files = 0
        for line in stat_lines:
            parts = line.split("\t")
            if len(parts) == 3:
                files += 1
                if parts[0] != "-":  # binary files show "-" instead of counts
                    added += int(parts[0])
                    removed += int(parts[1])
        commits.append({
            "h": short_hash,
            "H": full_hash,
            "p": parents.split(),
            "d": date,
            "a": author,
            "s": subject,
            "r": [r.strip().removeprefix("origin/") for r in refs.split(",") if r.strip()],
            "ad": added,
            "de": removed,
            "f": files,
        })
    return commits


def read_branches() -> list[dict]:
    lines = git(
        "for-each-ref", "--sort=-committerdate",
        "--format=%(refname)\x1f%(objectname:short)\x1f%(committerdate:iso-strict)",
        REMOTE,
    ).splitlines()
    branches = []
    for line in lines:
        ref, short_hash, date = line.split("\x1f")
        name = ref.removeprefix(REMOTE)
        if name == "HEAD":
            continue
        branch = f"origin/{name}"
        branches.append({
            "name": name,
            "h": short_hash,
            "d": date,
            "ahead": int(git("rev-list", "--count", f"origin/main..{branch}")),
            "behind": int(git("rev-list", "--count", f"{branch}..origin/main")),
            "total": int(git("rev-list", "--count", branch)),
        })
    return branches


def read_repo_slug() -> str:
    """Return "owner/repo" from the origin URL, for links to commits on GitHub."""
    url = git("remote", "get-url", "origin").strip()
    match = re.search(r"github\.com[:/](.+?)(?:\.git)?/?$", url)
    return match.group(1) if match else ""


# Shown in search results and in link previews on WhatsApp, iMessage, Slack and so on.
DESCRIPTION = (
    "Every commit, branch and merge in Workout Logger, with a commit calendar, "
    "streaks and lines of code. Rebuilt every night."
)
# The tab icon: a gold ring around a gold dot, drawn inline so no image file is needed.
FAVICON = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='32' rx='8' fill='%23111316'/%3E"
    "%3Ccircle cx='16' cy='16' r='9' fill='none' stroke='%23E2B74D' stroke-width='2.5'/%3E"
    "%3Ccircle cx='16' cy='16' r='4.5' fill='%23E2B74D'/%3E%3C/svg%3E"
)


def main() -> None:
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
    commits = read_commits()
    branches = read_branches()
    if not commits or not branches:
        sys.exit("No commits or branches found. Was the repository checked out with full history?")

    # Show every time in the owner's timezone: the one most commits were made in.
    # Commits from cloud sessions are recorded in UTC, and without this they
    # would show UTC clock times as if they were local, hours off.
    home_tz = Counter(datetime.fromisoformat(c["d"]).utcoffset() for c in commits).most_common(1)[0][0]
    home_tz = timezone(home_tz)
    for item in commits + branches:
        item["d"] = datetime.fromisoformat(item["d"]).astimezone(home_tz).isoformat()

    now = datetime.now(timezone.utc)
    # "Today" is counted in the same timezone, so the current streak and the
    # "Today" label match the owner's calendar.
    local_now = now.astimezone(home_tz)
    zone = {"UTC+05:30": "IST"}.get(local_now.tzname(), local_now.tzname())
    built = local_now.strftime(f"%-d %b %Y, %H:%M {zone}")
    data = {
        "commits": commits,
        "branches": branches,
        # Branches are sorted newest first, so this is where the latest work is.
        "latest": branches[0]["name"],
        "built": built,
        "builtIso": now.isoformat(),
        "today": local_now.date().isoformat(),
        "zone": zone,
        "repo": read_repo_slug(),
    }
    # "</" is escaped so a commit message can never close the <script> tag early.
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    page = TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", payload)

    # The template holds the page's title, fonts and styles first, then its body.
    head, body = page.split('<div class="wrap">', 1)
    html = (
        '<!doctype html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        f'<meta name="description" content="{DESCRIPTION}">\n'
        '<meta property="og:title" content="Workout Logger History">\n'
        f'<meta property="og:description" content="{DESCRIPTION}">\n'
        '<meta property="og:type" content="website">\n'
        '<meta name="theme-color" content="#F3F4F1" media="(prefers-color-scheme: light)">\n'
        '<meta name="theme-color" content="#111316" media="(prefers-color-scheme: dark)">\n'
        f'<link rel="icon" href="{FAVICON}">\n'
        f"{head}<style>body{{margin:0}}</style>\n</head>\n<body>\n"
        f'<div class="wrap">{body}\n</body>\n</html>\n'
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"Wrote {out_dir / 'index.html'}: {len(commits)} commits, {len(branches)} branches, built {built}.")


if __name__ == "__main__":
    main()
