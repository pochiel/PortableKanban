"""domain/export_template.py - テキストエクスポートテンプレートドメインモデル。"""

from dataclasses import dataclass


@dataclass
class ExportTemplate:
    """export_templatesテーブルに対応するデータクラス。

    template_body は Jinja2 テンプレート文字列。
    """

    name: str
    template_body: str
    id: int | None = None
    created_at: str = ""
    updated_at: str = ""

    @staticmethod
    def from_row(row: object) -> "ExportTemplate":
        """sqlite3.Row を ExportTemplate に変換する。"""
        return ExportTemplate(
            id=row["id"],
            name=row["name"],
            template_body=row["template_body"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
