"""Tests for configuration management."""

import json
from pathlib import Path
from unittest.mock import patch

from onenote_to_obsidian.config import (
    DEFAULT_AUTHORITY,
    DEFAULT_CLIENT_ID,
    DEFAULT_SCOPES,
    DEFAULT_VAULT_PATH,
    Config,
)


class TestConfigDefaults:
    def test_default_values(self):
        config = Config()
        assert config.client_id == DEFAULT_CLIENT_ID
        assert config.vault_path == DEFAULT_VAULT_PATH
        assert config.authority == DEFAULT_AUTHORITY
        assert config.scopes == list(DEFAULT_SCOPES)

    def test_default_vault_path_is_home_relative(self):
        assert "ObsidianVault" in DEFAULT_VAULT_PATH
        assert str(Path.home()) in DEFAULT_VAULT_PATH

    def test_custom_values(self):
        config = Config(
            client_id="custom-id",
            vault_path="/custom/vault",
            authority="https://custom.authority",
            scopes=["Custom.Scope"],
            config_dir="/custom/dir",
        )
        assert config.client_id == "custom-id"
        assert config.vault_path == "/custom/vault"
        assert config.scopes == ["Custom.Scope"]


class TestConfigProperties:
    def test_config_dir_path(self, tmp_path):
        config = Config(config_dir=str(tmp_path / "mydir"))
        assert config.config_dir_path == tmp_path / "mydir"

    def test_config_file(self, tmp_path):
        config = Config(config_dir=str(tmp_path / "mydir"))
        assert config.config_file == tmp_path / "mydir" / "config.json"


class TestConfigSave:
    def test_save_creates_file(self, tmp_path):
        config_dir = tmp_path / "config"
        config = Config(config_dir=str(config_dir))
        config.save()

        config_file = config_dir / "config.json"
        assert config_file.exists()

    def test_save_creates_dir(self, tmp_path):
        config_dir = tmp_path / "deep" / "nested" / "config"
        config = Config(config_dir=str(config_dir))
        config.save()

        assert config_dir.exists()

    def test_save_valid_json(self, tmp_path):
        config_dir = tmp_path / "config"
        config = Config(
            client_id="test-id",
            vault_path="/test/vault",
            config_dir=str(config_dir),
        )
        config.save()

        data = json.loads((config_dir / "config.json").read_text())
        assert data["client_id"] == "test-id"
        assert data["vault_path"] == "/test/vault"
        assert "scopes" in data

    def test_save_sets_file_permissions(self, tmp_path):
        config_dir = tmp_path / "config"
        config = Config(config_dir=str(config_dir))
        config.save()

        config_file = config_dir / "config.json"
        mode = config_file.stat().st_mode & 0o777
        assert mode == 0o600

    def test_save_overwrites_existing(self, tmp_path):
        config_dir = tmp_path / "config"
        config = Config(client_id="first", config_dir=str(config_dir))
        config.save()

        config.client_id = "second"
        config.save()

        data = json.loads((config_dir / "config.json").read_text())
        assert data["client_id"] == "second"


class TestConfigLoad:
    def test_load_existing(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        data = {
            "client_id": "loaded-id",
            "vault_path": "/loaded/vault",
            "authority": DEFAULT_AUTHORITY,
            "scopes": ["Notes.Read"],
            "config_dir": str(config_dir),
            "attachments_folder_name": "attachments",
        }
        (config_dir / "config.json").write_text(json.dumps(data))

        loaded = Config.load(config_dir)
        assert loaded is not None
        assert loaded.client_id == "loaded-id"
        assert loaded.vault_path == "/loaded/vault"

    def test_load_missing_returns_none(self, tmp_path):
        result = Config.load(tmp_path / "nonexistent")
        assert result is None

    def test_load_roundtrip(self, tmp_path):
        config_dir = tmp_path / "config"
        original = Config(
            client_id="roundtrip-id",
            vault_path="/roundtrip",
            config_dir=str(config_dir),
        )
        original.save()

        loaded = Config.load(config_dir)
        assert loaded is not None
        assert loaded.client_id == original.client_id
        assert loaded.vault_path == original.vault_path
        assert loaded.scopes == original.scopes


class TestLoadOrSetup:
    def test_loads_existing_config(self, tmp_path):
        config_dir = tmp_path / "config"
        existing = Config(client_id="existing", config_dir=str(config_dir))
        existing.save()

        loaded = Config.load_or_setup(config_dir=config_dir)
        assert loaded.client_id == "existing"

    def test_overrides_vault_path(self, tmp_path):
        config_dir = tmp_path / "config"
        existing = Config(
            vault_path="/original",
            config_dir=str(config_dir),
        )
        existing.save()

        loaded = Config.load_or_setup(
            vault_path="/overridden",
            config_dir=config_dir,
        )
        assert loaded.vault_path == "/overridden"

    def test_creates_default_when_missing(self, tmp_path):
        config_dir = tmp_path / "config"
        config = Config.load_or_setup(config_dir=config_dir)
        assert config.client_id == DEFAULT_CLIENT_ID
        assert (config_dir / "config.json").exists()

    @patch("builtins.input", return_value="")
    def test_force_setup_default_client(self, mock_input, tmp_path):
        config_dir = tmp_path / "config"
        config = Config.load_or_setup(
            config_dir=config_dir,
            force_setup=True,
        )
        assert config.client_id == DEFAULT_CLIENT_ID

    @patch("builtins.input", return_value="custom-client-id-from-user")
    def test_force_setup_custom_client(self, mock_input, tmp_path):
        config_dir = tmp_path / "config"
        config = Config.load_or_setup(
            config_dir=config_dir,
            force_setup=True,
        )
        assert config.client_id == "custom-client-id-from-user"

    def test_force_setup_saves_config(self, tmp_path):
        config_dir = tmp_path / "config"
        with patch("builtins.input", return_value=""):
            Config.load_or_setup(config_dir=config_dir, force_setup=True)
        assert (config_dir / "config.json").exists()

    def test_force_setup_overrides_existing(self, tmp_path):
        config_dir = tmp_path / "config"
        existing = Config(client_id="old", config_dir=str(config_dir))
        existing.save()

        with patch("builtins.input", return_value="new-id"):
            config = Config.load_or_setup(
                config_dir=config_dir,
                force_setup=True,
            )
        assert config.client_id == "new-id"
