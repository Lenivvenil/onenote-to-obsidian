# OneNote → Obsidian Exporter

## What is this

Python CLI tool for exporting OneNote notebooks to Obsidian-compatible Markdown via Microsoft Graph API. Exports text, images, and file attachments preserving the notebook/section/page hierarchy.

## Project Structure

```
onenote_to_obsidian/
├── __main__.py              # CLI entry point (python -m onenote_to_obsidian)
├── config.py                # Configuration (default Microsoft Office client_id, no Azure AD needed)
├── auth.py                  # OAuth2 device code flow via MSAL, token caching, fallback client_id
├── graph_client.py          # HTTP client for Graph API (retry 429/5xx/401, pagination)
├── onenote_api.py           # OneNote endpoints: notebooks, sections, section groups, pages
├── html_converter.py        # OneNote HTML → Markdown (markdownify + BeautifulSoup)
├── resource_downloader.py   # Image/attachment downloading
├── exporter.py              # Main export orchestrator
├── state.py                 # Export state tracking (resume by lastModifiedDateTime)
├── utils.py                 # sanitize_filename, deduplicate_path
├── py.typed                 # PEP 561 typing marker
└── requirements.txt         # msal, requests, beautifulsoup4, markdownify
tests/
├── conftest.py              # Shared fixtures (mock MSAL, sample dataclasses)
├── test_auth.py             # 29 tests for auth.py
├── test_graph_client.py     # 66 tests for graph_client.py
├── test_onenote_api.py      # 46 tests for onenote_api.py
├── test_resource_downloader.py
├── test_exporter.py         # Integration tests
├── test_config.py
├── test_main.py             # CLI tests
├── test_html_converter.py
├── test_state.py
└── test_utils.py
```

## How to Run

```bash
cd ~/Projects/onenote-to-obsidian
source .venv/bin/activate

# Export all notebooks (config auto-created on first run)
python -m onenote_to_obsidian

# List notebooks
python -m onenote_to_obsidian --list

# Export specific notebook
python -m onenote_to_obsidian --notebook "Asaka"

# Full re-export
python -m onenote_to_obsidian --reset-state

# Custom client_id setup (if default doesn't work)
python -m onenote_to_obsidian --setup

# Verbose logging
python -m onenote_to_obsidian -v
```

No Azure AD app registration required. Default: public Microsoft Office client_id
(`d3590ed6-52b3-4102-aeff-aad2292ab01c`). Fallback: Microsoft Teams
(`1fec8e78-bce4-4aaf-ab1b-5451cc387264`).

## Dependencies

Virtual env: `.venv/` (Python 3.10+). From `pyproject.toml`:
- `msal` — Microsoft OAuth2
- `requests` — HTTP client
- `beautifulsoup4` — HTML parsing
- `markdownify` — HTML→Markdown conversion

Dev: `pytest`, `pytest-cov`, `pytest-mock`, `responses`, `ruff`

Install: `source .venv/bin/activate && pip install -e ".[dev]"`

## Configuration

Stored in `~/.onenote_exporter/`:
- `config.json` — client_id, vault_path, scopes
- `token_cache.json` — OAuth2 token cache (chmod 600)
- `export_state.json` — which pages have been exported

Default vault: `~/ObsidianVault`

## Architecture & Key Decisions

- **Auth**: OAuth2 device code flow, authority `https://login.microsoftonline.com/common` (personal Microsoft account). MSAL SerializableTokenCache for persistence. `force_refresh=True` on 401 retry.
- **Graph API**: Retry on 429 (Retry-After), 5xx (exponential backoff), 401 (force token refresh). Auto-pagination via `@odata.nextLink`.
- **HTML→Markdown**: Custom `markdownify.MarkdownConverter` subclass with overridden `convert_img`, `convert_object`, `convert_p`, `convert_li`, `convert_iframe`. Uses `**kwargs` for markdownify >= 1.2 compatibility.
- **Resources**: Images and attachments downloaded to `attachments/` within section folder.
- **Resume**: Export state by page_id + lastModifiedDateTime. Unchanged pages skipped.
- **Deduplication**: File dedup seeded from disk (survives crash + restart).
- **Section groups**: Recursive traversal of nested section groups.
- **YAML frontmatter**: All values quoted for safety.

## Export Output

```
Vault/
├── Notebook Name/
│   ├── Section Name/
│   │   ├── attachments/
│   │   │   ├── 0-resourceid.png
│   │   │   └── document.pdf
│   │   ├── Page Title.md
│   │   └── Another Page.md
│   └── Another Section/
│       └── ...
└── Another Notebook/
    └── ...
```

Each `.md` contains YAML frontmatter:
```yaml
---
created: "2023-01-15T10:30:00Z"
modified: "2024-06-20T14:22:00Z"
source: onenote
onenote_id: "page-guid"
---
```

## What Gets Converted from OneNote HTML

| OneNote HTML | Markdown |
|---|---|
| `<img src="graph.../resources/{id}/$value">` | `![alt](attachments/id.png)` |
| `<object data-attachment="file.pdf">` | `[file.pdf](attachments/file.pdf)` |
| `<p data-tag="to-do">` | `- [ ] text` |
| `<p data-tag="to-do:completed">` | `- [x] text` |
| `<iframe data-original-src="...">` | `[Embedded content](url)` |
| `position:absolute` CSS | Removed |
| `<b>`, `<i>`, `<h1>`-`<h6>`, `<table>`, `<a>` | Standard Markdown |

## Development Guidelines

- When adding new tag converters: override `convert_<tagname>` in `OneNoteMarkdownConverter` with signature `(self, el, text, **kwargs)`.
- Test converter via `preprocess_onenote_html()` → `convert_page_html()`.
- Graph API endpoint changes go in `onenote_api.py`, not `graph_client.py`.
- Don't edit `token_cache.json` manually — managed by MSAL.
- Run `ruff check` and `ruff format` before committing.
- All changes must pass: `pytest --cov=onenote_to_obsidian` (target: >80%).
- All UI strings must be in English.
