# OneNote → Obsidian Exporter

[![Tests](https://github.com/Lenivvenil/onenote-to-obsidian/actions/workflows/test.yml/badge.svg)](https://github.com/Lenivvenil/onenote-to-obsidian/actions/workflows/test.yml)
[![Lint](https://github.com/Lenivvenil/onenote-to-obsidian/actions/workflows/lint.yml/badge.svg)](https://github.com/Lenivvenil/onenote-to-obsidian/actions/workflows/lint.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyPI Version](https://img.shields.io/pypi/v/onenote-to-obsidian.svg)](https://pypi.org/project/onenote-to-obsidian/)
[![Downloads](https://img.shields.io/pypi/dm/onenote-to-obsidian.svg)](https://pypi.org/project/onenote-to-obsidian/)
[![GitHub Release](https://img.shields.io/github/v/release/Lenivvenil/onenote-to-obsidian)](https://github.com/Lenivvenil/onenote-to-obsidian/releases)

Export your Microsoft OneNote notebooks to Obsidian-compatible Markdown files via Microsoft Graph API.

## Why This Tool?

- **Zero setup** — no Azure AD app registration needed, works out of the box
- **Full fidelity** — images, file attachments, checkboxes, tables, embedded content
- **Smart resume** — re-running skips unchanged pages, exports only what's new
- **Preserves structure** — Notebook / Section / Section Group hierarchy mapped to folders
- **Open source** — MIT licensed, community-driven, 98% test coverage

## Features

- **No Azure AD registration required** — uses a public Microsoft client ID out of the box
- **Full notebook export** — text, images, file attachments, checkboxes, embedded content
- **Preserves structure** — Notebook / Section / Page hierarchy mapped to folders
- **Resume support** — re-running skips unchanged pages (tracks by modification time)
- **Recursive section groups** — nested section groups are fully supported
- **YAML frontmatter** — each page includes `created`, `modified`, `source`, `onenote_id`

## Requirements

- Python 3.10+
- A personal Microsoft account with OneNote data

## Installation

### From PyPI (recommended)

```bash
pip install onenote-to-obsidian
```

### From source

```bash
git clone https://github.com/Lenivvenil/onenote-to-obsidian.git
cd onenote-to-obsidian
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

## Quick Start

```bash
# Export all notebooks (first run creates config automatically)
onenote-to-obsidian

# Or run as a module
python -m onenote_to_obsidian

# List your notebooks
onenote-to-obsidian --list

# Export a specific notebook
onenote-to-obsidian --notebook "My Notebook"

# Export to a custom vault path
onenote-to-obsidian --vault /path/to/obsidian/vault
```

On the first run, you'll see a device code prompt:

```
===========================================================
  To authorize:
  1. Open: https://microsoft.com/devicelogin
  2. Enter code: XXXXXXXXX
===========================================================
```

Open the link in your browser, enter the code, and sign in with your Microsoft account.

## CLI Options

| Option | Description |
|---|---|
| `--vault PATH` | Path to Obsidian vault (default: `~/ObsidianVault`) |
| `--notebook NAME` | Export only the specified notebook |
| `--list` | List available notebooks and exit |
| `--reset-state` | Force re-export of all pages |
| `--setup` | Configure a custom client ID |
| `-v, --verbose` | Enable debug logging |

## Output Structure

```
vault/
├── Notebook Name/
│   ├── Section Name/
│   │   ├── attachments/
│   │   │   ├── 0-resourceid.png
│   │   │   └── document.pdf
│   │   ├── Page Title.md
│   │   └── Another Page.md
│   └── Section Group/
│       └── Nested Section/
│           └── ...
└── Another Notebook/
    └── ...
```

Each `.md` file includes YAML frontmatter:

```yaml
---
created: "2023-01-15T10:30:00Z"
modified: "2024-06-20T14:22:00Z"
source: onenote
onenote_id: "page-guid"
---
```

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

## Authentication

The tool uses OAuth2 device code flow. No app registration is needed — it ships with the public Microsoft Office client ID.

**Token storage:** OAuth tokens are cached in `~/.onenote_exporter/token_cache.json` (permissions: owner-only, `chmod 600`). Re-authentication is only needed when refresh tokens expire.

**Custom client ID:** If the default client ID doesn't work for your account type, run `--setup` and provide your own (see [Azure AD app registration guide](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app)).

## Configuration

All configuration is stored in `~/.onenote_exporter/`:

| File | Purpose |
|---|---|
| `config.json` | Client ID, vault path, OAuth scopes |
| `token_cache.json` | Cached OAuth2 tokens (chmod 600) |
| `export_state.json` | Which pages have been exported |

## Troubleshooting

### "Invalid client_id" error

Try the fallback client ID:

```bash
onenote-to-obsidian --setup
# Enter: 1fec8e78-bce4-4aaf-ab1b-5451cc387264
```

### Pages not exporting

1. Verify you're signed in: `onenote-to-obsidian --list`
2. Check logs: `onenote-to-obsidian --verbose`
3. Reset state: `onenote-to-obsidian --reset-state`

### "Account not supported" error

Your Microsoft account type may not be compatible with the default client ID. Run `--setup` and try the fallback, or register your own app in Azure AD.

## FAQ

### Does this work with work/school Microsoft accounts?

It works with personal Microsoft accounts out of the box. Work/school accounts may require a custom client ID — run `--setup` and register your own app in [Azure AD](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app).

### Can I re-export without re-downloading everything?

Yes. The tool tracks exported pages by ID and modification time. Re-running exports only new or changed pages. Use `--reset-state` to force a full re-export.

### What happens if the export crashes mid-way?

Progress is saved in `~/.onenote_exporter/export_state.json`. Re-running picks up where it left off. File deduplication also survives crashes.

### Is my data sent anywhere besides Microsoft?

No. The tool only communicates with Microsoft Graph API and writes to your local filesystem. OAuth tokens are cached locally with owner-only permissions.

### How do I use a different Obsidian vault location?

```bash
onenote-to-obsidian --vault /path/to/your/vault
```

The default location is `~/ObsidianVault`.

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

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=onenote_to_obsidian

# Lint and format
ruff check onenote_to_obsidian/
ruff format onenote_to_obsidian/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full contributor guidelines.

## License

[MIT](LICENSE)
