## QA

**Tests:** No logic files changed. `pyproject.toml` diff is a single version-string change — no test coverage applicable. All 282 pre-existing tests pass (verified during `/implement`).

**Docs:** All contracts current.

- `CLAUDE.md` already contains `--retry-resources` example and `failed_resources.json` entry (added in PR #34) — no update needed.
- `docs/runbooks/` is empty — no runbooks to check.
- `README.md` and `docs/getting-started.md` updated in this PR: CLI Options table, Configuration table, FAQ/Troubleshooting section — parity confirmed between both files.
- `docs/changelog.md` (MkDocs-served) synced to match root `CHANGELOG.md` with `[1.2.0]` section.

**Real-world canary (not automated — author gate before tagging):**
Before pushing `v1.2.0` tag, run `python -m onenote_to_obsidian` against real OneNote account and confirm `--retry-resources` appears in `--help`. See plan.md §5.
