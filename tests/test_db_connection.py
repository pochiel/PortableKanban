"""
tests/test_db_connection.py

db/connection.py の単体テスト（3.1.6）
"""

import sqlite3
from pathlib import Path

import pytest

import db.connection as connection


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_module_state():
    """各テスト後にモジュールのシングルトン状態をリセットする。"""
    yield
    connection.close_all()


@pytest.fixture()
def rules_db(tmp_path: Path) -> Path:
    return tmp_path / "rules.db"


@pytest.fixture()
def work_db(tmp_path: Path) -> Path:
    return tmp_path / "work.db"


# ---------------------------------------------------------------------------
# _create_connection（WAL・row_factory・外部キー）
# ---------------------------------------------------------------------------


class TestCreateConnection:
    def test_wal_mode_is_enabled(self, tmp_path: Path) -> None:
        """_create_connection() でWALモードが有効になること。"""
        db_path = str(tmp_path / "test.db")
        conn = connection._create_connection(db_path)
        try:
            row = conn.execute("PRAGMA journal_mode").fetchone()
            assert row[0] == "wal"
        finally:
            conn.close()

    def test_row_factory_is_set(self, tmp_path: Path) -> None:
        """_create_connection() で row_factory が sqlite3.Row になること。"""
        db_path = str(tmp_path / "test.db")
        conn = connection._create_connection(db_path)
        try:
            conn.execute("CREATE TABLE t (v INTEGER)")
            conn.execute("INSERT INTO t VALUES (42)")
            row = conn.execute("SELECT v FROM t").fetchone()
            # sqlite3.Row はカラム名でアクセス可能
            assert row["v"] == 42
        finally:
            conn.close()

    def test_foreign_keys_are_enabled(self, tmp_path: Path) -> None:
        """_create_connection() で外部キー制約が有効になること。"""
        db_path = str(tmp_path / "test.db")
        conn = connection._create_connection(db_path)
        try:
            row = conn.execute("PRAGMA foreign_keys").fetchone()
            assert row[0] == 1
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# set_db_paths / get_rules_db / get_work_db
# ---------------------------------------------------------------------------


class TestSetDbPaths:
    def test_raises_before_set(self) -> None:
        """set_db_paths() 呼び出し前は RuntimeError を送出すること。"""
        with pytest.raises(RuntimeError, match="rules.db"):
            connection.get_rules_db()

        with pytest.raises(RuntimeError, match="work.db"):
            connection.get_work_db()

    def test_returns_connection_after_set(self, rules_db: Path, work_db: Path) -> None:
        """set_db_paths() 後は正常に接続を返すこと。"""
        connection.set_db_paths(str(rules_db), str(work_db))
        rules_conn = connection.get_rules_db()
        work_conn = connection.get_work_db()
        assert isinstance(rules_conn, sqlite3.Connection)
        assert isinstance(work_conn, sqlite3.Connection)

    def test_returns_same_singleton(self, rules_db: Path, work_db: Path) -> None:
        """同一パスに対して get_rules_db() / get_work_db() は同じインスタンスを返すこと。"""
        connection.set_db_paths(str(rules_db), str(work_db))
        assert connection.get_rules_db() is connection.get_rules_db()
        assert connection.get_work_db() is connection.get_work_db()

    def test_resets_connection_on_repath(self, tmp_path: Path) -> None:
        """set_db_paths() を再呼び出しすると接続がリセットされること。"""
        path1 = str(tmp_path / "a.db")
        path2 = str(tmp_path / "b.db")

        connection.set_db_paths(path1, path1)
        conn1 = connection.get_rules_db()

        connection.set_db_paths(path2, path2)
        conn2 = connection.get_rules_db()

        assert conn1 is not conn2


# ---------------------------------------------------------------------------
# init_rules_db
# ---------------------------------------------------------------------------


class TestInitRulesDb:
    def test_creates_all_tables(self, rules_db: Path) -> None:
        """init_rules_db() で rules.db の全テーブルが作成されること。"""
        connection.init_rules_db(str(rules_db))

        conn = sqlite3.connect(str(rules_db))
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        finally:
            conn.close()

        assert "members" in tables
        assert "statuses" in tables
        assert "tag_definitions" in tables
        assert "export_templates" in tables
        assert "settings" in tables

    def test_idempotent(self, rules_db: Path) -> None:
        """init_rules_db() を2回実行してもエラーにならないこと。"""
        connection.init_rules_db(str(rules_db))
        connection.init_rules_db(str(rules_db))  # 再実行しても安全


# ---------------------------------------------------------------------------
# init_work_db
# ---------------------------------------------------------------------------


class TestInitWorkDb:
    def test_creates_all_tables(self, work_db: Path) -> None:
        """init_work_db() で work.db の全テーブルが作成されること。"""
        connection.init_work_db(str(work_db))

        conn = sqlite3.connect(str(work_db))
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        finally:
            conn.close()

        assert "tickets" in tables
        assert "tag_values" in tables

    def test_creates_indexes(self, work_db: Path) -> None:
        """init_work_db() でインデックスが作成されること。"""
        connection.init_work_db(str(work_db))

        conn = sqlite3.connect(str(work_db))
        try:
            indexes = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                ).fetchall()
            }
        finally:
            conn.close()

        assert "idx_tickets_status_id" in indexes
        assert "idx_tickets_assignee_id" in indexes
        assert "idx_tickets_is_deleted" in indexes
        assert "idx_tag_values_ticket_id" in indexes
        assert "idx_tag_values_tag_def_id_value" in indexes

    def test_tag_values_unique_constraint(self, work_db: Path) -> None:
        """tag_values は (ticket_id, tag_def_id) の重複を許容しないこと。"""
        connection.init_work_db(str(work_db))

        now = "2026-01-01T00:00:00"
        conn = sqlite3.connect(str(work_db))
        try:
            conn.execute(
                "INSERT INTO tickets (title, status_id, created_at, updated_at)"
                " VALUES ('t', 1, ?, ?)",
                (now, now),
            )
            conn.execute(
                "INSERT INTO tag_values (ticket_id, tag_def_id, value, created_at, updated_at)"
                " VALUES (1, 1, 'v1', ?, ?)",
                (now, now),
            )
            conn.commit()
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO tag_values (ticket_id, tag_def_id, value, created_at, updated_at)"
                    " VALUES (1, 1, 'v2', ?, ?)",
                    (now, now),
                )
                conn.commit()
        finally:
            conn.close()

    def test_idempotent(self, work_db: Path) -> None:
        """init_work_db() を2回実行してもエラーにならないこと。"""
        connection.init_work_db(str(work_db))
        connection.init_work_db(str(work_db))


# ---------------------------------------------------------------------------
# execute_with_retry
# ---------------------------------------------------------------------------


class TestExecuteWithRetry:
    def test_normal_execution(self, tmp_path: Path) -> None:
        """ロックなし正常系: クエリ結果を返すこと。"""
        db_path = str(tmp_path / "test.db")
        conn = connection._create_connection(db_path)
        try:
            conn.execute("CREATE TABLE t (v TEXT)")
            conn.execute("INSERT INTO t VALUES ('hello')")
            conn.commit()

            cursor = connection.execute_with_retry(conn, "SELECT v FROM t")
            row = cursor.fetchone()
            assert row["v"] == "hello"
        finally:
            conn.close()

    def test_reraises_non_lock_error(self, tmp_path: Path) -> None:
        """DBロック以外の OperationalError はそのまま再送出すること。"""
        db_path = str(tmp_path / "test.db")
        conn = connection._create_connection(db_path)
        try:
            with pytest.raises(sqlite3.OperationalError, match="no such table"):
                connection.execute_with_retry(conn, "SELECT * FROM nonexistent")
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# close_all
# ---------------------------------------------------------------------------


class TestCloseAll:
    def test_resets_paths_and_connections(self, rules_db: Path, work_db: Path) -> None:
        """close_all() 後に get_rules_db() を呼ぶと RuntimeError になること。"""
        connection.set_db_paths(str(rules_db), str(work_db))
        connection.get_rules_db()  # 接続を生成
        connection.close_all()

        with pytest.raises(RuntimeError):
            connection.get_rules_db()
