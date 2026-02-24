"""service/lock_service.py - managerロックの取得・解放・ハートビート制御。

同時に1人のmanagerだけが編集できる排他制御を実現する。
ロックファイルのタイムスタンプが LOCK_TIMEOUT_SEC を超えた場合、
ロックを「無効（強制解放可能）」とみなす。
"""

import threading
from datetime import datetime, timezone

from domain.service_result import ServiceResult
from lock.manager_lock import ManagerLock

LOCK_TIMEOUT_SEC: int = 30       # ハートビートが止まったとみなす閾値（秒）
HEARTBEAT_INTERVAL_SEC: int = 10  # ハートビート更新間隔（秒）


class LockService:
    """managerロックファイルの制御を担当する。

    acquire() でロックを取得し、start_heartbeat() で定期更新を開始する。
    アプリ終了時は release() と stop_heartbeat() を呼ぶ。
    """

    def __init__(self, db_folder: str) -> None:
        self._lock = ManagerLock(db_folder)
        self._heartbeat_thread: threading.Thread | None = None
        self._heartbeat_stop = threading.Event()

    # ------------------------------------------------------------------
    # ロック操作
    # ------------------------------------------------------------------

    def acquire(self) -> ServiceResult:
        """ロックを取得する。他のmanagerが有効なロックを保持している場合は失敗。

        Returns:
            is_ok=True: 取得成功。
            is_ok=False: 他のmanagerがロック中（有効なロックあり）。
        """
        if self.is_locked_by_other():
            info = self._lock.get_locker_info() or "不明"
            return ServiceResult.err(
                f"現在、別のmanagerが編集中です: {info}\n"
                "しばらく待ってから再試行するか、相手に確認してください。"
            )

        self._lock.acquire()
        return ServiceResult.ok()

    def release(self) -> None:
        """ロックを解放する。"""
        self.stop_heartbeat()
        self._lock.release()

    def force_release(self) -> ServiceResult:
        """無効なロックを強制解放する。

        ロックが存在しない、またはタイムアウトしていない場合は失敗。
        """
        if not self._lock.exists():
            return ServiceResult.err("ロックファイルが存在しません。")

        if not self._is_lock_expired():
            info = self._lock.get_locker_info() or "不明"
            return ServiceResult.err(
                f"ロックはまだ有効です（{info}）。"
                f"タイムアウト（{LOCK_TIMEOUT_SEC}秒）後に再試行してください。"
            )

        self._lock.release()
        return ServiceResult.ok()

    # ------------------------------------------------------------------
    # 状態確認
    # ------------------------------------------------------------------

    def is_locked_by_other(self) -> bool:
        """有効なロックが存在するか返す（タイムアウト済みは無視）。"""
        if not self._lock.exists():
            return False
        return not self._is_lock_expired()

    def get_locker_info(self) -> str | None:
        """ロック中のmanager情報を返す。ロックなし or タイムアウト済みは None。"""
        if not self.is_locked_by_other():
            return None
        return self._lock.get_locker_info()

    # ------------------------------------------------------------------
    # ハートビート（3.2.3）
    # ------------------------------------------------------------------

    def start_heartbeat(self) -> None:
        """バックグラウンドでハートビート（タイムスタンプ更新）を開始する。"""
        if self._heartbeat_thread is not None and self._heartbeat_thread.is_alive():
            return  # 既に動作中

        self._heartbeat_stop.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name="LockHeartbeat",
        )
        self._heartbeat_thread.start()

    def stop_heartbeat(self) -> None:
        """ハートビートスレッドを停止する。"""
        self._heartbeat_stop.set()
        if self._heartbeat_thread is not None:
            self._heartbeat_thread.join(timeout=HEARTBEAT_INTERVAL_SEC + 1)
            self._heartbeat_thread = None

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------

    def _is_lock_expired(self) -> bool:
        """ロックのタイムスタンプが LOCK_TIMEOUT_SEC を超えているか返す。"""
        ts = self._lock.get_timestamp()
        if ts is None:
            return True  # 読み取り失敗 → 無効とみなす

        # タイムゾーン対応
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        elapsed = (datetime.now(timezone.utc) - ts).total_seconds()
        return elapsed > LOCK_TIMEOUT_SEC

    def _heartbeat_loop(self) -> None:
        """HEARTBEAT_INTERVAL_SEC ごとにロックファイルのタイムスタンプを更新する。"""
        while not self._heartbeat_stop.wait(timeout=HEARTBEAT_INTERVAL_SEC):
            self._lock.update_timestamp()
