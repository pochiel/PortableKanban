"""lock/manager_lock.py - managerロックファイルの物理的な読み書き。

ロックファイルはDBと同じフォルダに配置する。
LockService から呼ばれることを想定している。

ファイル形式（JSON）:
    {
        "manager": "hostname",
        "timestamp": "2026-02-22T10:00:00"
    }
"""

import json
import socket
from datetime import datetime, timezone
from pathlib import Path

_LOCK_FILENAME = ".manager.lock"


class ManagerLock:
    """ロックファイルの読み書きを担当する低レベルクラス。"""

    def __init__(self, db_folder: str) -> None:
        self._lock_path = Path(db_folder) / _LOCK_FILENAME

    # ------------------------------------------------------------------
    # 書き込み系
    # ------------------------------------------------------------------

    def acquire(self) -> None:
        """ロックファイルを作成（上書き）する。"""
        data = {
            "manager": socket.gethostname(),
            "timestamp": _now_iso(),
        }
        self._lock_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def release(self) -> None:
        """ロックファイルを削除する。存在しない場合は何もしない。"""
        try:
            self._lock_path.unlink()
        except FileNotFoundError:
            pass

    def update_timestamp(self) -> None:
        """ロックファイルのタイムスタンプを現在時刻に更新する（ハートビート用）。"""
        if not self._lock_path.exists():
            return
        data = self._read_raw()
        if data is None:
            return
        data["timestamp"] = _now_iso()
        self._lock_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------
    # 読み取り系
    # ------------------------------------------------------------------

    def exists(self) -> bool:
        """ロックファイルが存在するか返す。"""
        return self._lock_path.exists()

    def read(self) -> dict | None:
        """ロックファイルの内容を dict で返す。読み取り失敗時は None。"""
        return self._read_raw()

    def get_locker_info(self) -> str | None:
        """ロック中のmanager情報を文字列で返す。ロックなしは None。"""
        data = self._read_raw()
        if data is None:
            return None
        manager = data.get("manager", "不明")
        timestamp = data.get("timestamp", "不明")
        return f"{manager} ({timestamp})"

    def get_timestamp(self) -> datetime | None:
        """ロックファイルのタイムスタンプを datetime で返す。失敗時は None。"""
        data = self._read_raw()
        if data is None:
            return None
        try:
            ts = data.get("timestamp", "")
            return datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------

    def _read_raw(self) -> dict | None:
        """ロックファイルを読み込んで dict を返す。失敗時は None。"""
        if not self._lock_path.exists():
            return None
        try:
            content = self._lock_path.read_text(encoding="utf-8")
            return json.loads(content)
        except (OSError, json.JSONDecodeError):
            return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
