"""domain/tag_value.py - タグ実体値ドメインモデル（EAVパターン）。"""

from dataclasses import dataclass


@dataclass
class TagValue:
    """tag_valuesテーブルに対応するデータクラス。

    value はすべて TEXT で保存し、型変換はアプリ層が担当する。
    """

    ticket_id: int
    tag_def_id: int
    value: str = ""
    id: int | None = None
    created_at: str = ""
    updated_at: str = ""

    @staticmethod
    def from_row(row: object) -> "TagValue":
        """sqlite3.Row を TagValue に変換する。"""
        return TagValue(
            id=row["id"],
            ticket_id=row["ticket_id"],
            tag_def_id=row["tag_def_id"],
            value=row["value"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
