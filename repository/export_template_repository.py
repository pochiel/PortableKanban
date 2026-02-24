"""repository/export_template_repository.py - export_templates テーブルの CRUD。"""

from datetime import datetime, timezone

from db.connection import get_rules_db, execute_with_retry
from domain.export_template import ExportTemplate


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


class ExportTemplateRepository:
    """export_templates テーブルの読み書き。"""

    def find_all(self) -> list[ExportTemplate]:
        """全テンプレートを id 昇順で返す。"""
        conn = get_rules_db()
        rows = conn.execute(
            "SELECT * FROM export_templates ORDER BY id"
        ).fetchall()
        return [ExportTemplate.from_row(row) for row in rows]

    def find_by_id(self, template_id: int) -> ExportTemplate | None:
        """指定IDのテンプレートを返す。存在しない場合は None。"""
        conn = get_rules_db()
        row = conn.execute(
            "SELECT * FROM export_templates WHERE id = ?", (template_id,)
        ).fetchone()
        return ExportTemplate.from_row(row) if row else None

    def save(self, template: ExportTemplate) -> ExportTemplate:
        """新規作成または更新する。"""
        conn = get_rules_db()
        now = _now()

        if template.id is None:
            cursor = execute_with_retry(
                conn,
                "INSERT INTO export_templates (name, template_body, created_at, updated_at)"
                " VALUES (?, ?, ?, ?)",
                (template.name, template.template_body, now, now),
            )
            conn.commit()
            template.id = cursor.lastrowid
        else:
            execute_with_retry(
                conn,
                "UPDATE export_templates SET name = ?, template_body = ?, updated_at = ?"
                " WHERE id = ?",
                (template.name, template.template_body, now, template.id),
            )
            conn.commit()

        return template

    def delete(self, template_id: int) -> None:
        """指定IDのテンプレートを削除する。"""
        conn = get_rules_db()
        execute_with_retry(
            conn,
            "DELETE FROM export_templates WHERE id = ?",
            (template_id,),
        )
        conn.commit()
