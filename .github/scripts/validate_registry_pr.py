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


def list_changed_files_with_status() -> list[tuple[str, str]]:
    """
    Returns list of (status, path) for changes vs origin/main merge-base.

    status is one of:
      - "A" added
      - "M" modified
      - "D" deleted

    Rename/copy changes are rejected to keep registry PRs simple and auditable.
    """
    base = run(["git", "merge-base", "HEAD", "origin/main"])
    out = run(["git", "diff", "--name-status", f"{base}..HEAD"])

    items: list[tuple[str, str]] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue

        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue

        st, path = parts[0].strip(), parts[1].strip()

        # Disallow renames/copies for strictness
        if st.startswith("R") or st.startswith("C"):
            raise SystemExit(f"Disallowed change type in PR: {st} {path}")

        if st not in ("A", "M", "D"):
            raise SystemExit(f"Unsupported change status: {st} {path}")

        items.append((st, path))

    return items


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Invalid JSON: {path}: {e}", file=sys.stderr)
        raise SystemExit(1)


def is_https_github_repo(url: str) -> bool:
    return url.startswith("https://github.com/") and " " not in url and "\n" not in url


def git_ls_remote(repo_url: str, ref: str) -> str:
    # returns lines: "<hash>\t<ref>"
    return run(["git", "ls-remote", repo_url, ref], check=False, capture=True)


def tag_exists(repo_url: str, tag: str) -> bool:
    # Accept lightweight tag ref OR annotated tag peeled ref
    out = git_ls_remote(repo_url, f"refs/tags/{tag}")
    out2 = git_ls_remote(repo_url, f"refs/tags/{tag}^{{}}")
    combined = (out + "\n" + out2).strip()
    if not combined:
        return False
    for line in combined.splitlines():
        if f"refs/tags/{tag}" in line:
            return True
    return False


def tag_points_to_commit(repo_url: str, tag: str, commit: str) -> bool:
    commit_l = commit.lower()

    # Annotated tags: peeled ref resolves to commit
    out = git_ls_remote(repo_url, f"refs/tags/{tag}^{{}}")
    if out:
        got = out.splitlines()[0].split("\t", 1)[0].strip().lower()
        return got == commit_l

    # Lightweight tags: direct ref resolves to commit
    out = git_ls_remote(repo_url, f"refs/tags/{tag}")
    if out:
        got = out.splitlines()[0].split("\t", 1)[0].strip().lower()
        return got == commit_l

    return False


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

        # Tag existence + tag->commit (peeled when annotated) is sufficient.
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

    changed = list_changed_files_with_status()
    if not changed:
        raise SystemExit("No changed files detected")

    # Only allow changes inside index/**/*.json
    allowed: list[tuple[str, str]] = []
    for st, f in changed:
        if f.startswith("index/") and f.endswith(".json"):
            allowed.append((st, f))
        else:
            raise SystemExit(f"Disallowed file change in PR: {st} {f}")

    if not allowed:
        raise SystemExit("No index/**/*.json changes found")

    # Validate added/modified entries. Deleted entries are allowed (unpublish).
    for st, rel in allowed:
        if st == "D":
            continue

        p = ROOT / rel
        if not p.exists():
            raise SystemExit(f"Changed file missing in workspace: {rel}")

        validate_entry_file(p)

    pr_mergeable_or_fail(repo, pr_number)

    print("OK: registry PR validated and mergeable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
