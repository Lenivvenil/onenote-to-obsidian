# OneNote → Obsidian Exporter

Export your Microsoft OneNote notebooks to Obsidian-compatible Markdown files via Microsoft Graph API.

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
python -m onenote_to_obsidian

# List your notebooks
python -m onenote_to_obsidian --list

# Export a specific notebook
python -m onenote_to_obsidian --notebook "My Notebook"

# Export to a custom vault path
python -m onenote_to_obsidian --vault /path/to/obsidian/vault
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
created: 2023-01-15T10:30:00Z
modified: 2024-06-20T14:22:00Z
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

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=onenote_to_obsidian
```

## License

[MIT](LICENSE)
