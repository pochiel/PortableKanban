"""repository/tag_value_repository.py - tag_values テーブルの読み書き。"""

from datetime import datetime, timezone

from db.connection import get_work_db, execute_with_retry
from domain.tag_value import TagValue


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


class TagValueRepository:
    """tag_values テーブルの読み書き。"""

    def find_by_ticket(self, ticket_id: int) -> list[TagValue]:
        """指定チケットの全タグ値を tag_def_id 昇順で返す。"""
        conn = get_work_db()
        rows = conn.execute(
            "SELECT * FROM tag_values WHERE ticket_id = ? ORDER BY tag_def_id",
            (ticket_id,),
        ).fetchall()
        return [TagValue.from_row(row) for row in rows]

    def save_all(self, ticket_id: int, tag_values: list[TagValue]) -> None:
        """指定チケットのタグ値を全件入れ替える（DELETE + INSERT）。

        値が空文字のエントリはスキップする（DBに保存しない）。
        """
        conn = get_work_db()
        now = _now()

        execute_with_retry(
            conn, "DELETE FROM tag_values WHERE ticket_id = ?", (ticket_id,)
        )

        for tv in tag_values:
            if not tv.value:
                continue  # 空値はスキップ
            execute_with_retry(
                conn,
                "INSERT INTO tag_values (ticket_id, tag_def_id, value, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (ticket_id, tv.tag_def_id, tv.value, now, now),
            )

        conn.commit()
