# Configuration

All configuration is stored in `~/.onenote_exporter/`:

| File | Purpose |
|---|---|
| `config.json` | Client ID, vault path, OAuth scopes |
| `token_cache.json` | Cached OAuth2 tokens (chmod 600) |
| `export_state.json` | Which pages have been exported |

## Custom Client ID

By default, the tool uses the public Microsoft Office client ID. If you need to use your own:

```bash
onenote-to-obsidian --setup
```

To register your own app:

1. Create a free Azure account at [portal.azure.com](https://portal.azure.com)
2. Microsoft Entra ID → App registrations → New registration
3. Supported account types: "Accounts in any organizational directory and personal Microsoft accounts"
4. Redirect URI: Public client → `https://login.microsoftonline.com/common/oauth2/nativeclient`
5. Authentication → Allow public client flows = Yes
6. API permissions → Microsoft Graph → Delegated: `Notes.Read`, `Notes.ReadWrite`, `User.Read`

## Reset Export State

To force a full re-export of all pages:

```bash
onenote-to-obsidian --reset-state
```

This clears `~/.onenote_exporter/export_state.json` so all pages are treated as new.
