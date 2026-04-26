## QA

**Tests:** All changed paths covered. 282 tests pass, 98% total coverage.

- `state.py` (new `FailedResourceState`) — 100% coverage via `TestFailedResourceState` (10 tests)
- `resource_downloader.py` (new `DownloadResult`) — 100% coverage; existing + new assertions updated
- `exporter.py` (wired `FailedResourceState`, `retry_failed_resources`) — 100% coverage via `TestFailedResources` (7 tests)
- `__main__.py` (`--retry-resources`, extended `--reset-state`) — 91% coverage; uncovered lines 125, 158–163, 167 are pre-existing gaps (`_print_section_group` with nested groups, `__main__` guard) — not introduced by this PR

**Post-review fixes (Claude + Codex):**
- Fixed bug: "Total processed" count in summary now includes `failed_resources` pages (Codex BLOCK)
- Added defensive `KeyError`/`TypeError` handling in `retry_failed_resources` for malformed state entries (Codex SUGGEST)
- `export_all` now resets `_stats` and `_failed_page_titles` at invocation start, preventing state leakage across calls (Claude SUGGEST)
- Declined: file permission hardening for `failed_resources.json` — `ExportState` has the same gap; fix should be holistic in a follow-up issue
- Declined: `.md` existence check before `mark_exported` in retry — over-engineering; plan (Risk 2) documents why the `.md` is always present

**Docs:** One contract updated (Claude-authored):

- `CLAUDE.md` "How to Run" section: added `--retry-resources` example command
- `CLAUDE.md` "Configuration" section: added `failed_resources.json` entry alongside `export_state.json`

No runbooks exist yet (`docs/runbooks/` is empty). No other doc references to CLI flags found.
