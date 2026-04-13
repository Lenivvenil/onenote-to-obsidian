# OneNote to Obsidian Exporter

Export your Microsoft OneNote notebooks to Obsidian-compatible Markdown files via Microsoft Graph API.

## Why This Tool?

- **Zero setup** — no Azure AD app registration needed, works out of the box
- **Full fidelity** — images, file attachments, checkboxes, tables, embedded content
- **Smart resume** — re-running skips unchanged pages, exports only what's new
- **Preserves structure** — Notebook / Section / Section Group hierarchy mapped to folders
- **Open source** — MIT licensed, community-driven, 98% test coverage

## Quick Install

```bash
pip install onenote-to-obsidian
```

Then run:

```bash
onenote-to-obsidian
```

On the first run, you'll see a device code prompt — open the link in your browser and sign in with your Microsoft account. That's it.

## What Gets Converted

| OneNote element | Markdown result |
|---|---|
| Images | `![alt](attachments/id.png)` |
| File attachments | `[file.pdf](attachments/file.pdf)` |
| Checkboxes (unchecked) | `- [ ] text` |
| Checkboxes (checked) | `- [x] text` |
| Embedded content (iframes) | `[Embedded content](url)` |
| Headers, bold, italic, tables, links | Standard Markdown |
| Absolute positioning CSS | Removed |

## Comparison with Alternatives

| Feature | onenote-to-obsidian | Manual copy-paste | OneNote export (OOXML) |
|---|---|---|---|
| No registration needed | Yes | N/A | N/A |
| Images & attachments | Yes | Manual | Partial |
| Resume / incremental | Yes | No | No |
| Checkboxes | Yes | No | No |
| Section groups | Yes | N/A | Yes |
| YAML frontmatter | Yes | No | No |
| Automation-friendly | Yes | No | Partial |
