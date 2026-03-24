"""repository/ticket_change_history_repository.py - ticket_change_history テーブルへの書き込み。"""

from datetime import datetime, timezone

from db.connection import get_work_db, execute_with_retry


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


class TicketChangeHistoryRepository:
    """ticket_change_history テーブルへのINSERT専用リポジトリ。"""

    def record(
        self,
        ticket_id: int,
        field_name: str,
        old_value: str | None,
        new_value: str | None,
    ) -> None:
        """変更履歴を1件INSERTする。"""
        conn = get_work_db()
        execute_with_retry(
            conn,
            "INSERT INTO ticket_change_history"
            " (ticket_id, field_name, old_value, new_value, changed_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (ticket_id, field_name, old_value, new_value, _now()),
        )
        conn.commit()

    def record_many(self, records: list[tuple]) -> None:
        """複数の変更履歴を一括INSERTする。records = [(ticket_id, field_name, old, new), ...]"""
        if not records:
            return
        conn = get_work_db()
        now = _now()
        for ticket_id, field_name, old_value, new_value in records:
            execute_with_retry(
                conn,
                "INSERT INTO ticket_change_history"
                " (ticket_id, field_name, old_value, new_value, changed_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (ticket_id, field_name, old_value, new_value, now),
            )
        conn.commit()
