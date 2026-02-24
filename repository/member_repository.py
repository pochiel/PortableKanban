"""repository/member_repository.py - members テーブルの CRUD。"""

from datetime import datetime, timezone

from db.connection import get_rules_db, execute_with_retry
from domain.member import Member


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


class MemberRepository:
    """members テーブルの読み書き。バリデーションは Service 層で行う。"""

    def find_all_active(self) -> list[Member]:
        """有効な担当者（is_active=1）を全件返す。"""
        conn = get_rules_db()
        rows = conn.execute(
            "SELECT * FROM members WHERE is_active = 1 ORDER BY id"
        ).fetchall()
        return [Member.from_row(row) for row in rows]

    def find_by_id(self, member_id: int) -> Member | None:
        """指定IDの担当者を返す。存在しない場合は None。"""
        conn = get_rules_db()
        row = conn.execute(
            "SELECT * FROM members WHERE id = ?", (member_id,)
        ).fetchone()
        return Member.from_row(row) if row else None

    def save(self, member: Member) -> Member:
        """新規作成または更新する。id が None なら INSERT、あれば UPDATE。

        Returns:
            id が採番された Member オブジェクト。
        """
        conn = get_rules_db()
        now = _now()

        if member.id is None:
            cursor = execute_with_retry(
                conn,
                "INSERT INTO members (name, email, is_active, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (member.name, member.email, int(member.is_active), now, now),
            )
            conn.commit()
            member.id = cursor.lastrowid
        else:
            execute_with_retry(
                conn,
                "UPDATE members SET name = ?, email = ?, is_active = ?, updated_at = ?"
                " WHERE id = ?",
                (member.name, member.email, int(member.is_active), now, member.id),
            )
            conn.commit()

        return member

    def deactivate(self, member_id: int) -> None:
        """担当者を論理削除する（is_active=0）。"""
        conn = get_rules_db()
        execute_with_retry(
            conn,
            "UPDATE members SET is_active = 0, updated_at = ? WHERE id = ?",
            (_now(), member_id),
        )
        conn.commit()
