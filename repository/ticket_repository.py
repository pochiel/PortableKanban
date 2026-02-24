"""repository/ticket_repository.py - tickets テーブルの CRUD とフィルター検索。"""

from datetime import datetime, timezone

from db.connection import get_work_db, execute_with_retry
from domain.filter_condition import FilterCondition
from domain.ticket import Ticket


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


class TicketRepository:
    """tickets テーブルの読み書き。バリデーションは Service 層で行う。"""

    def find_all(
        self,
        filter: FilterCondition | None = None,
        include_deleted: bool = False,
    ) -> list[Ticket]:
        """フィルター条件に合致するチケットを返す。

        filter が None の場合はフィルターなし（削除済みを除く全件）。
        """
        conn = get_work_db()
        conditions: list[str] = []
        params: list = []

        if not include_deleted:
            conditions.append("t.is_deleted = 0")

        if filter:
            self._apply_filter(filter, conditions, params)

        where = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT t.* FROM tickets t WHERE {where} ORDER BY t.id"
        rows = conn.execute(query, params).fetchall()
        return [Ticket.from_row(row) for row in rows]

    def find_by_id(self, ticket_id: int) -> Ticket | None:
        """指定IDのチケットを返す。存在しない場合は None。"""
        conn = get_work_db()
        row = conn.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        return Ticket.from_row(row) if row else None

    def save(self, ticket: Ticket) -> Ticket:
        """新規作成または更新する。id が None なら INSERT、あれば UPDATE。"""
        conn = get_work_db()
        now = _now()

        if ticket.id is None:
            cursor = execute_with_retry(
                conn,
                "INSERT INTO tickets"
                " (title, assignee_id, status_id, start_date, end_date,"
                "  note, is_deleted, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ticket.title,
                    ticket.assignee_id,
                    ticket.status_id,
                    ticket.start_date,
                    ticket.end_date,
                    ticket.note,
                    int(ticket.is_deleted),
                    now,
                    now,
                ),
            )
            conn.commit()
            ticket.id = cursor.lastrowid
        else:
            execute_with_retry(
                conn,
                "UPDATE tickets SET"
                " title=?, assignee_id=?, status_id=?, start_date=?, end_date=?,"
                " note=?, is_deleted=?, updated_at=?"
                " WHERE id=?",
                (
                    ticket.title,
                    ticket.assignee_id,
                    ticket.status_id,
                    ticket.start_date,
                    ticket.end_date,
                    ticket.note,
                    int(ticket.is_deleted),
                    now,
                    ticket.id,
                ),
            )
            conn.commit()

        return ticket

    def soft_delete(self, ticket_id: int) -> None:
        """チケットを論理削除する（is_deleted=1）。"""
        conn = get_work_db()
        execute_with_retry(
            conn,
            "UPDATE tickets SET is_deleted=1, updated_at=? WHERE id=?",
            (_now(), ticket_id),
        )
        conn.commit()

    # ------------------------------------------------------------------
    # フィルタークエリ構築（内部）
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_filter(
        f: FilterCondition,
        conditions: list[str],
        params: list,
    ) -> None:
        """FilterCondition の各条件を WHERE 句に追加する。"""

        # 担当者フィルター（OR条件）
        if f.assignee_ids:
            placeholders = ",".join("?" * len(f.assignee_ids))
            conditions.append(f"t.assignee_id IN ({placeholders})")
            params.extend(f.assignee_ids)

        # ステータスフィルター（OR条件）
        if f.status_ids:
            placeholders = ",".join("?" * len(f.status_ids))
            conditions.append(f"t.status_id IN ({placeholders})")
            params.extend(f.status_ids)

        # タグフィルター（AND/OR/NOT）
        and_tags = [tf for tf in f.tag_filters if tf.operator == "and"]
        or_tags = [tf for tf in f.tag_filters if tf.operator == "or"]
        not_tags = [tf for tf in f.tag_filters if tf.operator == "not"]

        for tf in and_tags:
            conditions.append(
                "EXISTS ("
                "  SELECT 1 FROM tag_values tv"
                "  WHERE tv.ticket_id = t.id"
                "  AND tv.tag_def_id = ?"
                "  AND tv.value LIKE ?"
                ")"
            )
            params.extend([tf.tag_def_id, f"%{tf.value}%"])

        if or_tags:
            or_parts = []
            for tf in or_tags:
                or_parts.append(
                    "EXISTS ("
                    "  SELECT 1 FROM tag_values tv"
                    "  WHERE tv.ticket_id = t.id"
                    "  AND tv.tag_def_id = ?"
                    "  AND tv.value LIKE ?"
                    ")"
                )
                params.extend([tf.tag_def_id, f"%{tf.value}%"])
            conditions.append(f"({' OR '.join(or_parts)})")

        for tf in not_tags:
            conditions.append(
                "NOT EXISTS ("
                "  SELECT 1 FROM tag_values tv"
                "  WHERE tv.ticket_id = t.id"
                "  AND tv.tag_def_id = ?"
                "  AND tv.value LIKE ?"
                ")"
            )
            params.extend([tf.tag_def_id, f"%{tf.value}%"])

        # 日付フィルター（範囲）
        if f.start_date_from:
            conditions.append("t.start_date >= ?")
            params.append(str(f.start_date_from))
        if f.start_date_to:
            conditions.append("t.start_date <= ?")
            params.append(str(f.start_date_to))
        if f.end_date_from:
            conditions.append("t.end_date >= ?")
            params.append(str(f.end_date_from))
        if f.end_date_to:
            conditions.append("t.end_date <= ?")
            params.append(str(f.end_date_to))
