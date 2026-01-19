# Contributing to Vix Registry

Thank you for your interest in contributing to **Vix Registry**.

Vix Registry is **not a software project**.  
It is a **specification + index repository** that defines how Vix discovers and resolves packages.

Please read this document carefully before opening an issue or pull request.

---

## What This Repository Is

- A **Git-based package index**
- A **source of truth for package metadata**
- A **stable specification** consumed by the `vix` CLI

## What This Repository Is Not

- ❌ A C++ project
- ❌ A build system
- ❌ A runtime or service
- ❌ A place to upload source code archives

No binaries are built here.  
No code is compiled here.

---

## Types of Contributions

We welcome the following contributions:

### 1. Package Entries (Most Common)

Adding or updating package metadata in the `index/` directory.

Examples:
- Adding a new package
- Adding a new version to an existing package
- Marking a version as yanked
- Fixing metadata (license, description, repo URL)

---

### 2. Specification Improvements

- Clarifying documentation
- Improving JSON schemas
- Fixing inconsistencies in `registry.json`
- Improving architecture documents

---

### 3. Validation & Governance

- Proposing validation rules
- Improving naming conventions
- Improving long-term registry stability

---

## Adding a New Package

### Requirements (V1)

To add a package to the registry, **all** of the following must be true:

1. The package is hosted in a **public Git repository**
2. The repository uses **Semantic Versioning tags** (`v1.2.3`)
3. A `vix.json` manifest exists in the repository
4. The repository declares a **clear license**
5. The package name follows naming rules (see below)

---

### Package Entry File

Each package entry is a single JSON file in:

```
index/{namespace}.{name}.json
```

Example:
```
index/vixcpp.rix.json
```

The file **must** conform to:

```
schema/package-entry.schema.json
```

Pull requests that do not validate against the schema will be rejected.

---

### Naming Rules

- `namespace`: lowercase, alphanumeric, dashes allowed
- `name`: lowercase, alphanumeric, dots, dashes, underscores allowed
- No spaces
- No uppercase letters

Good:
- `vixcpp.rix`
- `adastra.sync`

Bad:
- `MyLib`
- `vix cpp`
- `cool-lib!`

---

### Version Rules

- Versions **must** follow SemVer: `MAJOR.MINOR.PATCH`
- Each version **must** include:
  - a Git tag
  - the resolved commit SHA
- Tags must point to immutable history

Moving tags is strongly discouraged.

---

## Updating an Existing Package

You may submit a PR to:

- add a new version
- fix incorrect metadata
- mark a version as yanked

Do **not**:
- remove historical versions
- rewrite version history without strong justification

---

## Yanked Versions

A version may be marked as:

```json
"1.2.1": {
  "tag": "v1.2.1",
  "commit": "deadbeef",
  "yanked": true
}
```

Yanked versions:
- remain in the registry
- are not selected by default
- remain installable if pinned in a lockfile

---

## Validation

All pull requests are expected to:

- pass JSON schema validation
- keep formatting clean and consistent
- avoid unnecessary changes

Automated validation may be enforced via CI.

---

## What Not to Do

Please do **not**:

- add C++ source code
- add binaries or archives
- add build systems
- introduce runtime dependencies
- add network services

This repository must remain **lightweight and durable**.

---

## Philosophy

Vix Registry is designed to:

- survive long-term with minimal maintenance
- avoid infrastructure costs
- remain reproducible and deterministic
- stay aligned with Vix's local-first vision

Every contribution should reinforce these goals.

---

## Questions or Proposals

If you are unsure about a change:

- open an issue
- explain your motivation clearly
- propose minimal, forward-compatible changes

Large design changes require discussion before implementation.

---

## License

By contributing to this repository, you agree that your contributions will be licensed under the same license as this project (MIT).

---

**Thank you for helping keep Vix Registry simple, stable, and future-proof.**
