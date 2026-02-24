"""domain/tag_definition.py - タグ定義ドメインモデル。"""

from dataclasses import dataclass

# field_type の許容値
FIELD_TYPE_TEXT = "text"
FIELD_TYPE_DATE = "date"
VALID_FIELD_TYPES: frozenset[str] = frozenset({FIELD_TYPE_TEXT, FIELD_TYPE_DATE})


@dataclass
class TagDefinition:
    """tag_definitionsテーブルに対応するデータクラス。

    field_type は "text" / "date" のみ許容する。
    """

    name: str
    field_type: str
    id: int | None = None
    created_at: str = ""
    updated_at: str = ""

    @staticmethod
    def from_row(row: object) -> "TagDefinition":
        """sqlite3.Row を TagDefinition に変換する。"""
        return TagDefinition(
            id=row["id"],
            name=row["name"],
            field_type=row["field_type"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
