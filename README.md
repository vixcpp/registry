# Vix Registry

A **cloudless, Git-based package registry** for Vix.

Vix Registry does not host packages.
It indexes them.

Packages live in Git repositories.
The registry provides **discovery, version resolution, and reproducibility** — nothing more.

This design keeps costs near zero, avoids fragile infrastructure, and aligns with Vix’s
**local-first / offline-first** philosophy.

---

## What Vix Registry Is

- A **Git repository** acting as a package index
- A **source of truth** for package metadata
- A **SemVer resolver** that maps versions → commits
- A foundation for **reproducible installs**

## What Vix Registry Is Not

- ❌ A cloud service
- ❌ A tarball host
- ❌ A VPS-backed registry
- ❌ A runtime dependency at build time

---

## Core Principles

### 1. Git is the distribution layer
Every package is a Git repository (GitHub-first in V1).

No file uploads.
No storage billing.
No single point of failure.

---

### 2. Index, not hosting
The registry only stores:

- package metadata
- repository locations
- version → commit mappings

The actual source code remains where it already belongs.

---

### 3. Reproducibility by default
All installations are pinned to **commit SHAs**, not floating tags.

Same lockfile → same code → same build.

---

### 4. Local-first & offline-friendly
- The registry index is cached locally
- Packages are cloned once and reused
- Offline installs work if dependencies are cached

---

## Repository Structure

```text
vix-registry/
├── registry.json
├── index/
│   └── example.package.json
├── namespaces/
├── policies/
└── README.md
```

---

## Package Entry (Concept)

Each package is described by a single JSON file inside `index/`.

```json
{
  "name": "rix",
  "namespace": "vixcpp",
  "repo": "https://github.com/vixcpp/rix",
  "license": "MIT",
  "type": "header-only",
  "manifestPath": "vix.json",
  "versions": {
    "1.0.0": { "tag": "v1.0.0", "commit": "abc123" }
  }
}
```

---

## How Vix Uses the Registry

```bash
vix registry sync
vix registry search json
vix add vixcpp/rix
vix install
```

---

## Publishing a Package (V1)

1. Public Git repository
2. SemVer tags
3. `vix.json` present
4. Explicit license
5. Pull request adding a JSON entry

---

## License

MIT

---

**Vix Registry**
*Indexing code, not hosting it.*

