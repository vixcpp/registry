# Vix Registry — Architecture

## Purpose

Build a **registry without cloud storage**: no VPS to maintain for hosting tarballs, no heavy recurring costs.
The registry is reduced to a **lightweight index** that references packages hosted on **Git (GitHub-first)**, while still providing:

- **version resolution** (SemVer)
- **reproducibility** (lockfile pinned to commit SHA)
- **local caching** (offline-friendly)
- **progressive security** (SHA pinning → signatures later)
- **scalability** (mirrors and P2P distribution in the future)

---

## Vision

**Vix Registry = “Index + rules”, not “hosting”.**

- Packages live in Git repositories.
- The registry itself is a Git repository.
- The `vix` CLI synchronizes the registry **on demand**.
- Installation is done by **checking out a specific commit**, not by downloading opaque tarballs.

---

## Components

### 1) Registry Index Repository (GitHub-first)

A single official repository, for example:

- `vixcpp/registry`

Contents:

- `registry.json` — global metadata (format version, policies)
- `index/` — package entries (one file per package)
- `namespaces/` (optional) — namespace rules and ownership
- `policies/` (optional) — security or validation policies

The registry is **just a Git repository**, easily mirrored or forked.
No dedicated server is required in V1.

---

### 2) Package Repository

Each package is a Git repository (or a subdirectory in a mono-repo) that contains a local manifest:

- `vix.json`

This manifest describes how the package is consumed (header-only, CMake package, Vix module, etc.).

---

### 3) Vix CLI (Client)

The CLI is responsible for:

- `vix registry sync` — update the local registry index
- `vix registry search` — search packages offline using the local index
- `vix add <pkg>` — resolve version, fetch source, lock commit, integrate
- `vix install` — install dependencies from `vix.lock`
- `vix update` — update dependencies (planned for V2)

---

## Core Workflow (V1)

### A) Registry synchronization

1. `vix registry sync` clones or pulls the `vixcpp/registry` repository
2. The index is stored in a local cache
3. All searches and resolutions are performed locally

There is **no background daemon**.
Synchronization can be manual or TTL-based.

---

### B) Adding a package

1. `vix add <name>@<range?>`
2. Version resolution:
   - locate the package entry in the local index
   - resolve the SemVer range to an exact version
   - retrieve the associated `tag` and `commit`
3. Fetch the package repository into the local store
4. Checkout the **exact commit SHA**
5. Integrate the package according to `vix.json`
6. Write or update `vix.lock` (commit pinned)

---

### C) Reproducible installation

1. `vix install` reads `vix.lock`
2. Each dependency is checked out by **commit SHA**
3. Build and integration steps are deterministic (given the same toolchain)

---

## Local Storage and Cache

### Recommended layout

- `~/.vix/registry/`
  - `index/` — cloned registry repository
  - `state.json` — last sync, TTL, metadata

- `~/.vix/store/`
  - `git/<hash>/` — cloned repositories
  - `build/<hash>/` — build artifacts (if needed)
  - `pkgs/<name>/<version>/` — installed view (optional)

Goals:
- offline installation when cached
- no unnecessary re-downloads
- isolation by version and commit

---

## Reproducibility and Lockfile

### Principle

To prevent:
- moved tags
- silently changing dependencies
- non-deterministic installs

The lockfile **must pin commit SHAs**.

### Minimal `vix.lock` content

- `name`
- `version`
- `repo`
- `commit`
- `resolvedAt` (optional)
- `integrity` (optional in V1, recommended in V2)

---

## Registry Index Format (V1)

### Package entry (concept)

One file per package in `index/`, for example:
- `index/vixcpp.rix.json`

Conceptual fields:

- `name`, `namespace`
- `repo` (Git URL)
- `description`, `license`
- `versions`:
  - `1.2.0` → `{ tag, commit }`
  - `1.2.1` → `{ tag, commit }`
- `type` (header-only | cmake | vix-module)
- `manifestPath` (usually `vix.json` at repo root)

In V1, the index can store commit SHAs directly for simplicity.
In V2, entries can be generated automatically via CI.

---

## Package Manifest (`vix.json`) — V1 concept

Purpose: describe how the package is consumed.

Conceptual fields:

- `name`
- `type`: `header-only | cmake | vix-module`
- `include` (for header-only)
- `cmake`:
  - project name
  - exported targets
  - `find_package` name
- `requires` (dependencies, planned for V2)

V1 should focus on:
- header-only packages
- simple CMake packages

---

## Security Roadmap

### V1 — Baseline
- lockfile with commit SHA
- optional source hash

### V2 — Signatures
- public keys of maintainers stored in the registry
- release signatures (minisign / sigstore)
- verification during install

### V3 — Trust policies
- namespace-level policies
- allowlists / denylists
- provenance and build attestations

---

## Availability Strategy

### V1
- primary source: GitHub
- offline support via local cache

### V2 — Mirrors
- package entries may define `mirrors[]`
- CLI tries primary, then mirrors

### V3 — P2P / Edge distribution
- fetching through the Vix network
- edge nodes caching repositories and artifacts
- aligned with Softadastra’s offline-first vision

---

## Governance and Contributions

### V1 rules

To publish a package:
1. Public Git repository
2. SemVer tags
3. `vix.json` present
4. Explicit license
5. Pull request to `vixcpp/registry` (manual or automated later)

### Validation

Registry CI may:
- validate JSON schema
- verify that commits exist
- optionally check that `vix.json` exists at the referenced commit

---

## CLI Contract (V1)

- `vix registry sync`
- `vix registry search <query>`
- `vix add <name>[@range]`
- `vix install`
- `vix lock` (optional if locking is implicit)

---

## Why this architecture fits Vix

- **No cloud infrastructure** required initially
- **Near-zero cost**
- **Deterministic and reproducible**
- **Offline-friendly**
- **Naturally scalable**
- **Fully aligned** with Vix / Softadastra philosophy: local-first, resilient, realistic

---

## V1 Decisions

1. Registry is a Git repository, not a hosted service
2. Packages are Git repositories with SemVer tags
3. Lockfile must pin commit SHAs
4. Registry synchronization is on-demand
5. Minimal integration via `vix.json` (header-only + CMake)

---
