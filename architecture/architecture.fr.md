# Vix Registry — Architecture

## But

Construire **un registry sans cloud storage** : pas de VPS à maintenir pour stocker des tarballs, pas de coûts récurrents lourds.
Le registry devient un **index léger** qui référence des packages hébergés sur **Git (GitHub-first)**, tout en gardant :

- **résolution de versions** (SemVer)
- **reproductibilité** (lockfile avec commit SHA)
- **cache local** (offline-friendly)
- **sécurité progressive** (SHA pinning → signatures ensuite)
- **évolutivité** (mirrors et P2P plus tard)

---

## Vision

**Vix Registry = “Index + règles”, pas “hébergement”.**

- Les packages vivent dans des repos Git.
- Le registry vit dans un repo Git (index).
- Le CLI `vix` synchronise l’index **à la demande** (pas de “suivi temps réel” permanent).
- L’installation est basée sur **checkout d’un commit** (via tag → SHA), puis build/intégration.

---

## Composants

### 1) Registry Index Repository (GitHub-first)
Un repo officiel, exemple :

- `vixcpp/registry`

Contenu :

- `registry.json` : métadonnées globales (version du format, endpoints, etc.)
- `index/` : entrées de packages (un fichier par package)
- `namespaces/` (optionnel) : règles/validation par namespace
- `policies/` (optionnel) : policies (security baseline, conventions)

Le registry est un **repo Git** clonable/miroirable.
Aucun serveur requis en V1.

---

### 2) Package Repository (le code)
Chaque package est un repo Git (ou un sous-dossier d’un mono-repo), contenant un manifest local :

- `vix.json` (manifest côté package)

Ce fichier décrit comment le package s’intègre (header-only, CMake package, module Vix, etc.).

---

### 3) Vix CLI (client)
Le CLI gère :

- `registry sync` : met à jour l’index en cache local
- `registry search` : recherche offline dans l’index (local)
- `add <pkg>` : résout la version → fetch le repo → lock SHA → installe
- `install` : installe selon `vix.lock` (reproductible)
- `update` : met à jour les versions (optionnel V2)

---

## Flux principal (V1)

### A) Synchronisation de l’index
1. `vix registry sync` clone (ou pull) le repo `vixcpp/registry`
2. Le repo est stocké localement (cache)
3. Le CLI lit `index/` pour search et résolution

**Important** : pas de background daemon obligatoire.
Le sync peut être manuel ou basé sur un TTL.

---

### B) Ajout d’un package
1. `vix add <name>@<range?>`
2. Résolution :
   - trouve l’entrée dans l’index local
   - résout le range SemVer en version exacte
   - récupère `tag` + `commit`
3. Fetch du repo package (git clone/fetch) vers un store local
4. Checkout **du commit SHA**
5. Intégration (selon `vix.json`)
6. Écriture de `vix.lock` (SHA pinned)

---

### C) Installation reproductible
1. `vix install` lit `vix.lock`
2. Chaque dépendance est checkout par **commit SHA**
3. Build/intégration strictement déterministes (à la config près)

---

## Stockage local (cache)

### Répertoires recommandés
- `~/.vix/registry/`
  - `index/` (clone du registry)
  - `state.json` (last sync, ttl, etc.)

- `~/.vix/store/`
  - `git/<hash>/` (repos clonés, checkouts)
  - `build/<hash>/` (artefacts build si nécessaire)
  - `pkgs/<name>/<version>/` (vue installée, optionnel)

Objectif : permettre :
- offline install si déjà en cache
- pas de re-download inutile
- isolation par version/commit

---

## Reproductibilité et Lockfile

### Principe
Pour éviter :
- tags déplacés
- dépendances qui changent silencieusement
- install non déterministe

Le lockfile doit contenir **commit SHA**.

### Informations minimales dans `vix.lock`
- `name`
- `version`
- `repo`
- `commit`
- `resolvedAt` (optionnel)
- `integrity` (optionnel en V1, recommandé en V2)

---

## Format de l’index (V1)

### Entrée package (concept)
Un fichier par package dans `index/`, ex :
- `index/vixcpp.rix.json`

Contenu minimal conceptuel :
- `name`, `namespace`
- `repo` (git URL)
- `description`, `license`
- `versions` :
  - `1.2.0` → `{ tag, commit }`
  - `1.2.1` → `{ tag, commit }`
- `type` (header-only / cmake / vix-module)
- `manifestPath` (ex: `vix.json` à la racine)

**Note** : en V1, l’index peut stocker directement `commit` pour chaque version (le plus simple).
En V2, on peut automatiser la génération via GitHub Actions.

---

## Manifest package (vix.json) — concept V1
But : décrire comment consommer le package.

Champs conceptuels :
- `name`
- `type` : `header-only | cmake | vix-module`
- `include` (header-only)
- `cmake` :
  - `project` / `targets` / `find_package` name
  - `options` (toolchain flags)
- `requires` (deps, optionnel V2)

V1 peut démarrer avec :
- header-only + cmake simple.

---

## Sécurité (Roadmap)

### V1 — baseline
- lockfile avec commit SHA
- optional : hash de l’archive source (si tu veux)

### V2 — signatures
- clés publiques maintainers dans l’index
- `minisign`/`sigstore` pour signer les releases
- vérification côté `vix` avant install

### V3 — trust policy
- policies par namespace
- allowlist/denylist
- provenance (build attestation)

---

## Disponibilité (GitHub-first, mais pas GitHub-only)

### V1
- Source primaire : GitHub
- Offline : cache local

### V2 — mirrors
- l’entrée du package peut contenir `mirrors[]`
- le CLI tente : primary → mirrors

### V3 — distribution P2P / edge
- fetch via réseau Vix (store-and-forward)
- edge nodes cache les repos/artefacts
- compatible avec la vision Softadastra (offline-first, local-first)

---

## Gouvernance & Contributions

### Règles simples (V1)
Pour publier un package :
1. Repo Git public
2. Tags SemVer
3. `vix.json` présent
4. Licence explicite
5. PR vers `vixcpp/registry` pour ajouter l’entrée (ou automatisation plus tard)

### Validation
- CI sur `vixcpp/registry` :
  - JSON schema validation
  - vérification que chaque version pointe vers un commit existant
  - vérification que `vix.json` existe au commit (optionnel en V1)

---

## CLI — Contrats attendus (V1)

- `vix registry sync`
- `vix registry search <query>`
- `vix add <name>[@range]`
- `vix install`
- `vix lock` (optionnel si `add` lock déjà)

---

## Pourquoi cette architecture est la meilleure (pour Vix)

- **Zéro infra cloud** au départ
- **Coûts quasi nuls**
- **Reproductible** (commit SHA)
- **Offline-friendly** (cache local)
- **Évolutive** (mirrors, P2P)
- **Alignée** avec la philosophie Vix/Softadastra : local-first, résiliente, réaliste

---

## Décisions (V1)

1. Registry = repo Git (index), pas un service cloud
2. Packages = repos Git + tags SemVer
3. Lockfile = commit SHA pinned obligatoire
4. Sync index = à la demande (TTL optionnel)
5. Build integration minimale via `vix.json` (header-only + cmake)

---
