# Changelog

All notable changes to **vix-registry** will be documented in this file.

This project follows **Semantic Versioning** (`MAJOR.MINOR.PATCH`)
and adheres to the principles of **Keep a Changelog**.

---

## [Unreleased]

### Added

- Initial project structure (CMake, presets, folders)
- Core application skeleton (`App`)
- HTTP server based on Vix (`HttpServer`)
- Database layer using Vix ORM (MySQL)
- Environment-based database configuration
- Health endpoints:
  - `/health`
  - `/health/db`
- Domain models:
  - Package
  - Version
  - User
  - Token
- Database migrations (initial schema)
- Unit test skeleton (database connection test)
- Config files and examples

### Changed

- N/A

### Fixed

- N/A

### Removed

- N/A

---

## [0.1.0] — 2025-12-18

### Added

- First public bootstrap of **vix-registry**
- Full build system using CMake + Vix
- Modular architecture (http, db, domain, services)
- Initial documentation and README

---

## Versioning policy

- **MAJOR** — breaking API or protocol changes
- **MINOR** — backward-compatible features
- **PATCH** — backward-compatible bug fixes

---

## Notes

This project is in **early development**.
APIs, database schema, and internal architecture may evolve rapidly
until version `1.0.0`.
