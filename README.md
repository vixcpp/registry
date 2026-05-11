# Vix Registry

The Vix Registry is the official package registry for Vix packages.

It stores package metadata in simple JSON files and allows the Vix CLI to resolve, install, update, publish, and inspect dependencies.

## Purpose

The registry exists to provide a trusted package index for Vix projects.

It is used by commands such as:

```bash
vix add
vix install
vix update
vix outdated
vix publish
vix registry sync
```

The registry does not store package source code directly.

Each package entry points to its Git repository and declares the available tagged versions.

## Repository structure

```
registry/
├── architecture/
├── index/
│   ├── namespace.package.json
│   └── ...
├── schema/
│   ├── package-entry.schema.json
│   └── registry.schema.json
├── .github/
│   ├── scripts/
│   │   ├── index_from_tags.py
│   │   └── validate_registry_pr.py
│   └── workflows/
│       ├── registry_auto_merge.yml
│       ├── registry_index_from_tags.yml
│       └── deploy_registry_web.yml
├── registry.json
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

## Main files

| Path | Purpose |
|---|---|
| `registry.json` | Global registry metadata |
| `index/*.json` | One package entry per package |
| `schema/package-entry.schema.json` | JSON schema for package entries |
| `schema/registry.schema.json` | JSON schema for the registry metadata |
| `.github/scripts/validate_registry_pr.py` | Validates package PRs |
| `.github/scripts/index_from_tags.py` | Updates package versions from Git tags |
| `.github/workflows/registry_auto_merge.yml` | Validates and auto-merges valid registry PRs |
| `.github/workflows/registry_index_from_tags.yml` | Periodically refreshes versions from tags |
| `.github/workflows/deploy_registry_web.yml` | Triggers the registry website deployment after registry changes |

## Package entry format

Each package has one JSON file inside `index/`.

The filename should follow this format:

```
namespace.package.json
```

Example:

```
cnerium.app.json
```

A package entry looks like this:

```json
{
  "namespace": "cnerium",
  "name": "app",
  "displayName": "app",
  "description": "the fast, minimalist web framework for Vix.",
  "type": "header-only",
  "license": "MIT",
  "homepage": "https://github.com/cnerium/app",
  "documentation": "https://github.com/cnerium/app#readme",
  "repo": {
    "url": "https://github.com/cnerium/app",
    "defaultBranch": "main"
  },
  "manifestPath": "vix.json",
  "keywords": [
    "cpp",
    "framework",
    "http",
    "web",
    "runtime",
    "router",
    "middleware",
    "cnerium",
    "vix"
  ],
  "maintainers": [
    {
      "name": "Gaspard Kirira",
      "github": "cnerium"
    }
  ],
  "constraints": {
    "minCppStandard": "c++17",
    "platforms": [
      "linux",
      "macos",
      "windows"
    ]
  },
  "dependencies": {
    "registry": [],
    "git": [],
    "system": []
  },
  "exports": {
    "headers": [],
    "modules": [],
    "namespaces": []
  },
  "quality": {
    "hasDocs": true,
    "hasExamples": true,
    "hasTests": true,
    "ci": []
  },
  "api": {
    "format": "vix-api-1",
    "generatedBy": "vix-cli",
    "path": "vix.api.json",
    "updatedAt": "2026-04-01T08:24:26Z"
  },
  "versions": {
    "0.5.0": {
      "tag": "v0.5.0",
      "commit": "9d515e6dff4b23f47cac9de7642c8fadb35380f5"
    }
  }
}
```

## Required fields

A package entry must include:

| Field | Description |
|---|---|
| `namespace` | Package namespace, for example `cnerium` |
| `name` | Package name, for example `app` |
| `description` | Short package description |
| `repo.url` | HTTPS GitHub repository URL |
| `versions` | Published versions mapped to Git tags and commits |

## Version format

Versions use SemVer without the leading `v`.

Correct:

```json
"0.5.0": {
  "tag": "v0.5.0",
  "commit": "9d515e6dff4b23f47cac9de7642c8fadb35380f5"
}
```

The version key is:

```
0.5.0
```

The Git tag is:

```
v0.5.0
```

## Tag requirements

Each version must point to a real Git tag in the package repository.

For a version like:

```json
"0.5.0": {
  "tag": "v0.5.0",
  "commit": "9d515e6dff4b23f47cac9de7642c8fadb35380f5"
}
```

The tag must exist remotely:

```bash
git ls-remote https://github.com/cnerium/app refs/tags/v0.5.0
```

The tag must also resolve to the declared commit.

## Adding a new package manually

Create a new file under `index/`.

Example:

```bash
nano index/cnerium.app.json
```

Add the package metadata.

Then validate locally:

```bash
git status
git diff
```

Commit and push:

```bash
git add index/cnerium.app.json
git commit -m "registry: add cnerium/app"
git push origin main
```

## Publishing with the Vix CLI

The recommended workflow is to publish from the package repository using `vix publish`.

Inside your package repository:

```bash
git status
vix fmt --check
vix check --tests
vix build --preset release

git tag -a v0.5.0 -m "Release v0.5.0"
git push origin v0.5.0

vix publish 0.5.0 --dry-run
vix publish 0.5.0 --notes "Release v0.5.0"
```

`vix publish` prepares a registry update for the package version.

The command expects the version without the `v` prefix:

```bash
vix publish 0.5.0
```

The Git tag keeps the `v` prefix:

```
v0.5.0
```

## Updating versions from tags

The registry includes an automated workflow that scans package repositories and updates the `versions` object from Git tags.

The script is:

```
.github/scripts/index_from_tags.py
```

It accepts tags like:

```
v1.2.3
v1.2.3-rc.1
v1.2.3+build.5
```

It writes versions like:

```json
"1.2.3": {
  "tag": "v1.2.3",
  "commit": "..."
}
```

The workflow is:

```
.github/workflows/registry_index_from_tags.yml
```

It can run manually or on schedule.

## Registry validation

Pull requests that modify `index/**/*.json` are validated automatically.

Validation checks include:

| Check | Purpose |
|---|---|
| Only `index/**/*.json` changes are allowed | Keeps registry PRs auditable |
| JSON must be valid | Prevents broken metadata |
| Namespace must be valid | Ensures stable package IDs |
| Package name must be valid | Ensures stable package IDs |
| `repo.url` must be HTTPS GitHub URL | Keeps resolution predictable |
| Versions must use SemVer | Ensures resolver compatibility |
| Tags must exist remotely | Prevents broken package versions |
| Tags must point to the declared commit | Ensures reproducibility |

## Registry website deployment

The registry website lives in a separate repository:

```
https://github.com/vixcpp/registry-web
```

When `registry.json` or `index/**/*.json` changes on `main`, the registry triggers a Vercel deployment hook.

The website build fetches the latest registry data, generates the public registry index, and builds the frontend.

Final flow:

```
Package added or updated
        ↓
Registry PR validated
        ↓
Registry changes merged into main
        ↓
Registry web deploy hook triggered
        ↓
registry-web rebuilds on Vercel
        ↓
Latest package appears on the website
```

## Using a package

After a package is published, users can add it to a Vix project:

```bash
vix registry sync
vix add cnerium/app
vix install
vix build
```

Add a specific version:

```bash
vix add cnerium/app@0.5.0
```

Add a compatible range:

```bash
vix add cnerium/app@^0.5.0
```

## Local registry sync

The Vix CLI uses a local registry index.

Refresh it with:

```bash
vix registry sync
```

Use this before:

- `vix add`
- `vix update`
- `vix outdated`
- `vix publish`

Show the local registry path:

```bash
vix registry path
```

## Dependency workflow

Add a dependency:

```bash
vix add cnerium/app
```

Install locked dependencies:

```bash
vix install
```

Check outdated dependencies:

```bash
vix outdated
```

Update dependencies:

```bash
vix update --install
```

Remove a dependency:

```bash
vix remove cnerium/app
```

List project dependencies:

```bash
vix list
```

## Package quality metadata

The `quality` field describes the current state of the package.

Example:

```json
"quality": {
  "hasDocs": true,
  "hasExamples": true,
  "hasTests": true,
  "ci": []
}
```

| Field | Meaning |
|---|---|
| `hasDocs` | The package has documentation |
| `hasExamples` | The package has examples |
| `hasTests` | The package has tests |
| `ci` | List of CI providers or CI status metadata |

## Dependency metadata

The `dependencies` field describes package requirements.

Example:

```json
"dependencies": {
  "registry": [],
  "git": [],
  "system": []
}
```

| Field | Meaning |
|---|---|
| `registry` | Dependencies from the Vix registry |
| `git` | Direct Git dependencies |
| `system` | System-level dependencies |

## API metadata

The `api` field describes generated package API metadata.

Example:

```json
"api": {
  "format": "vix-api-1",
  "generatedBy": "vix-cli",
  "path": "vix.api.json",
  "updatedAt": "2026-04-01T08:24:26Z"
}
```

This allows registry tools and websites to display package API information later.

## Best practices for package maintainers

Before publishing a package:

```bash
vix fmt --check
vix check --tests
vix build --preset release
```

Then tag and publish:

```bash
git tag -a v0.5.0 -m "Release v0.5.0"
git push origin v0.5.0

vix publish 0.5.0 --dry-run
vix publish 0.5.0 --notes "Release v0.5.0"
```

After publishing:

```bash
vix registry sync
vix add namespace/name
vix build
```

## Best practices for registry entries

Use:

```
namespace/name
```

Example:

```
cnerium/app
gaspardkirira/result
gaspardkirira/http_client
```

Use lowercase names. Avoid spaces, uppercase names, and unstable repository URLs.

## Common mistakes

### Using the tag as the version key

Wrong:

```json
"v0.5.0": {
  "tag": "v0.5.0",
  "commit": "..."
}
```

Correct:

```json
"0.5.0": {
  "tag": "v0.5.0",
  "commit": "..."
}
```

### Publishing before pushing the tag

Wrong:

```bash
git tag -a v0.5.0 -m "Release v0.5.0"
vix publish 0.5.0
```

Correct:

```bash
git tag -a v0.5.0 -m "Release v0.5.0"
git push origin v0.5.0
vix publish 0.5.0
```

### Forgetting to sync locally

If a package is not found:

```bash
vix registry sync
vix add namespace/name
```

### Declaring a tag with the wrong commit

The registry validator checks that the tag points to the declared commit.

Fix the commit field or fix the tag before submitting.

## Related repositories

| Repository | Purpose |
|---|---|
| `vixcpp/vix` | Vix CLI and runtime |
| `vixcpp/registry` | Package registry metadata |
| `vixcpp/registry-web` | Registry web interface |
| `vixcpp/docs` | Vix documentation |

## License

This registry is released under the license declared in LICENSE.
