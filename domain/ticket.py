"""domain/ticket.py - チケットドメインモデル。"""

from dataclasses import dataclass


@dataclass
class Ticket:
    """ticketsテーブルに対応するデータクラス。

    is_deleted=True のチケットは全画面で非表示（論理削除のみ、物理削除なし）。
    表示番号は display_number() で生成する。
    """

    title: str
    status_id: int
    id: int | None = None
    assignee_id: int | None = None
    start_date: str | None = None   # ISO8601 文字列（"YYYY-MM-DD"）
    end_date: str | None = None     # ISO8601 文字列（"YYYY-MM-DD"）
    note: str = ""
    is_deleted: bool = False
    created_at: str = ""
    updated_at: str = ""

    @staticmethod
    def from_row(row: object) -> "Ticket":
        """sqlite3.Row を Ticket に変換する。"""
        return Ticket(
            id=row["id"],
            title=row["title"],
            status_id=row["status_id"],
            assignee_id=row["assignee_id"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            note=row["note"] or "",
            is_deleted=bool(row["is_deleted"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def display_number(self, prefix: str) -> str:
        """チケット表示番号を返す（例: ABC-12）。"""
        return f"{prefix}-{self.id}"
