"""Configuration management and first-run setup wizard."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

DEFAULT_VAULT_PATH = str(Path.home() / "ObsidianVault")
DEFAULT_CONFIG_DIR = Path.home() / ".onenote_exporter"
DEFAULT_AUTHORITY = "https://login.microsoftonline.com/common"
DEFAULT_ATTACHMENTS_FOLDER = "attachments"

# Microsoft Office — pre-registered Microsoft app with
# Notes.Read, Notes.ReadWrite scopes for Graph API.
# No custom Azure AD registration required.
DEFAULT_CLIENT_ID = "d3590ed6-52b3-4102-aeff-aad2292ab01c"

# Fallback: Microsoft Teams — also has Notes.ReadWrite.All
FALLBACK_CLIENT_ID = "1fec8e78-bce4-4aaf-ab1b-5451cc387264"

DEFAULT_SCOPES = ["Notes.Read", "Notes.ReadWrite", "User.Read"]

CUSTOM_SETUP_INSTRUCTIONS = """\
╔══════════════════════════════════════════════════════════════════╗
║   OneNote → Obsidian Exporter: Custom Client ID Configuration   ║
╚══════════════════════════════════════════════════════════════════╝

By default, the tool uses Microsoft Office's public client_id which
requires no app registration. If you want to use your own — enter it below.

To register your own app:
  1. Create a free Azure account at https://portal.azure.com
  2. Microsoft Entra ID → App registrations → New registration
  3. Supported account types: "Accounts in any organizational directory
     and personal Microsoft accounts"
  4. Redirect URI: Public client → https://login.microsoftonline.com/common/oauth2/nativeclient
  5. Authentication → Allow public client flows = Yes
  6. API permissions → Microsoft Graph → Delegated:
     Notes.Read, Notes.ReadWrite, User.Read

Press Enter to use the default client_id (Microsoft Office).
"""


@dataclass
class Config:
    client_id: str = DEFAULT_CLIENT_ID
    vault_path: str = DEFAULT_VAULT_PATH
    authority: str = DEFAULT_AUTHORITY
    scopes: list[str] = field(default_factory=lambda: list(DEFAULT_SCOPES))
    config_dir: str = str(DEFAULT_CONFIG_DIR)
    attachments_folder_name: str = DEFAULT_ATTACHMENTS_FOLDER

    @property
    def config_dir_path(self) -> Path:
        return Path(self.config_dir)

    @property
    def config_file(self) -> Path:
        return self.config_dir_path / "config.json"

    def save(self):
        self.config_dir_path.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        self.config_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    @classmethod
    def load(cls, config_dir: Path = DEFAULT_CONFIG_DIR) -> "Config | None":
        config_file = config_dir / "config.json"
        if not config_file.exists():
            return None
        data = json.loads(config_file.read_text())
        return cls(**data)

    @classmethod
    def load_or_setup(
        cls,
        vault_path: str | None = None,
        config_dir: Path = DEFAULT_CONFIG_DIR,
        force_setup: bool = False,
    ) -> "Config":
        """Load existing config, create default, or run interactive setup."""
        if not force_setup:
            config = cls.load(config_dir)
            if config is not None:
                if vault_path:
                    config.vault_path = vault_path
                return config

        if force_setup:
            # Interactive setup for custom client_id
            print(CUSTOM_SETUP_INSTRUCTIONS)
            client_id = input("Application (client) ID [Enter = default]: ").strip()
            if not client_id:
                client_id = DEFAULT_CLIENT_ID
                print("Using default client_id: Microsoft Office")
        else:
            # Auto-create config with default client_id
            client_id = DEFAULT_CLIENT_ID
            print("Creating configuration with default client_id (Microsoft Office)...")

        config = cls(
            client_id=client_id,
            vault_path=vault_path or DEFAULT_VAULT_PATH,
            config_dir=str(config_dir),
        )
        config.save()
        print(f"Configuration saved to {config.config_file}\n")
        return config
