# FAQ

## Does this work with work/school Microsoft accounts?

It works with personal Microsoft accounts out of the box. Work/school accounts may require a custom client ID — run `--setup` and register your own app in [Azure AD](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app).

## Can I re-export without re-downloading everything?

Yes. The tool tracks exported pages by ID and modification time. Re-running exports only new or changed pages. Use `--reset-state` to force a full re-export.

## What happens if the export crashes mid-way?

Progress is saved in `~/.onenote_exporter/export_state.json`. Re-running picks up where it left off. File deduplication also survives crashes.

## Is my data sent anywhere besides Microsoft?

No. The tool only communicates with Microsoft Graph API and writes to your local filesystem. OAuth tokens are cached locally with owner-only permissions.

## How do I use a different Obsidian vault location?

```bash
onenote-to-obsidian --vault /path/to/your/vault
```

The default location is `~/ObsidianVault`.
