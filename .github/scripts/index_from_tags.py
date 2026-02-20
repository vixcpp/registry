import json
import os
import re
import sys
import time
from pathlib import Path
import urllib.request
import subprocess
from typing import Optional

INDEX_DIR = Path("index")
TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)(?:[-+].*)?$")

def http_get(url: str, token: str):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.getcode(), resp.headers, resp.read()

def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return (p.stdout or "").strip()

def resolve_tag_commit(repo_url: str, tag: str) -> Optional[str]:
    # Annotated tags: use peeled commit via ^{}
    out = run(["git", "ls-remote", repo_url, f"refs/tags/{tag}^{{}}"])
    if out:
        return out.splitlines()[0].split("\t", 1)[0].strip()

    # Lightweight tags: direct ref hash is the commit
    out = run(["git", "ls-remote", repo_url, f"refs/tags/{tag}"])
    if out:
        return out.splitlines()[0].split("\t", 1)[0].strip()

    return None

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

def parse_repo_url(url: str):
    # supports https://github.com/owner/repo and git@github.com:owner/repo
    u = url.strip()
    if u.endswith(".git"):
        u = u[:-4]
    if u.startswith("git@github.com:"):
        path = u[len("git@github.com:"):]
    elif "github.com/" in u:
        path = u.split("github.com/", 1)[1]
    else:
        return None
    if "/" not in path:
        return None
    owner, repo = path.split("/", 1)
    if not owner or not repo:
        return None
    return owner.lower(), repo.lower()

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
            continue

        owner, repo = parsed
        try:
            tags = gh_list_tags(owner, repo, token)
        except Exception as e:
            print(f"[warn] {entry_path.name}: cannot list tags for {owner}/{repo}: {e}")
            continue

        versions = entry.get("versions")
        if not isinstance(versions, dict):
            versions = {}

        new_versions = {}
        for t in tags:
            name = (t.get("name") or "").strip()
            m = TAG_RE.match(name)
            if not m:
                continue

            commit = resolve_tag_commit(repo_url, name)
            if not commit:
                continue

            ver = m.group(1)
            new_versions[ver] = {"tag": name, "commit": commit}

        # keep stable ordering when dumping
        if new_versions != versions:
            entry["versions"] = new_versions
            with entry_path.open("w", encoding="utf-8") as f:
                json.dump(entry, f, indent=2, ensure_ascii=False)
                f.write("\n")
            changed += 1

    print(f"updated entries: {changed}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
