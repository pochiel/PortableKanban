"""repository/tag_repository.py - tag_definitions テーブルの CRUD。"""

from datetime import datetime, timezone

from db.connection import get_rules_db, execute_with_retry
from domain.tag_definition import TagDefinition


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


class TagRepository:
    """tag_definitions テーブルの読み書き。"""

    def find_all(self) -> list[TagDefinition]:
        """全タグ定義を id 昇順で返す。"""
        conn = get_rules_db()
        rows = conn.execute(
            "SELECT * FROM tag_definitions ORDER BY id"
        ).fetchall()
        return [TagDefinition.from_row(row) for row in rows]

    def find_by_id(self, tag_id: int) -> TagDefinition | None:
        """指定IDのタグ定義を返す。存在しない場合は None。"""
        conn = get_rules_db()
        row = conn.execute(
            "SELECT * FROM tag_definitions WHERE id = ?", (tag_id,)
        ).fetchone()
        return TagDefinition.from_row(row) if row else None

    def save(self, tag: TagDefinition) -> TagDefinition:
        """新規作成または更新する。"""
        conn = get_rules_db()
        now = _now()

        if tag.id is None:
            cursor = execute_with_retry(
                conn,
                "INSERT INTO tag_definitions (name, field_type, created_at, updated_at)"
                " VALUES (?, ?, ?, ?)",
                (tag.name, tag.field_type, now, now),
            )
            conn.commit()
            tag.id = cursor.lastrowid
        else:
            execute_with_retry(
                conn,
                "UPDATE tag_definitions SET name = ?, field_type = ?, updated_at = ?"
                " WHERE id = ?",
                (tag.name, tag.field_type, now, tag.id),
            )
            conn.commit()

        return tag

    def delete(self, tag_id: int) -> None:
        """タグ定義を物理削除する。使用中チェックは Service 層で行う。"""
        conn = get_rules_db()
        execute_with_retry(
            conn, "DELETE FROM tag_definitions WHERE id = ?", (tag_id,)
        )
        conn.commit()

    def is_in_use(self, tag_id: int) -> bool:
        """work.db の tag_values テーブルで使用されているか確認する。"""
        from db.connection import get_work_db

        conn = get_work_db()
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM tag_values WHERE tag_def_id = ?",
            (tag_id,),
        ).fetchone()
        return row["cnt"] > 0
