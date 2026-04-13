"""Tests for OAuth2 authentication module."""

import json
from unittest.mock import MagicMock, patch, call

import pytest

from onenote_to_obsidian.auth import AuthManager, AuthError
from onenote_to_obsidian.config import Config, FALLBACK_CLIENT_ID


class TestAuthManagerInit:
    """Tests for AuthManager.__init__"""

    def test_init_creates_app_with_config(self, sample_config, mock_token_cache):
        """AuthManager initializes MSAL app with correct config."""
        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication") as mock_app_class, \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache):
            auth = AuthManager(sample_config)

            mock_app_class.assert_called_once_with(
                client_id=sample_config.client_id,
                authority=sample_config.authority,
                token_cache=mock_token_cache,
            )
            assert auth._config == sample_config
            assert auth._scopes == sample_config.scopes

    def test_init_sets_cache_path_correctly(self, sample_config, mock_token_cache):
        """AuthManager sets correct cache file path."""
        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication"), \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache):
            auth = AuthManager(sample_config)
            expected_cache_path = sample_config.config_dir_path / "token_cache.json"
            assert auth._cache_path == expected_cache_path

    def test_init_calls_load_cache(self, sample_config, tmp_path, mock_token_cache):
        """AuthManager calls _load_cache during initialization."""
        cache_file = sample_config.config_dir_path / "token_cache.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text('{"tokens": []}')

        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication"), \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache) as mock_cache_class:
            auth = AuthManager(sample_config)
            mock_token_cache.deserialize.assert_called_once()


class TestGetToken:
    """Tests for AuthManager.get_token()"""

    def test_silent_acquisition_success(self, sample_config, mock_token_cache):
        """get_token returns token from cache when silent acquire succeeds."""
        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication") as mock_app_class, \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache):
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            mock_app.get_accounts.return_value = [MagicMock()]
            mock_app.acquire_token_silent.return_value = {"access_token": "cached-token"}

            auth = AuthManager(sample_config)
            token = auth.get_token()

            assert token == "cached-token"
            mock_app.acquire_token_silent.assert_called_once()
            mock_token_cache.has_state_changed = False

    def test_silent_acquisition_with_no_accounts_falls_back_to_device_flow(
        self, sample_config, mock_token_cache
    ):
        """get_token falls back to device flow when no accounts exist."""
        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication") as mock_app_class, \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache), \
             patch("builtins.print"):
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            mock_app.get_accounts.return_value = []
            mock_app.initiate_device_flow.return_value = {
                "user_code": "ABC123",
                "verification_uri": "https://microsoft.com/devicelogin",
            }
            mock_app.acquire_token_by_device_flow.return_value = {
                "access_token": "device-flow-token",
            }

            auth = AuthManager(sample_config)
            token = auth.get_token()

            assert token == "device-flow-token"
            mock_app.acquire_token_by_device_flow.assert_called_once()

    def test_silent_acquisition_error_falls_back_to_device_flow(
        self, sample_config, mock_token_cache
    ):
        """get_token falls back to device flow when silent acquire returns error."""
        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication") as mock_app_class, \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache), \
             patch("builtins.print"):
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            mock_app.get_accounts.return_value = [MagicMock()]
            mock_app.acquire_token_silent.return_value = {
                "error": "invalid_grant",
                "error_description": "Token has expired",
            }
            mock_app.initiate_device_flow.return_value = {
                "user_code": "XYZ789",
                "verification_uri": "https://microsoft.com/devicelogin",
            }
            mock_app.acquire_token_by_device_flow.return_value = {
                "access_token": "refreshed-token",
            }

            auth = AuthManager(sample_config)
            token = auth.get_token()

            assert token == "refreshed-token"

    def test_silent_acquisition_none_result_falls_back_to_device_flow(
        self, sample_config, mock_token_cache
    ):
        """get_token falls back to device flow when silent acquire returns None."""
        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication") as mock_app_class, \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache), \
             patch("builtins.print"):
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            mock_app.get_accounts.return_value = [MagicMock()]
            mock_app.acquire_token_silent.return_value = None
            mock_app.initiate_device_flow.return_value = {
                "user_code": "ABC123",
                "verification_uri": "https://microsoft.com/devicelogin",
            }
            mock_app.acquire_token_by_device_flow.return_value = {
                "access_token": "new-token",
            }

            auth = AuthManager(sample_config)
            token = auth.get_token()

            assert token == "new-token"

    def test_get_token_saves_cache_on_silent_success(self, sample_config, mock_token_cache):
        """get_token saves cache after successful silent acquisition."""
        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication") as mock_app_class, \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache):
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            mock_app.get_accounts.return_value = [MagicMock()]
            mock_app.acquire_token_silent.return_value = {"access_token": "cached-token"}
            mock_token_cache.has_state_changed = True

            auth = AuthManager(sample_config)
            auth.get_token()

            mock_token_cache.serialize.assert_called()


class TestDeviceCodeFlow:
    """Tests for AuthManager._device_code_flow()"""

    def test_device_flow_success(self, sample_config, mock_token_cache):
        """_device_code_flow returns access token on success."""
        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication") as mock_app_class, \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache), \
             patch("builtins.print"):
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            mock_app.initiate_device_flow.return_value = {
                "user_code": "ABC123",
                "verification_uri": "https://microsoft.com/devicelogin",
            }
            mock_app.acquire_token_by_device_flow.return_value = {
                "access_token": "new-token",
            }
            mock_token_cache.has_state_changed = True

            auth = AuthManager(sample_config)
            token = auth._device_code_flow()

            assert token == "new-token"
            mock_token_cache.serialize.assert_called()

    def test_device_flow_missing_user_code_exits(self, sample_config, mock_token_cache):
        """_device_code_flow exits when initiate_device_flow returns no user_code."""
        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication") as mock_app_class, \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache), \
             patch("builtins.print"), \
             patch("sys.exit", side_effect=SystemExit(1)):
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            mock_app.initiate_device_flow.return_value = {
                "error": "invalid_client",
                "error_description": "Client not found in tenant",
            }

            auth = AuthManager(sample_config)
            with pytest.raises(SystemExit):
                auth._device_code_flow()

    def test_device_flow_missing_access_token_exits(self, sample_config, mock_token_cache):
        """_device_code_flow exits when acquire_token_by_device_flow returns no access_token."""
        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication") as mock_app_class, \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache), \
             patch("builtins.print"), \
             patch("sys.exit", side_effect=SystemExit(1)):
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            mock_app.initiate_device_flow.return_value = {
                "user_code": "ABC123",
                "verification_uri": "https://microsoft.com/devicelogin",
            }
            mock_app.acquire_token_by_device_flow.return_value = {
                "error": "AADSTS50020",
                "error_description": "does not exist in tenant",
            }

            auth = AuthManager(sample_config)
            with pytest.raises(SystemExit):
                auth._device_code_flow()

    def test_device_flow_aadsts50020_error_shows_fallback_suggestion(
        self, sample_config, mock_token_cache
    ):
        """_device_code_flow handles AADSTS50020 error with fallback suggestion."""
        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication") as mock_app_class, \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache), \
             patch("builtins.print") as mock_print, \
             patch("sys.exit", side_effect=SystemExit(1)):
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            mock_app.initiate_device_flow.return_value = {
                "user_code": "ABC123",
                "verification_uri": "https://microsoft.com/devicelogin",
            }
            mock_app.acquire_token_by_device_flow.return_value = {
                "error": "AADSTS50020",
                "error_description": "Account does not exist in tenant",
            }

            auth = AuthManager(sample_config)
            with pytest.raises(SystemExit):
                auth._device_code_flow()

            # Verify that fallback message is printed
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Account not supported" in str(c) for c in print_calls)

    def test_device_flow_aadsts65001_consent_error(
        self, sample_config, mock_token_cache
    ):
        """_device_code_flow handles AADSTS65001 consent error."""
        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication") as mock_app_class, \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache), \
             patch("builtins.print") as mock_print, \
             patch("sys.exit", side_effect=SystemExit(1)):
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            mock_app.initiate_device_flow.return_value = {
                "user_code": "ABC123",
                "verification_uri": "https://microsoft.com/devicelogin",
            }
            mock_app.acquire_token_by_device_flow.return_value = {
                "error": "AADSTS65001",
                "error_description": "User or admin has not consented to use the application",
            }

            auth = AuthManager(sample_config)
            with pytest.raises(SystemExit):
                auth._device_code_flow()

            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Consent required" in str(c) for c in print_calls)

    def test_device_flow_aadsts7000218_device_code_flow_not_supported(
        self, sample_config, mock_token_cache
    ):
        """_device_code_flow handles AADSTS7000218 device flow not supported error."""
        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication") as mock_app_class, \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache), \
             patch("builtins.print") as mock_print, \
             patch("sys.exit", side_effect=SystemExit(1)):
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            mock_app.initiate_device_flow.return_value = {
                "user_code": "ABC123",
                "verification_uri": "https://microsoft.com/devicelogin",
            }
            mock_app.acquire_token_by_device_flow.return_value = {
                "error": "AADSTS7000218",
                "error_description": "Device code flow is not supported for this client",
            }

            auth = AuthManager(sample_config)
            with pytest.raises(SystemExit):
                auth._device_code_flow()

            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("device code flow" in str(c).lower() for c in print_calls)


class TestSuggestFallback:
    """Tests for AuthManager._suggest_fallback()"""

    def test_suggest_fallback_when_not_using_fallback_id(
        self, sample_config, mock_token_cache
    ):
        """_suggest_fallback suggests switching to FALLBACK_CLIENT_ID."""
        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication"), \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache), \
             patch("builtins.print") as mock_print:
            auth = AuthManager(sample_config)
            auth._suggest_fallback("Some AADSTS error")

            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Microsoft Teams" in str(c) for c in print_calls)
            assert any(FALLBACK_CLIENT_ID in str(c) for c in print_calls)
            assert any("--setup" in str(c) for c in print_calls)

    def test_suggest_fallback_when_already_using_fallback_id(self, tmp_path, mock_token_cache):
        """_suggest_fallback provides Azure AD registration info when using fallback."""
        config = Config(
            client_id=FALLBACK_CLIENT_ID,
            vault_path=str(tmp_path / "vault"),
            authority="https://login.microsoftonline.com/common",
            scopes=["Notes.Read"],
            config_dir=str(tmp_path / ".config"),
        )

        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication"), \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache), \
             patch("builtins.print") as mock_print:
            auth = AuthManager(config)
            auth._suggest_fallback("Some AADSTS error")

            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Azure" in str(c) or "portal.azure.com" in str(c) for c in print_calls)
            assert any("All built-in" in str(c) for c in print_calls)


class TestLoadCache:
    """Tests for AuthManager._load_cache()"""

    def test_load_cache_from_existing_file(self, sample_config, mock_token_cache):
        """_load_cache loads cache from existing file."""
        cache_file = sample_config.config_dir_path / "token_cache.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_content = '{"tokens": [{"access_token": "old-token"}]}'
        cache_file.write_text(cache_content)

        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication"), \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache):
            auth = AuthManager(sample_config)
            mock_token_cache.deserialize.assert_called_once_with(cache_content)

    def test_load_cache_file_not_exists(self, sample_config, mock_token_cache):
        """_load_cache gracefully handles missing cache file."""
        # Ensure cache file does not exist
        cache_file = sample_config.config_dir_path / "token_cache.json"
        if cache_file.exists():
            cache_file.unlink()

        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication"), \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache):
            # Should not raise
            auth = AuthManager(sample_config)
            mock_token_cache.deserialize.assert_not_called()

    def test_load_cache_corrupted_file_logs_warning(self, sample_config, mock_token_cache):
        """_load_cache handles corrupted JSON gracefully."""
        cache_file = sample_config.config_dir_path / "token_cache.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text("{ invalid json }")

        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication"), \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache):
            # Should not raise
            auth = AuthManager(sample_config)
            # Cache should remain in initial state

    def test_load_cache_deserialization_error(self, sample_config, mock_token_cache):
        """_load_cache handles cache deserialization errors."""
        cache_file = sample_config.config_dir_path / "token_cache.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text('{"valid": "json"}')

        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication"), \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache):
            mock_token_cache.deserialize.side_effect = ValueError("Deserialization failed")
            # Should not raise
            auth = AuthManager(sample_config)


class TestSaveCache:
    """Tests for AuthManager._save_cache()"""

    def test_save_cache_when_state_changed(self, sample_config, mock_token_cache):
        """_save_cache writes cache file when has_state_changed is True."""
        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication"), \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache):
            mock_token_cache.has_state_changed = True
            mock_token_cache.serialize.return_value = '{"tokens": []}'

            auth = AuthManager(sample_config)
            auth._save_cache()

            cache_file = sample_config.config_dir_path / "token_cache.json"
            assert cache_file.exists()
            assert cache_file.read_text() == '{"tokens": []}'

    def test_save_cache_skipped_when_no_state_change(self, sample_config, mock_token_cache):
        """_save_cache does not write file when has_state_changed is False."""
        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication"), \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache):
            mock_token_cache.has_state_changed = False

            auth = AuthManager(sample_config)
            cache_file = sample_config.config_dir_path / "token_cache.json"
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            original_content = "original"
            cache_file.write_text(original_content)

            auth._save_cache()

            # File should not be modified
            assert cache_file.read_text() == original_content
            mock_token_cache.serialize.assert_not_called()

    def test_save_cache_creates_config_dir(self, tmp_path, mock_token_cache):
        """_save_cache creates config directory if it doesn't exist."""
        nonexistent_config_dir = tmp_path / "nonexistent" / ".config"
        config = Config(
            client_id="test-client-id",
            vault_path=str(tmp_path / "vault"),
            authority="https://login.microsoftonline.com/common",
            scopes=["Notes.Read"],
            config_dir=str(nonexistent_config_dir),
        )

        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication"), \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache):
            mock_token_cache.has_state_changed = True
            mock_token_cache.serialize.return_value = '{"tokens": []}'

            auth = AuthManager(config)
            auth._save_cache()

            assert nonexistent_config_dir.exists()
            cache_file = nonexistent_config_dir / "token_cache.json"
            assert cache_file.exists()

    def test_save_cache_sets_permissions_600(self, sample_config, mock_token_cache):
        """_save_cache sets file permissions to 600 (owner read/write only)."""
        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication"), \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache):
            mock_token_cache.has_state_changed = True
            mock_token_cache.serialize.return_value = '{"tokens": []}'

            auth = AuthManager(sample_config)
            auth._save_cache()

            cache_file = sample_config.config_dir_path / "token_cache.json"
            file_stat = cache_file.stat()
            file_mode = file_stat.st_mode & 0o777
            assert file_mode == 0o600


class TestAuthError:
    """Tests for AuthError exception."""

    def test_auth_error_is_exception(self):
        """AuthError is an Exception subclass."""
        assert issubclass(AuthError, Exception)

    def test_auth_error_can_be_raised(self):
        """AuthError can be raised and caught."""
        with pytest.raises(AuthError):
            raise AuthError("Test error message")

    def test_auth_error_message_preserved(self):
        """AuthError preserves error message."""
        message = "Test error message"
        try:
            raise AuthError(message)
        except AuthError as e:
            assert str(e) == message


class TestAuthManagerIntegration:
    """Integration tests for complete auth flows."""

    def test_complete_silent_flow_with_cache(self, sample_config, mock_token_cache):
        """Complete flow: init → get_token from cache → save."""
        cache_file = sample_config.config_dir_path / "token_cache.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text('{"tokens": []}')

        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication") as mock_app_class, \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache):
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            mock_app.get_accounts.return_value = [MagicMock()]
            mock_app.acquire_token_silent.return_value = {"access_token": "cached-token"}
            mock_token_cache.has_state_changed = True

            auth = AuthManager(sample_config)
            token = auth.get_token()

            assert token == "cached-token"
            assert cache_file.exists()

    def test_complete_device_flow(self, sample_config, mock_token_cache):
        """Complete flow: init → device_code_flow → save."""
        with patch("onenote_to_obsidian.auth.msal.PublicClientApplication") as mock_app_class, \
             patch("onenote_to_obsidian.auth.msal.SerializableTokenCache", return_value=mock_token_cache), \
             patch("builtins.print"):
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            mock_app.get_accounts.return_value = []
            mock_app.initiate_device_flow.return_value = {
                "user_code": "ABC123",
                "verification_uri": "https://microsoft.com/devicelogin",
            }
            mock_app.acquire_token_by_device_flow.return_value = {
                "access_token": "device-token",
            }
            mock_token_cache.has_state_changed = True

            auth = AuthManager(sample_config)
            token = auth.get_token()

            assert token == "device-token"
            cache_file = sample_config.config_dir_path / "token_cache.json"
            assert cache_file.exists()
