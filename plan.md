# Plan — release: cut v1.2.0 with retry-resources feature (Issue #38)

## 1. Problem restatement

The `--retry-resources` feature shipped in #34 and is fully merged and tested (282 tests, 98% coverage), but the published package on PyPI is still v1.1.0 — which predates this feature entirely. Users who install from PyPI cannot use `--retry-resources`. Beyond the version bump, the user-facing documentation (README CLI table, Configuration table, FAQ) and the MkDocs site (`docs/getting-started.md`) have not been updated to reflect the new flag or the new `failed_resources.json` state file. This release closes that gap: bump the version, date the changelog, and ensure all public docs accurately describe v1.2.0 behaviour.

## 2. Affected bounded contexts and files

**BC: OneNoteExport** (`docs/domain/onenote-export/`) — no changes to domain logic; export behaviour already updated in #34.

Files to change:

| File | Change |
|---|---|
| `pyproject.toml` | `version = "1.1.0"` → `"1.2.0"` (already done on branch) |
| `CHANGELOG.md` | `[Unreleased]` → `[1.2.0] - 2026-04-27` (already done on branch) |
| `docs/changelog.md` | Separate MkDocs-served duplicate of root CHANGELOG — add `[1.2.0]` section to match (currently stops at v1.1.0) |
| `README.md` | Add `--retry-resources` row to CLI Options table; add `failed_resources.json` row to Configuration table; add FAQ entry: "What if images or attachments fail to download?" |
| `docs/getting-started.md` | Same additions: CLI options table, examples block, Configuration table, Troubleshooting section |

`mkdocs.yml` nav already contains `Changelog: changelog.md` and `Getting Started: getting-started.md` — no nav changes needed.

No code changes. No test changes. No new dependencies.

## 3. Considered approaches

### A. Minimal (chosen): version bump + targeted doc updates only

Update exactly the four files listed above. Comparison table rewrite, social preview image, demo GIF, and competitor analysis are **deferred to a follow-up pre-launch polish PR** — they are promotion scope, not release scope.

**Trade-off:** Release is smaller and faster; some README sections (comparison table) still reference only manual/OOXML alternatives instead of real competitors like `onenote-md-exporter`. Acceptable because: (a) the existing table is not wrong, just incomplete; (b) conflating promotion work with the release PR adds scope risk and delays PyPI publish.

### B. Full pre-launch polish in one PR

Include social preview, competitor comparison rewrite, demo GIF, README first-fold reorder alongside the version bump.

**Trade-off:** Higher risk (more files = more review surface); delays PyPI publish; demo GIF requires screen recording infrastructure not in this repo. Rejected: "выхолощенный надёжный релиз" means minimal blast radius, not maximum content.

**Why A and not B:** B is the right thing to do — eventually. The correct sequencing is: ship v1.2.0 fast so PyPI is current, then run a dedicated `chore: pre-launch README polish` PR before any external posts.

## 4. Chosen approach and why

Approach A. No ADR required — version bump and documentation update satisfy none of the architectural significance triggers in `docs/principles.md`. The OIDC publish workflow (`publish.yml`) already exists and triggers on tag push; no workflow changes needed.

ADR 0001 (`docs/decisions/0001-baseline-state-at-onboarding.md`) governs the tech stack — this plan adds nothing to the stack.

## 5. Test strategy

No new tests required. The feature being released is already covered by the 282-test suite from #34.

**Real-world canary (mandatory before tagging — author owns this):**

The `--retry-resources` feature has only mock-based unit coverage. Before pushing `v1.2.0` tag, the author must run:

1. `python -m onenote_to_obsidian` against real OneNote account — verify normal export still works after the v1.2.0 changes.
2. Confirm `--retry-resources` flag appears in `--help` output.
3. If any resource ever failed in a prior export, run `--retry-resources` and verify behaviour.

This is the acceptance gate for "стабильный надёжный релиз" — mocks pass, but the real client never ran v1.2.0.

**Post-publish verification (manual):**

- `pip install onenote-to-obsidian==1.2.0` in a clean venv
- `onenote-to-obsidian --help` shows `--retry-resources`
- PyPI page shows `1.2.0` as latest

**CI gates:** existing `test.yml` (282 tests) and `lint.yml` (ruff) run on PR; `publish.yml` triggers on `v1.2.0` tag.

## 6. Risks and unknowns

**Risk 1 — Pre-existing partial changes on branch:** `pyproject.toml` and `CHANGELOG.md` were edited before this plan was written (pipeline deviation caught and corrected). During `/implement` step 1, run `git diff main -- pyproject.toml CHANGELOG.md` to verify the pre-pipeline edits match plan exactly and no unintended edits crept in.

**Risk 2 — PyPI OIDC trusted publisher misconfiguration:** If the `publish.yml` workflow has a scope or environment mismatch, the tag push will fail silently on PyPI. Mitigation: verify on PyPI that the Trusted Publisher is configured for `Lenivvenil/onenote-to-obsidian` before tagging. If it fails, fallback is manual `twine upload`.

**Risk 3 — MkDocs deploy on main merge, not tag:** The `docs.yml` workflow deploys the site when changes land on `main`. If the PR merges before the tag, the live site will reflect v1.2.0 docs while PyPI still shows v1.1.0 briefly. Acceptable window — typically minutes between merge and tag push.

**Risk 4 — Docs drift between README and getting-started.md:** Both files have a CLI Options table and a Configuration table. Changes must be applied to both identically; single-file updates create user confusion when readers compare PyPI README to the site. Verify parity after edits. *(Post-implement: parity confirmed — same substance, context-appropriate wording in each section.)*

**Known pre-existing: MkDocs strict-mode warning** — `docs/decisions/adr-template.md` contains a placeholder link `NNNN-*.md` that fails `mkdocs build --strict`. Pre-exists on main before this PR. Out of scope here; track as separate issue if strict-mode CI is ever added.

---

*Closes #38*
