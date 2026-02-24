"""domain/member.py - 担当者ドメインモデル。"""

from dataclasses import dataclass


@dataclass
class Member:
    """membersテーブルに対応するデータクラス。

    is_active=False で論理削除。物理削除は行わない。
    """

    name: str
    id: int | None = None
    email: str = ""
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""

    @staticmethod
    def from_row(row: object) -> "Member":
        """sqlite3.Row を Member に変換する。"""
        return Member(
            id=row["id"],
            name=row["name"],
            email=row["email"] or "",
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
