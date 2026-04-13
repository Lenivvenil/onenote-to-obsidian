# Getting Started

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

## First Run

```bash
onenote-to-obsidian
```

On the first run, you'll see a device code prompt:

```
===========================================================
  To authorize:
  1. Open: https://microsoft.com/devicelogin
  2. Enter code: XXXXXXXXX
===========================================================
```

Open the link in your browser, enter the code, and sign in with your Microsoft account. Configuration is created automatically.

## Authentication

The tool uses OAuth2 device code flow. No app registration is needed — it ships with the public Microsoft Office client ID.

**Token storage:** OAuth tokens are cached in `~/.onenote_exporter/token_cache.json` (permissions: owner-only, `chmod 600`). Re-authentication is only needed when refresh tokens expire.

**Custom client ID:** If the default client ID doesn't work for your account type, run `--setup` and provide your own (see [Azure AD app registration guide](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app)).
