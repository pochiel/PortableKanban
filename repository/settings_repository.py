"""repository/settings_repository.py - settings テーブルの CRUD。"""

from datetime import datetime, timezone

from db.connection import get_rules_db, execute_with_retry


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


class SettingsRepository:
    """settings テーブルの key-value 読み書き。"""

    def get(self, key: str) -> str | None:
        """指定キーの値を返す。存在しない場合は None。"""
        conn = get_rules_db()
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def set(self, key: str, value: str) -> None:
        """指定キーに値を保存する（upsert）。"""
        conn = get_rules_db()
        execute_with_retry(
            conn,
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, value, _now()),
        )
        conn.commit()
