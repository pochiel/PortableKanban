"""domain/status.py - ステータス定義ドメインモデル。"""

from dataclasses import dataclass


@dataclass
class Status:
    """statusesテーブルに対応するデータクラス。

    display_order の昇順でカンバンボードの列を左→右に生成する。
    """

    name: str
    display_order: int
    id: int | None = None
    created_at: str = ""
    updated_at: str = ""

    @staticmethod
    def from_row(row: object) -> "Status":
        """sqlite3.Row を Status に変換する。"""
        return Status(
            id=row["id"],
            name=row["name"],
            display_order=row["display_order"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
