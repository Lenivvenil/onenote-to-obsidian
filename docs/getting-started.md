# Getting Started

Everything you need to export your OneNote notebooks to Obsidian. Takes about 2 minutes.

## Requirements

- **Python 3.10+** (macOS, Windows, Linux)
- A **personal Microsoft account** with OneNote data

!!! note "Work/school accounts"
    Personal accounts work out of the box. Work/school accounts may need a custom client ID — see [Custom Client ID](#custom-client-id) below.

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

### Docker

No Python required. Just Docker:

```bash
docker run -it --rm \
  -v ~/.onenote_exporter:/home/appuser/.onenote_exporter \
  -v ~/ObsidianVault:/home/appuser/ObsidianVault \
  ghcr.io/lenivvenil/onenote-to-obsidian
```

The `-it` flags are needed for the interactive OAuth login on first run. Volumes mount your config (so tokens persist) and vault (so exports land on your disk).

Or with Docker Compose:

```bash
docker compose run onenote-exporter
docker compose run onenote-exporter --list
docker compose run onenote-exporter --notebook "Work Notes"
```

## First run

```bash
onenote-to-obsidian
```

You'll see a device code prompt:

```
===========================================================
  To authorize:
  1. Open: https://microsoft.com/devicelogin
  2. Enter code: XXXXXXXXX
===========================================================
```

Open the link, enter the code, sign in. Done — your notes start exporting.

## CLI options

| Option | What it does |
|---|---|
| `--vault PATH` | Export to a specific Obsidian vault (default: `~/ObsidianVault`) |
| `--notebook NAME` | Export only one notebook by name |
| `--list` | List your notebooks and exit |
| `--reset-state` | Force re-export of all pages |
| `--retry-resources` | Retry downloading resources that failed in a previous export |
| `--setup` | Configure a custom client ID |
| `-v, --verbose` | Show debug-level logs |

### Examples

```bash
# See what notebooks you have
onenote-to-obsidian --list

# Export just one notebook
onenote-to-obsidian --notebook "Work Notes"

# Export to a specific vault
onenote-to-obsidian --vault ~/Documents/MyVault

# Something went wrong? Get verbose logs
onenote-to-obsidian --verbose

# Start fresh — re-export everything
onenote-to-obsidian --reset-state

# Retry images/attachments that failed to download in a previous export
onenote-to-obsidian --retry-resources
```

## Output structure

Your OneNote hierarchy maps directly to folders:

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

Every `.md` file gets YAML frontmatter:

```yaml
---
created: "2023-01-15T10:30:00Z"
modified: "2024-06-20T14:22:00Z"
source: onenote
onenote_id: "page-guid"
---
```

## Configuration

All config lives in `~/.onenote_exporter/`:

| File | Purpose |
|---|---|
| `config.json` | Client ID, vault path, OAuth scopes |
| `token_cache.json` | OAuth2 tokens (chmod 600, owner-only) |
| `export_state.json` | Tracks which pages have been exported |
| `failed_resources.json` | Pages with resources that failed to download (use `--retry-resources` to retry) |

### Custom client ID

The default client ID (Microsoft Office) works for most personal accounts. If you get auth errors:

```bash
onenote-to-obsidian --setup
```

**Quick fix:** try the fallback client ID: `1fec8e78-bce4-4aaf-ab1b-5451cc387264`

**Register your own:** if neither works, create an app in [Azure AD](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app) with these permissions: `Notes.Read`, `Notes.ReadWrite`, `User.Read`.

## Smart resume

The tool remembers what it exported. Re-running only grabs new or modified pages — unchanged ones are skipped automatically. This means you can:

- Run it on a schedule (cron, Task Scheduler) without waste
- Recover from crashes — progress is saved after every page
- Update your vault incrementally as you add notes in OneNote

To force a full re-export:

```bash
onenote-to-obsidian --reset-state
```

## Troubleshooting

### "Invalid client_id" error

Try the fallback:

```bash
onenote-to-obsidian --setup
# Enter: 1fec8e78-bce4-4aaf-ab1b-5451cc387264
```

### Pages not exporting

1. Check you're signed in: `onenote-to-obsidian --list`
2. Check logs: `onenote-to-obsidian --verbose`
3. Reset state: `onenote-to-obsidian --reset-state`

### Images or attachments are missing

Some resources may have failed to download (network issue, temporary Graph API error). The export summary will list affected pages. Retry with:

```bash
onenote-to-obsidian --retry-resources
```

This re-downloads only the failed resources without re-exporting pages. If resources still fail, check your network and try again.

### "Account not supported" error

Your account type may not be compatible with the default client ID. Run `--setup` and try the fallback, or register your own app.

## Contributing

```bash
git clone https://github.com/Lenivvenil/onenote-to-obsidian.git
cd onenote-to-obsidian
pip install -e ".[dev]"
pytest                              # run tests
ruff check onenote_to_obsidian/     # lint
ruff format onenote_to_obsidian/    # format
```

All changes need tests. Target coverage: >80%. See [CONTRIBUTING.md](https://github.com/Lenivvenil/onenote-to-obsidian/blob/main/CONTRIBUTING.md) for details.
