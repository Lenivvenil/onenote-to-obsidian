# Usage

## Basic Commands

```bash
# Export all notebooks
onenote-to-obsidian

# Or run as a module
python -m onenote_to_obsidian

# List your notebooks
onenote-to-obsidian --list

# Export a specific notebook
onenote-to-obsidian --notebook "My Notebook"

# Export to a custom vault path
onenote-to-obsidian --vault /path/to/obsidian/vault

# Force re-export of all pages
onenote-to-obsidian --reset-state

# Enable debug logging
onenote-to-obsidian --verbose
```

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
