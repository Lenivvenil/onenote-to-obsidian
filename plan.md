# Plan: feat/retry-failed-resources (Issue #33)

## Problem restatement

When `ResourceDownloader` fails to fetch a resource (image or file attachment), it currently logs a warning, maps the URL to the expected filename anyway, and the page proceeds to export successfully — including being marked as done in `ExportState`. The result: the vault contains `.md` files with broken `![alt](attachments/id.png)` links that will never be fixed on re-run, because `ExportState` considers those pages already complete. The only escape is `--reset-state`, which re-exports everything. The fix must introduce a separate retry path that tracks only what failed and retries only that — without touching unchanged pages.

## Affected bounded contexts and files

**BC: OneNoteExport** (single BC, see `docs/domain/onenote-export/overview.md`)

| File | Change |
|---|---|
| `onenote_to_obsidian/state.py` | Add `FailedResourceState` class |
| `onenote_to_obsidian/resource_downloader.py` | Change return type to expose failed URLs |
| `onenote_to_obsidian/exporter.py` | Wire `FailedResourceState`; skip `mark_exported` on partial failure; add `retry_failed_resources()`; update summary |
| `onenote_to_obsidian/__main__.py` | Add `--retry-resources` flag; extend `--reset-state` |
| `tests/test_state.py` | Add `TestFailedResourceState` |
| `tests/test_resource_downloader.py` | Update assertions for new return type |
| `tests/test_exporter.py` | Add partial-failure and retry tests |

## Considered approaches

### A — Separate `FailedResourceState` class + separate `failed_resources.json`

New class in `state.py` mirroring `ExportState` in structure. File lives alongside `export_state.json` in `~/.onenote_exporter/`. Schema:

```json
{
  "failed_resources": {
    "<page_id>": {
      "title": "Page Title",
      "last_modified": "2024-06-20T14:22:00Z",
      "attachments_dir": "Notebook/Section/attachments",
      "resources": [
        {"url": "https://graph.microsoft.com/.../resources/0-abc/$value",
         "filename": "0-abc.png",
         "media_type": "image/png"}
      ]
    }
  }
}
```

`attachments_dir` is stored as a path relative to vault root. Retry reconstructs the full path as `vault_path / attachments_dir`. Storing `filename` and `media_type` per resource is required — retry calls `download_resources({url: (filename, media_type)}, attachments_dir)` and must pass the same arguments the original export used.

`ResourceDownloader.download_resources()` returns a `DownloadResult(resource_map, failed_urls)`. Exporter checks failed_urls: if non-empty, records in `FailedResourceState`, skips `ExportState.mark_exported()`. `--retry-resources` loads `FailedResourceState`, re-runs `download_resources` for each failed URL, on full-page success calls `ExportState.mark_exported()` and clears the page from `FailedResourceState`.

**Trade-offs:**
- Good: clean separation of concerns; matches existing `ExportState` pattern; each file has one job
- Good: `--retry-resources` can be implemented without touching normal export path
- Bad: two files to manage; `--reset-state` must clear both (simple, but easy to forget)
- Bad: `section_dir` must be stored in the state for retry to know where to write — coupling state to filesystem layout

### B — Merge failed resources into existing `export_state.json`

Add a `"failed_resources"` top-level key to the existing file. Single file, `ExportState` handles both concerns.

**Trade-offs:**
- Good: one file, simpler mental model
- Good: `clear()` automatically covers both
- Bad: violates single responsibility; `ExportState`'s contract is "what's done" — mixing "what failed" muddies it
- Bad: changes `ExportState` public API in a way that breaks existing tests and callers
- Bad: retry path reads the same class that the normal export path writes — harder to reason about invariants

### C — In-memory tracking only, no persistence

Report failures at end of run; do not persist. User re-runs full export or `--reset-state`.

**Trade-offs:**
- Good: zero new state files, zero schema decisions
- Bad: directly violates the AC and the domain model decision ("FailedResourceState" is explicitly a persisted aggregate)
- Bad: large notebooks with intermittent Graph API failures would require full re-export every time

**Chosen: Approach A.** Approach B violates the single-responsibility of `ExportState` and makes invariants harder to reason about. Approach C was ruled out by the operator decision in the domain model. Approach A mirrors the established `ExportState` pattern exactly — anyone who understands `ExportState` will immediately understand `FailedResourceState`.

## Implementation detail: DownloadResult

`ResourceDownloader.download_resources()` currently returns `dict[str, str]`. Changing to a named return is less disruptive than a dataclass if we use a `NamedTuple` or return `(resource_map, failed_urls)` as a tuple. Prefer a simple dataclass in `resource_downloader.py` to keep the type explicit:

```python
@dataclass
class DownloadResult:
    resource_map: dict[str, str]         # url -> local_filename
    failed_resources: list[dict]         # [{url, filename, media_type}] for each failure
```

**Note (post-plan correction):** The initial design used `failed_urls: list[str]` and had `_export_page` look up `(filename, media_type)` in `resource_urls`. This broke when `download_resources` was mocked in tests — the mock bypasses `preprocess_onenote_html`, so `resource_urls` is empty and the lookup raises `KeyError`. Storing full records in `DownloadResult` eliminates the lookup and is cleaner: the downloader already knows `filename` and `media_type` when it records a failure.

This is a breaking change to `ResourceDownloader.download_resources()` — all callers in `exporter.py` must be updated. Only one call site in `_export_page`.

## Test strategy

**Unit — `tests/test_state.py` (new `TestFailedResourceState`):**
- `mark_failed` persists to disk; `load` reads it back correctly
- `clear_page` removes a single page; remaining pages intact
- `clear` removes all entries and deletes the file
- `count` returns correct value
- Corrupted JSON handled gracefully (same pattern as `ExportState._load`)

**Unit — `tests/test_resource_downloader.py`:**
- Existing tests: update assertions from `dict` to `DownloadResult`
- New: partial failure → `failed_urls` non-empty, `resource_map` still contains successful entries
- New: all-success → `failed_urls` empty

**Unit — `tests/test_exporter.py`:**
- Page with partial resource failure: `_state.mark_exported` NOT called; `_failed_state.mark_failed` called; `stats["failed_resources"]` incremented
- Page with all resources succeeded: `_state.mark_exported` called; `_failed_state` not touched
- `export_all` summary: `failed_resources` count printed when > 0; page titles listed
- `retry_failed_resources`: loads `FailedResourceState`; calls `download_resources` for each failed URL only; on full-page success: `ExportState.mark_exported` called, `FailedResourceState.clear_page` called

**Integration — `tests/test_exporter.py`:**
- Export with one page having one failing resource (`responses` mock raises `ConnectionError` for that URL) → verify `failed_resources.json` written, `export_state.json` does NOT contain page_id
- Run retry → mock URL now succeeds → verify `export_state.json` contains page_id, `failed_resources.json` no longer contains page

## Risks and unknowns

1. **`section_dir` coupling in state**: retry needs to know where to write the downloaded file. Storing the absolute `section_dir` path means `failed_resources.json` breaks if the vault is moved between export and retry. Alternative: store relative path from vault root. Chosen: store relative path from vault root to avoid absolute-path fragility.

2. **Why retry does NOT need to rewrite `.md` files**: `_export_page` order is (1) fetch HTML, (2) preprocess, (3) `download_resources`, (4) convert HTML→Markdown, (5) write `.md`. Even on resource failure, `download_resources` maps the URL to the expected local filename (e.g. `0-abc123.png`) — not to the Graph API URL. So the written `.md` already references `attachments/0-abc123.png`. Retry simply writes the binary to that path. The Markdown reference is valid from the moment the page is first exported; it just points to a file that doesn't exist yet until retry succeeds. This is an elegant property of the current design, not a risk.

3. **`--reset-state` atomicity**: `ExportState.clear()` and `FailedResourceState.clear()` are two separate file operations. A crash between them leaves inconsistent state. Risk is low (migration tool, not long-running service), accepted without mitigation.

4. **`DownloadResult` is a breaking change**: all test mocks for `download_resources` must be updated. Risk of missed mock → test passes but runtime fails. Mitigated by type-checking (`mypy` or ruff UP rules would catch `dict` vs `DownloadResult` misuse).

5. **Stale entries in FailedResourceState**: a page is in `FailedResourceState` (some resources failed). User edits the page in OneNote — version changes. Normal re-export runs: `ExportState.is_exported()` returns False (version changed), so the page is fully re-exported with fresh HTML and a potentially different resource set. The old failed URLs in `FailedResourceState` are now stale. Fix: in `_export_section`, before exporting a page that is NOT in `ExportState`, call `_failed_state.clear_page(page.id)` first. This ensures re-export starts clean.

6. **`--retry-resources` with empty state**: if `FailedResourceState` is empty (nothing to retry), print `"No failed resources recorded. Nothing to retry."` and exit 0. Do not attempt Graph API calls.

7. **`--retry-resources` + `--notebook` filter interaction**: `--retry-resources` retries ALL entries in `FailedResourceState` regardless of `--notebook` filter. Rationale: `FailedResourceState` stores `page_id` and `section_dir` but not notebook name; filtering would require extra state. Accepted: retry is a recovery action, not a scoped export.

---

## ADR check (principles.md criteria)

Trigger initially flagged: "Меняется модель данных." On review with advisor: **No ADR needed.**

Rationale: the ADR trigger targets decisions like picking SQLite over Postgres, changing inter-service wire formats, or introducing event sourcing — choices that can't be recovered from easily. Here, `FailedResourceState` is a second JSON file using the identical `json.dumps`/`json.loads` pattern as `ExportState`. The conceptual decision (FailedResourceState aggregate, retry contract, separate file) is already captured in `docs/domain/onenote-export/overview.md` (operator-reviewed, domain-reviewer-approved). This plan's "Considered approaches" section covers the trade-offs. An ADR would duplicate both documents without adding information.

> Plan written. Next steps:
>
> 1. ~~Call advisor()~~ — done; plan updated with findings.
> 2. Run `/implement` — plan is sound.
