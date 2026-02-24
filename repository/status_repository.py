"""repository/status_repository.py - statuses テーブルの CRUD。"""

from datetime import datetime, timezone

from db.connection import get_rules_db, execute_with_retry
from domain.status import Status


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


class StatusRepository:
    """statuses テーブルの読み書き。"""

    def find_all(self) -> list[Status]:
        """全ステータスを display_order 昇順で返す。"""
        conn = get_rules_db()
        rows = conn.execute(
            "SELECT * FROM statuses ORDER BY display_order"
        ).fetchall()
        return [Status.from_row(row) for row in rows]

    def find_by_id(self, status_id: int) -> Status | None:
        """指定IDのステータスを返す。存在しない場合は None。"""
        conn = get_rules_db()
        row = conn.execute(
            "SELECT * FROM statuses WHERE id = ?", (status_id,)
        ).fetchone()
        return Status.from_row(row) if row else None

    def save(self, status: Status) -> Status:
        """新規作成または更新する。id が None なら INSERT、あれば UPDATE。"""
        conn = get_rules_db()
        now = _now()

        if status.id is None:
            cursor = execute_with_retry(
                conn,
                "INSERT INTO statuses (name, display_order, created_at, updated_at)"
                " VALUES (?, ?, ?, ?)",
                (status.name, status.display_order, now, now),
            )
            conn.commit()
            status.id = cursor.lastrowid
        else:
            execute_with_retry(
                conn,
                "UPDATE statuses SET name = ?, display_order = ?, updated_at = ?"
                " WHERE id = ?",
                (status.name, status.display_order, now, status.id),
            )
            conn.commit()

        return status

    def delete(self, status_id: int) -> None:
        """ステータスを物理削除する。使用中チェックは Service 層で行う。"""
        conn = get_rules_db()
        execute_with_retry(
            conn, "DELETE FROM statuses WHERE id = ?", (status_id,)
        )
        conn.commit()

    def is_in_use(self, status_id: int) -> bool:
        """work.db の tickets テーブルで使用されているか確認する。

        ※ cross-DB クエリは ATTACH を使わず Service 層経由で実装するため、
          ここでは work.db の接続を直接利用する。
        """
        from db.connection import get_work_db

        conn = get_work_db()
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM tickets WHERE status_id = ? AND is_deleted = 0",
            (status_id,),
        ).fetchone()
        return row["cnt"] > 0

    def get_max_display_order(self) -> int:
        """現在の最大 display_order を返す。ステータスが0件の場合は0を返す。"""
        conn = get_rules_db()
        row = conn.execute(
            "SELECT COALESCE(MAX(display_order), 0) AS max_order FROM statuses"
        ).fetchone()
        return row["max_order"]
