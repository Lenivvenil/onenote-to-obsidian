"""OAuth2 device code flow authentication with MSAL and token caching."""

import json
import logging
import sys
from pathlib import Path

import msal

from .config import Config, FALLBACK_CLIENT_ID

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Raised when authentication fails."""
    pass


class AuthManager:
    """Handles OAuth2 authentication via device code flow with token persistence."""

    def __init__(self, config: Config):
        self._config = config
        self._scopes = config.scopes
        self._cache = msal.SerializableTokenCache()
        self._cache_path = config.config_dir_path / "token_cache.json"
        self._load_cache()
        self._app = msal.PublicClientApplication(
            client_id=config.client_id,
            authority=config.authority,
            token_cache=self._cache,
        )

    def get_token(self) -> str:
        """Get a valid access token, refreshing or re-authenticating as needed."""
        # Try silent acquisition from cache
        accounts = self._app.get_accounts()
        if accounts:
            result = self._app.acquire_token_silent(
                self._scopes, account=accounts[0]
            )
            if result and "access_token" in result:
                logger.debug("Token acquired silently from cache")
                self._save_cache()
                return result["access_token"]
            if result and "error" in result:
                logger.warning(
                    "Silent token acquisition failed: %s",
                    result.get("error_description", ""),
                )

        # Fall back to device code flow
        return self._device_code_flow()

    def _device_code_flow(self) -> str:
        """Authenticate via device code flow."""
        flow = self._app.initiate_device_flow(scopes=self._scopes)
        if "user_code" not in flow:
            error_desc = flow.get("error_description", "Unknown error")
            error_code = flow.get("error", "")

            # Check if this is a client_id/scope issue
            if "AADSTS" in error_desc or "invalid" in error_desc.lower():
                logger.error("Device flow initiation failed: %s", error_desc)
                self._suggest_fallback(error_desc)

            print(f"Ошибка авторизации: {error_desc}")
            sys.exit(1)

        print()
        print("=" * 60)
        print("  Для авторизации:")
        print(f"  1. Откройте: {flow['verification_uri']}")
        print(f"  2. Введите код: {flow['user_code']}")
        print("=" * 60)
        print()
        print("Ожидание авторизации (у вас ~15 минут)...")

        result = self._app.acquire_token_by_device_flow(flow)

        if "access_token" not in result:
            error = result.get("error_description", result.get("error", "Unknown error"))
            error_code = result.get("error", "")

            # Specific error handling
            if "AADSTS50020" in error or "does not exist in tenant" in error:
                print(f"\nОшибка: Аккаунт не поддерживается с данным client_id.")
                self._suggest_fallback(error)
            elif "AADSTS65001" in error or "consent" in error.lower():
                print(f"\nОшибка: Требуется согласие на доступ.")
                print("Попробуйте принять разрешения при авторизации в браузере.")
            elif "AADSTS7000218" in error:
                print(f"\nОшибка: client_id не поддерживает device code flow.")
                self._suggest_fallback(error)
            else:
                print(f"\nОшибка авторизации: {error}")

            sys.exit(1)

        self._save_cache()
        logger.info("Successfully authenticated")
        print("Авторизация успешна!\n")
        return result["access_token"]

    def _suggest_fallback(self, error: str):
        """Suggest alternative client_id if current one fails."""
        current_id = self._config.client_id
        print(f"\nТекущий client_id: {current_id}")
        print()
        print("Попробуйте переключиться на другой client_id:")
        if current_id != FALLBACK_CLIENT_ID:
            print(f"  Microsoft Teams: {FALLBACK_CLIENT_ID}")
            print()
            print("Для этого запустите:")
            print("  python -m onenote_to_obsidian --setup")
            print(f"  и введите: {FALLBACK_CLIENT_ID}")
        else:
            print("  Все встроенные client_id не подошли.")
            print("  Вам потребуется зарегистрировать своё приложение в Azure AD.")
            print("  Создайте бесплатный аккаунт на https://portal.azure.com")
            print("  и запустите: python -m onenote_to_obsidian --setup")
        print()
        logger.debug("Auth error details: %s", error)

    def _load_cache(self):
        if self._cache_path.exists():
            try:
                self._cache.deserialize(self._cache_path.read_text())
            except (json.JSONDecodeError, Exception) as e:
                logger.warning("Failed to load token cache: %s", e)

    def _save_cache(self):
        if self._cache.has_state_changed:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(self._cache.serialize())
            # Restrict permissions to owner only
            self._cache_path.chmod(0o600)
