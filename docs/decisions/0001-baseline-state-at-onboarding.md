# 0001. Baseline state at claude-mini onboarding

* Status: accepted
* Date: 2026-04-26
* Deciders: Ivan Kuzmin
* Tags: architecture, tooling, baseline

## Context and Problem Statement

The `onenote-to-obsidian` project existed before adoption of the claude-mini development pipeline. This ADR documents the technical decisions already in place at the moment of onboarding — choices that are load-bearing and cannot be easily reversed without significant rework. Future decisions will reference this baseline when proposing changes.

## Decision Drivers

* Need a single source of truth for "what we already decided and why" so that future ADRs don't re-litigate settled questions
* Enables new contributors (and future Claude sessions) to understand constraints without reading full git history
* Satisfies claude-mini ADR-first rule: every architectural fact must be traceable to a decision record

## Considered Options

* Python 3.10+ as the implementation language (chosen; alternatives: Go, Node.js — not seriously evaluated at project inception)
* MSAL for Microsoft OAuth2 (chosen; alternative: raw OAuth2 with `requests` — rejected due to complexity of device code flow and token cache management)
* markdownify as HTML→Markdown engine (chosen; alternatives: html2text, pandoc subprocess — rejected: html2text produces lower quality output, pandoc adds system dependency)

## Decision Outcome

Chosen option: **Accept all baseline choices as-is**, because the project is already published on PyPI with >80% test coverage and active users. Reversing any of the core decisions (language, auth library, HTML converter) would break the public API and require a major version bump with no functional benefit.

### Positive Consequences

* No migration cost; pipeline can start immediately
* Existing test suite (300+ tests, 98% coverage) remains valid
* PyPI distribution and Docker image continue to work without changes

### Negative Consequences

* `requests` (synchronous) limits throughput for large notebooks; async alternative (`httpx`) cannot be adopted without significant refactor
* `markdownify` subclassing is fragile — internal API changes require updates to `OneNoteMarkdownConverter`
* Public Microsoft client_id (`d3590ed6-...`) is outside our control; if Microsoft revokes it, users must re-auth with a custom client_id

## Accepted Baseline Decisions

### Language and Runtime
- **Python 3.10+** — required for `match` syntax readiness, type union `X | Y`, and classifier coverage in pyproject.toml

### Authentication
- **MSAL ≥ 1.28** — device code flow via `PublicClientApplication.initiate_device_flow()` + `acquire_token_by_device_flow()`
- **Authority:** `https://login.microsoftonline.com/common` (personal Microsoft accounts only)
- **Token persistence:** `SerializableTokenCache` → `~/.onenote_exporter/token_cache.json` (chmod 600)
- **401 recovery:** `force_refresh=True` on retry
- **Public client_id:** Microsoft Office `d3590ed6-52b3-4102-aeff-aad2292ab01c`; fallback Teams `1fec8e78-bce4-4aaf-ab1b-5451cc387264`

### HTTP Client
- **requests ≥ 2.31** — synchronous; retry on 429 (Retry-After header), 5xx (exponential backoff), 401 (token refresh); auto-pagination via `@odata.nextLink`

### HTML Conversion
- **markdownify ≥ 1.2.2** — custom subclass `OneNoteMarkdownConverter` overrides `convert_img`, `convert_object`, `convert_p`, `convert_li`, `convert_iframe`; uses `**kwargs` for API compatibility
- **BeautifulSoup4 ≥ 4.12** — pre-processing of OneNote HTML before markdownify pass

### Export State / Resume
- State keyed by `page_id + lastModifiedDateTime` → `~/.onenote_exporter/export_state.json`
- Unchanged pages are skipped on re-run

### Output Layout
- `Vault/<Notebook>/<Section>/attachments/<id>.<ext>` — one `attachments/` dir per section
- YAML frontmatter on every page: `created`, `modified`, `source: onenote`, `onenote_id`

### Dev Toolchain
- **pytest ≥ 9** + pytest-cov + pytest-mock + responses — test suite
- **ruff** — linter and formatter (replaces flake8 + black)
- Coverage floor: 80% (currently 98%)

### Distribution
- **PyPI** via Trusted Publisher (OIDC) — no long-lived secrets
- **Docker** multi-stage image published to GHCR

## Confirmation

This ADR is confirmed by the existence of the published PyPI package and passing CI. Re-confirmed whenever `pytest --cov=onenote_to_obsidian` reports ≥ 80% coverage.

## Re-visit Trigger

- When Microsoft revokes the public client_id: requires user-facing migration guide and new auth ADR
- When `markdownify` releases a breaking API change: revisit `OneNoteMarkdownConverter` subclassing strategy
- When notebook size exceeds ~1000 pages and export time becomes a UX problem: revisit `requests` vs async `httpx`

## Links

* Superseded by: none (baseline)
* Related: future ADRs should reference this document for stack context
