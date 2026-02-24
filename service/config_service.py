"""service/config_service.py - config.ini の読み書き（UIなし設定管理）。"""

import configparser
from pathlib import Path


_CONFIG_FILENAME = "config.ini"
_SECTION = "app"
_KEY_LAST_DB_PATH = "last_db_path"


class ConfigService:
    """アプリローカルの config.ini を管理する。

    config.ini はアプリ実行ファイルと同じディレクトリに配置する。
    Samba共有のDBパスを「前回開いたパス」として保持するために使用する。
    """

    def __init__(self, config_dir: str | None = None) -> None:
        """
        Args:
            config_dir: config.ini を配置するディレクトリ。
                        None の場合は実行ファイルと同じディレクトリを使用する。
        """
        if config_dir is None:
            base = Path(__file__).parent.parent
        else:
            base = Path(config_dir)

        self._config_path = base / _CONFIG_FILENAME

    def get_last_db_path(self) -> str | None:
        """前回開いたDBディレクトリパスを返す。未設定の場合は None。"""
        parser = self._load()
        if not parser.has_option(_SECTION, _KEY_LAST_DB_PATH):
            return None
        value = parser.get(_SECTION, _KEY_LAST_DB_PATH).strip()
        return value if value else None

    def save_last_db_path(self, path: str) -> None:
        """DBディレクトリパスを保存する。"""
        parser = self._load()
        if not parser.has_section(_SECTION):
            parser.add_section(_SECTION)
        parser.set(_SECTION, _KEY_LAST_DB_PATH, path)
        with self._config_path.open("w", encoding="utf-8") as f:
            parser.write(f)

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------

    def _load(self) -> configparser.ConfigParser:
        parser = configparser.ConfigParser()
        if self._config_path.exists():
            parser.read(self._config_path, encoding="utf-8")
        return parser
