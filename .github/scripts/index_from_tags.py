import json
import os
import re
import sys
import time
from pathlib import Path
import urllib.request
from urllib.parse import urlparse

INDEX_DIR = Path("index")

# Accept:
#  - v1.2.3
#  - v1.2.3-rc.1
#  - v1.2.3+build.5
# Captures "1.2.3" (without the leading v)
TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)(?:[-+].*)?$")


def http_get(url: str, token: str):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.getcode(), resp.headers, resp.read()


def gh_list_tags(owner: str, repo: str, token: str):
    tags = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{owner}/{repo}/tags?per_page=100&page={page}"
        code, _, body = http_get(url, token)
        if code != 200:
            raise RuntimeError(f"GitHub API failed: {url} -> {code}")
        arr = json.loads(body.decode("utf-8"))
        if not arr:
            break
        tags.extend(arr)
        if len(arr) < 100:
            break
        page += 1
        time.sleep(0.2)
    return tags


def parse_repo_url(repo_url: str):
    """
    Extract (owner, repo) from:
      - https://github.com/Owner/Repo
      - https://github.com/Owner/Repo.git
      - git@github.com:Owner/Repo.git
      - ssh://git@github.com/Owner/Repo.git

    Returns tuple(str owner, str repo) preserving case, or None.
    """
    if not repo_url:
        return None

    u = repo_url.strip()
    if not u:
        return None

    # git@github.com:Owner/Repo(.git)
    m = re.match(r"^git@github\.com:([^/]+)/(.+?)(?:\.git)?$", u)
    if m:
        owner = m.group(1).strip()
        repo = m.group(2).strip()
        if owner and repo:
            return owner, repo
        return None

    # ssh://git@github.com/Owner/Repo(.git) OR https://github.com/Owner/Repo(.git)
    try:
        p = urlparse(u)
    except Exception:
        return None

    if (p.netloc or "").lower() != "github.com":
        return None

    path = (p.path or "").strip("/")
    parts = [x for x in path.split("/") if x]
    if len(parts) < 2:
        return None

    owner = parts[0].strip()
    repo = parts[1].strip()
    if repo.endswith(".git"):
        repo = repo[:-4]

    if not owner or not repo:
        return None

    return owner, repo


def main():
    token = os.environ.get("GH_TOKEN", "")
    if not INDEX_DIR.exists():
        print("index/ not found", file=sys.stderr)
        return 1

    changed = 0

    for entry_path in sorted(INDEX_DIR.glob("*.json")):
        with entry_path.open("r", encoding="utf-8") as f:
            entry = json.load(f)

        repo_url = (((entry.get("repo") or {}).get("url")) or "").strip()
        parsed = parse_repo_url(repo_url)
        if not parsed:
            print(f"[warn] {entry_path.name}: cannot parse github repo from url={repo_url!r}")
            continue

        owner, repo = parsed

        try:
            tags = gh_list_tags(owner, repo, token)
        except Exception as e:
            print(f"[warn] {entry_path.name}: cannot list tags for {owner}/{repo}: {e}")
            continue

        print(f"[info] {entry_path.name}: repo={owner}/{repo} tags={len(tags)}")

        versions = entry.get("versions")
        if not isinstance(versions, dict):
            versions = {}

        new_versions = {}
        for t in tags:
            name = (t.get("name") or "").strip()
            sha = ((t.get("commit") or {}).get("sha") or "").strip()
            m = TAG_RE.match(name)
            if not m or not sha:
                continue
            ver = m.group(1)  # "1.2.3"
            new_versions[ver] = {"tag": name, "commit": sha}

        print(f"[info] {entry_path.name}: matched_versions={len(new_versions)}")
        if tags and not new_versions:
            sample = [((t.get("name") or "").strip()) for t in tags[:10]]
            print(f"[warn] {entry_path.name}: tags found but none matched TAG_RE. sample={sample}")

        # Ensure stable JSON output: sort versions keys
        new_versions_sorted = dict(sorted(new_versions.items(), key=lambda kv: kv[0]))

        if new_versions_sorted != versions:
            entry["versions"] = new_versions_sorted
            with entry_path.open("w", encoding="utf-8") as f:
                json.dump(entry, f, indent=2, ensure_ascii=False)
                f.write("\n")
            changed += 1

    print(f"updated entries: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
