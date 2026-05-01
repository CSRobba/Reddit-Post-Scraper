"""
Restore any raw JSON file where something other than 'relevance_rate' or
'relevance_reasoning' changed relative to HEAD.
"""

import re
import subprocess
import sys

ALLOWED_CHANGED_KEYS = {"relevance_rate", "relevance_reasoning"}

# Matches top-level JSON keys (exactly 4 spaces indent = one level deep)
_TOP_KEY_RE = re.compile(r'^[+-]    "(\w+)"\s*:')

def get_repo_root():
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip()

REPO_ROOT = get_repo_root()

def get_modified_files():
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "raw/"],
        capture_output=True, text=True, check=True, cwd=REPO_ROOT
    )
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]

def changed_top_level_keys(fpath):
    """Return the set of top-level JSON keys that differ in the raw diff."""
    result = subprocess.run(
        ["git", "diff", "HEAD", "--", fpath],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    keys = set()
    for line in result.stdout.splitlines():
        if line.startswith(("+++", "---", "@@")):
            continue
        m = _TOP_KEY_RE.match(line)
        if m:
            keys.add(m.group(1))
    return keys

def main(dry_run=False):
    modified = get_modified_files()
    to_restore = []

    for fpath in modified:
        changed = changed_top_level_keys(fpath)
        non_rating = changed - ALLOWED_CHANGED_KEYS
        if non_rating:
            to_restore.append((fpath, non_rating))

    print(f"Files to restore: {len(to_restore)} / {len(modified)} modified")
    for fpath, non_rating in to_restore:
        print(f"  restoring: {fpath}  (changed: {', '.join(sorted(non_rating))})")
        if not dry_run:
            subprocess.run(["git", "restore", fpath], check=True, cwd=REPO_ROOT)

    if dry_run:
        print("\n(dry run — no files changed)")

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
