# Plan — chore: pre-launch README polish (Issue #43)

## 1. Problem restatement

The README's "Comparison with Alternatives" table currently benchmarks only against manual copy-paste and the official OOXML export — neither of which is a real software alternative. Anyone evaluating this tool will search for and find `onenote-md-exporter` and `ConvertOneNote2MarkDown` before landing here; if the README doesn't address them, the tool looks like its author doesn't know the space. Additionally, a cross-platform FAQ entry is missing, which is a frequent first question for Windows-native migrants who assume OneNote tooling requires Windows. The "Why This Tool?" section already has "Zero setup" first — confirmed by reading the current file — so that acceptance criterion is already met and requires no change.

## 2. Affected bounded contexts and files

**BC: OneNoteExport** — no domain logic changes. Documentation only.

| File | Change |
|---|---|
| `README.md` | Replace comparison table columns; add cross-platform FAQ entry |

No other files. `docs/getting-started.md` does not have a comparison table, so no parity work needed there.

## 3. Considered approaches

### A. Rewrite comparison table with real competitors (chosen)

Replace the two placeholder columns (`Manual copy-paste`, `OneNote export (OOXML)`) with `onenote-md-exporter` and `ConvertOneNote2MarkDown`. Keep the same row structure. Add a **Platform** row to surface the cross-platform advantage directly in the table.

**Competitor data (verified from primary sources 2026-04-27):**

`onenote-md-exporter` (github.com/alxnbl/onenote-md-exporter):
- Language: .Net 10 console app
- Platform: **Windows ≥10 only** — OneNote + Word COM Interop APIs
- Requires: OneNote ≥2013 + Word ≥2013 installed locally
- Images/attachments: Yes
- Resume/incremental: No (not documented)
- Section groups: Yes ("exported as a folder hierarchy")
- YAML frontmatter: Yes (optional — title, created, updated)
- PyPI/Homebrew: No (GitHub releases only)

`ConvertOneNote2MarkDown` (github.com/theohbrothers/ConvertOneNote2MarkDown):
- Language: PowerShell 5.x / 7.x
- Platform: **Windows ≥10 only** — OneNote Object Model (COM)
- Requires: OneNote ≥2016 Desktop (not Store version), must be open during export
- Images/attachments: Yes
- Resume/incremental: Partial (reuse existing .docx intermediates; not true page-level skip)
- Section groups: Yes (nested groups supported)
- YAML frontmatter: No
- PyPI/Homebrew: No (GitHub releases only)

**Key differentiators confirmed:**
1. Cross-platform (macOS/Linux/Windows) — only this tool
2. No local OneNote installation — Graph API vs COM
3. pip/Homebrew — only this tool
4. True page-level resume — only this tool
5. "No Azure AD" row **dropped** — both competitors also don't need it (they use local COM); including it would mislead

**Trade-off:** Verified data replaces unverifiable placeholder columns. onenote-md-exporter does have optional YAML frontmatter — table must reflect this accurately (not claim we're unique there).

### B. Add competitors as a separate "Alternatives" section, keep existing table

Keep the current table for non-software alternatives and add a separate table for software alternatives below it.

**Trade-off:** Two tables creates redundancy and cognitive overhead. The current table is already titled "Comparison with Alternatives" — it should cover all alternatives. Rejected.

## 4. Chosen approach and why

Approach A. Single table replacement is the minimal change that maximises information density. No ADR required — this is a documentation edit with no architectural significance. ADR 0001 governs the tech stack; this plan changes nothing in it.

**"Zero setup" position check:** Current README line 16 already has `**Zero setup**` as the first bullet in `## Why This Tool?`. AC criterion 2 is already satisfied. No change needed for that section.

## 5. Test strategy

No code changes. No automated tests required or applicable.

**Manual verification after edit:**
- Table renders correctly in GitHub markdown preview
- All feature rows have accurate Yes/No/Partial values
- Cross-platform FAQ entry is present and answers the question directly
- `--help` output unchanged (no CLI changes)

## 6. Risks and unknowns

**Risk 1 — Competitor feature accuracy:** Feature data for `onenote-md-exporter` and `ConvertOneNote2MarkDown` is based on publicly observable behaviour and README documentation at time of writing. Specific edge cases (partial image support, specific OS versions) may differ. Mitigation: use conservative "Yes/No" values only for clearly documented features; use "Partial" only where the caveat is explicit in the competitor's own docs.

**Risk 2 — Tone perception:** Comparison tables can read as attack marketing if worded poorly. Mitigation: use neutral Yes/No/Partial values only — no adjectives, no editorialising. Let the data speak.

**Risk 3 — "Zero setup" AC already satisfied:** If the reviewer reads the AC literally and marks it blocked because "no change was made," they may miss that the current state already satisfies it. Plan explicitly documents this pre-condition.

---

*Closes #43*
