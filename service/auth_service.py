"""service/auth_service.py - manager認証・パスワードハッシュ管理。"""

import hashlib
import secrets

from domain.service_result import ServiceResult
from repository.settings_repository import SettingsRepository

_SETTINGS_KEY_PASSWORD = "manager_password"  # settings テーブルのキー名
_HASH_ALGO = "sha256"
_SALT_BYTES = 16


class AuthService:
    """manager のパスワード認証を担当する。

    パスワードはハッシュ＋ランダムsaltで保存する（平文保存禁止）。
    保存形式: "<hex_salt>:<hex_digest>"
    """

    def __init__(self, settings_repo: SettingsRepository | None = None) -> None:
        self._settings_repo = settings_repo or SettingsRepository()

    def authenticate(self, password: str) -> ServiceResult:
        """パスワードを検証する。

        Returns:
            is_ok=True: 認証成功。
            is_ok=False: パスワード不一致またはパスワード未設定。
        """
        stored = self._settings_repo.get(_SETTINGS_KEY_PASSWORD)
        if stored is None:
            return ServiceResult.err("パスワードが設定されていません。")

        if not self._verify(password, stored):
            return ServiceResult.err("パスワードが正しくありません。")

        return ServiceResult.ok()

    def save_password(self, password: str) -> ServiceResult:
        """パスワードをハッシュ化して保存する。

        Args:
            password: 平文パスワード（空文字は不可）。

        Returns:
            is_ok=True: 保存成功。
        """
        if not password:
            return ServiceResult.err("パスワードを入力してください。")

        hashed = self._hash(password)
        self._settings_repo.set(_SETTINGS_KEY_PASSWORD, hashed)
        return ServiceResult.ok()

    def is_password_set(self) -> bool:
        """パスワードが設定済みかどうかを返す。"""
        return self._settings_repo.get(_SETTINGS_KEY_PASSWORD) is not None

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------

    @staticmethod
    def _hash(password: str) -> str:
        """ランダムsaltを生成してハッシュ文字列を返す。"""
        salt = secrets.token_hex(_SALT_BYTES)
        digest = hashlib.new(_HASH_ALGO, (salt + password).encode()).hexdigest()
        return f"{salt}:{digest}"

    @staticmethod
    def _verify(password: str, stored: str) -> bool:
        """保存済みハッシュと照合する。"""
        try:
            salt, digest = stored.split(":", 1)
        except ValueError:
            return False
        expected = hashlib.new(_HASH_ALGO, (salt + password).encode()).hexdigest()
        return secrets.compare_digest(expected, digest)
