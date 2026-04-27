# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

## [1.2.0] - 2026-04-27

### Added

- `--retry-resources` flag: retry downloading resources that failed in a previous export without re-exporting pages
- `FailedResourceState`: persisted state in `~/.onenote_exporter/failed_resources.json` tracking pages with failed resource downloads
- Export summary now lists pages with failed resources and prompts to retry
- `--reset-state` now also clears `failed_resources.json`

## [1.1.0] - 2026-04-13

### Added

- Comprehensive test suite: 255 tests, 98% coverage
- Type hints for all public methods
- GitHub Actions CI/CD (pytest on Python 3.10–3.13, ruff lint)
- `CONTRIBUTING.md` contributor guidelines
- `CHANGELOG.md`
- `py.typed` marker for PEP 561 typing support
- Persistent file deduplication (survives crash + restart)
- Force token refresh on 401 errors

### Changed

- All UI strings translated to English (was Russian)
- YAML frontmatter values now properly quoted
- Exception handling uses specific types instead of broad `except Exception`
- Code formatted with ruff

### Fixed

- Token retry on 401 now forces refresh from identity provider
- YAML frontmatter dates and IDs are quoted strings (safe for all parsers)
- Unused variables removed

## [1.0.0] - 2026-04-13

### Added

- Initial release
- OneNote to Obsidian export via Microsoft Graph API
- OAuth2 device code flow (no Azure AD registration required)
- Full notebook export: text, images, file attachments, checkboxes
- Resume support (tracks by page ID + modification time)
- Recursive section groups
- YAML frontmatter with metadata
- Configurable vault path and client ID
