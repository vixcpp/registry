import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # repo root
INDEX_DIR = ROOT / "index"

PKG_NS_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")
PKG_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+][0-9A-Za-z.-]+)?$")

def tag_points_to_commit(repo_url: str, tag: str, commit: str) -> bool:
    # For annotated tags, peeled ref gives the commit
    out = git_ls_remote(repo_url, f"refs/tags/{tag}^{{}}")
    if out:
        got = out.splitlines()[0].split("\t", 1)[0].strip()
        return got.lower() == commit.lower()

    # For lightweight tags, direct ref hash is the commit
    out = git_ls_remote(repo_url, f"refs/tags/{tag}")
    if out:
        got = out.splitlines()[0].split("\t", 1)[0].strip()
        return got.lower() == commit.lower()

    return False

def run(cmd: list[str], check: bool = True, capture: bool = True) -> str:
    p = subprocess.run(
        cmd,
        check=False,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True,
    )
    if check and p.returncode != 0:
        if capture:
            print("Command failed:", " ".join(cmd))
            print("stdout:", p.stdout)
            print("stderr:", p.stderr, file=sys.stderr)
        raise SystemExit(p.returncode)
    return (p.stdout or "").strip()

def gh_api(path: str) -> dict:
    # requires GH_TOKEN
    out = run(["gh", "api", "-H", "Accept: application/vnd.github+json", path], check=True, capture=True)
    return json.loads(out)

def list_changed_files() -> list[str]:
    # compare base..head
    base = run(["git", "merge-base", "HEAD", "origin/main"])
    out = run(["git", "diff", "--name-only", f"{base}..HEAD"])
    files = [f.strip() for f in out.splitlines() if f.strip()]
    return files

def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Invalid JSON: {path}: {e}", file=sys.stderr)
        raise SystemExit(1)

def is_https_github_repo(url: str) -> bool:
    return url.startswith("https://github.com/") and " " not in url and "\n" not in url

def git_ls_remote(repo_url: str, ref: str) -> str:
    # ref can be commit hash, refs/tags/v1.2.3, etc.
    # returns lines: "<hash>\t<ref>"
    return run(["git", "ls-remote", repo_url, ref], check=False, capture=True)

def tag_exists(repo_url: str, tag: str) -> bool:
    # Handle annotated tags: ls-remote may return both tag object and peeled ^{}
    # We accept if any line contains refs/tags/<tag> or refs/tags/<tag>^{}
    out = git_ls_remote(repo_url, f"refs/tags/{tag}")
    out2 = git_ls_remote(repo_url, f"refs/tags/{tag}^{{}}")
    combined = (out + "\n" + out2).strip()
    if not combined:
        return False
    for line in combined.splitlines():
        if f"refs/tags/{tag}" in line:
            return True
    return False

def commit_exists(repo_url: str, commit: str) -> bool:
    # ls-remote with a raw hash returns that hash if reachable on remote
    out = git_ls_remote(repo_url, commit)
    return bool(out.strip())

def validate_entry_file(path: Path) -> None:
    entry = load_json(path)

    if not isinstance(entry, dict):
        raise SystemExit(f"Entry must be a JSON object: {path}")

    ns = entry.get("namespace")
    name = entry.get("name")
    versions = entry.get("versions")

    if not isinstance(ns, str) or not PKG_NS_RE.match(ns):
        raise SystemExit(f"Invalid namespace in {path}: {ns}")

    if not isinstance(name, str) or not PKG_NAME_RE.match(name):
        raise SystemExit(f"Invalid name in {path}: {name}")

    if not isinstance(versions, dict) or not versions:
        raise SystemExit(f"Missing or empty versions in {path}")

    repo = entry.get("repo", {})
    if not isinstance(repo, dict):
        raise SystemExit(f"repo must be an object in {path}")

    repo_url = repo.get("url")
    if not isinstance(repo_url, str) or not is_https_github_repo(repo_url):
        raise SystemExit(f"Invalid repo.url in {path}: {repo_url}")

    for ver, meta in versions.items():
        if not isinstance(ver, str) or not SEMVER_RE.match(ver):
            raise SystemExit(f"Invalid version key in {path}: {ver}")

        if not isinstance(meta, dict):
            raise SystemExit(f"Version meta must be an object in {path} for {ver}")

        tag = meta.get("tag")
        commit = meta.get("commit")

        if not isinstance(tag, str) or not tag:
            raise SystemExit(f"Missing tag in {path} for {ver}")

        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-fA-F]{7,40}", commit):
            raise SystemExit(f"Invalid commit in {path} for {ver}: {commit}")

        if not tag_exists(repo_url, tag):
            raise SystemExit(f"Tag not found on remote: {repo_url} {tag} (file {path}, version {ver})")

        if not tag_points_to_commit(repo_url, tag, commit):
            raise SystemExit(
                f"Tag does not point to commit: {repo_url} {tag} -> {commit} (file {path}, version {ver})"
            )

def pr_mergeable_or_fail(repo: str, pr_number: str) -> None:
    # mergeable can be null initially, so retry a bit
    for _ in range(8):
        pr = gh_api(f"repos/{repo}/pulls/{pr_number}")
        mergeable = pr.get("mergeable")
        state = pr.get("mergeable_state")
        if mergeable is not None:
            if mergeable is True and state in ("clean", "unstable"):
                return
            raise SystemExit(f"PR not mergeable: mergeable={mergeable} state={state}")
        time.sleep(2)

    raise SystemExit("PR mergeable state is still unknown after retries")

def main() -> int:
    pr_number = os.getenv("PR_NUMBER", "").strip()
    repo = os.getenv("REPO", "").strip()

    if not pr_number or not repo:
        print("Missing PR_NUMBER or REPO env", file=sys.stderr)
        return 1

    changed = list_changed_files()
    if not changed:
        raise SystemExit("No changed files detected")

    # Only allow changes inside index/*.json (and optional metadata files if you want)
    allowed = []
    for f in changed:
        if f.startswith("index/") and f.endswith(".json"):
            allowed.append(f)
        else:
            raise SystemExit(f"Disallowed file change in PR: {f}")

    if not allowed:
        raise SystemExit("No index/*.json changes found")

    # Validate each changed entry file
    for rel in allowed:
        p = ROOT / rel
        if not p.exists():
            raise SystemExit(f"Changed file missing in workspace: {rel}")
        validate_entry_file(p)

    # Ensure PR has no conflicts and is mergeable
    pr_mergeable_or_fail(repo, pr_number)

    print("OK: registry PR validated and mergeable")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
