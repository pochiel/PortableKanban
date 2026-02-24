"""
db/connection.py

SQLite接続管理モジュール。
- get_rules_db() / get_work_db() 経由でのみ接続を取得する
- WALモード・row_factory を自動設定する
- Samba越しのロック対策として書き込みリトライ機構を提供する
- 接続はモジュール内でシングルトン管理する（グローバル変数はこのモジュール内に限定）
"""

import logging
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# --- 定数 ---

# Samba越しのロック競合リトライ設定
WRITE_RETRY_COUNT: int = 5
WRITE_RETRY_INTERVAL_SEC: float = 0.3

# sqlite3.connect() の timeout（秒）: DBファイルがロックされている間の待機上限
CONNECTION_TIMEOUT_SEC: float = 10.0

# --- モジュール内シングルトン ---

_rules_db_path: str | None = None
_work_db_path: str | None = None
_rules_conn: sqlite3.Connection | None = None
_work_conn: sqlite3.Connection | None = None


# ---------------------------------------------------------------------------
# 公開API
# ---------------------------------------------------------------------------

def set_db_paths(rules_db_path: str, work_db_path: str) -> None:
    """DB接続先のパスをセットする。アプリ起動時に一度だけ呼ぶ。

    既存の接続がある場合はクローズしてリセットする。
    """
    global _rules_db_path, _work_db_path, _rules_conn, _work_conn

    _close_if_open(_rules_conn)
    _close_if_open(_work_conn)

    _rules_db_path = rules_db_path
    _work_db_path = work_db_path
    _rules_conn = None
    _work_conn = None


def get_rules_db() -> sqlite3.Connection:
    """rules.db への接続を返す（遅延初期化・シングルトン）。

    Raises:
        RuntimeError: set_db_paths() が呼ばれていない場合。
    """
    global _rules_conn

    if _rules_db_path is None:
        raise RuntimeError(
            "rules.db のパスが未設定です。set_db_paths() を先に呼び出してください。"
        )
    if _rules_conn is None:
        _rules_conn = _create_connection(_rules_db_path)
    return _rules_conn


def get_work_db() -> sqlite3.Connection:
    """work.db への接続を返す（遅延初期化・シングルトン）。

    Raises:
        RuntimeError: set_db_paths() が呼ばれていない場合。
    """
    global _work_conn

    if _work_db_path is None:
        raise RuntimeError(
            "work.db のパスが未設定です。set_db_paths() を先に呼び出してください。"
        )
    if _work_conn is None:
        _work_conn = _create_connection(_work_db_path)
    return _work_conn


def init_rules_db(db_path: str) -> None:
    """rules.db を新規作成し、マイグレーションSQLを実行する。

    既存テーブルには IF NOT EXISTS を使用しているため再実行しても安全。
    """
    conn = _create_connection(db_path)
    try:
        sql = _load_migration_sql("rules_init.sql")
        conn.executescript(sql)
    finally:
        conn.close()


def init_work_db(db_path: str) -> None:
    """work.db を新規作成し、マイグレーションSQLを実行する。

    既存テーブルには IF NOT EXISTS を使用しているため再実行しても安全。
    """
    conn = _create_connection(db_path)
    try:
        sql = _load_migration_sql("work_init.sql")
        conn.executescript(sql)
    finally:
        conn.close()


def execute_with_retry(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple = (),
) -> sqlite3.Cursor:
    """書き込みをリトライ付きで実行する。

    Samba共有フォルダ上の SQLite では "database is locked" が
    発生しやすいため、一定回数リトライする。

    Args:
        conn: 使用するDB接続。
        sql: 実行するSQL文。
        params: バインドパラメータ。

    Returns:
        sqlite3.Cursor

    Raises:
        sqlite3.OperationalError: リトライ上限を超えてもロックが解消しない場合。
    """
    last_exc: sqlite3.OperationalError | None = None

    for attempt in range(1, WRITE_RETRY_COUNT + 1):
        try:
            return conn.execute(sql, params)
        except sqlite3.OperationalError as exc:
            if "database is locked" not in str(exc):
                raise
            last_exc = exc
            logger.warning(
                "DB がロック中のためリトライします (%d/%d): %s",
                attempt,
                WRITE_RETRY_COUNT,
                exc,
            )
            time.sleep(WRITE_RETRY_INTERVAL_SEC)

    # リトライ上限到達
    raise last_exc  # type: ignore[misc]


def close_all() -> None:
    """全接続をクローズし、シングルトンをリセットする。

    テスト後のクリーンアップやアプリ終了時に使用する。
    """
    global _rules_conn, _work_conn, _rules_db_path, _work_db_path

    _close_if_open(_rules_conn)
    _close_if_open(_work_conn)
    _rules_conn = None
    _work_conn = None
    _rules_db_path = None
    _work_db_path = None


# ---------------------------------------------------------------------------
# 内部ヘルパー
# ---------------------------------------------------------------------------

def _create_connection(db_path: str) -> sqlite3.Connection:
    """SQLite接続を生成し、WALモード・row_factory・外部キー制約を設定する。"""
    conn = sqlite3.connect(db_path, timeout=CONNECTION_TIMEOUT_SEC)
    conn.row_factory = sqlite3.Row
    # WALモード有効化（3.1.2）
    conn.execute("PRAGMA journal_mode=WAL")
    # 外部キー制約有効化
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _load_migration_sql(filename: str) -> str:
    """db/migrations/ 配下のSQLファイルを読み込んで返す。"""
    migration_dir = Path(__file__).parent / "migrations"
    sql_path = migration_dir / filename
    return sql_path.read_text(encoding="utf-8")


def _close_if_open(conn: sqlite3.Connection | None) -> None:
    """接続が存在する場合のみクローズする。"""
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
