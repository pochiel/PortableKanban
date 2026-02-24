"""service/member_service.py - 担当者の CRUD ビジネスロジック。"""

from domain.member import Member
from domain.service_result import ServiceResult
from repository.member_repository import MemberRepository

_MAX_NAME_LENGTH = 100
_MAX_EMAIL_LENGTH = 255


class MemberService:
    """担当者の CRUD を担当する。バリデーション・業務ルールを持つ。"""

    def __init__(self, member_repo: MemberRepository | None = None) -> None:
        self._repo = member_repo or MemberRepository()

    def get_all_active(self) -> list[Member]:
        """有効な担当者を全件返す。"""
        return self._repo.find_all_active()

    def create(self, name: str, email: str = "") -> ServiceResult:
        """担当者を新規作成する。

        Returns:
            is_ok=True: 成功。data に作成した Member を持つ。
        """
        error = self._validate(name, email)
        if error:
            return ServiceResult.err(error)

        member = Member(name=name.strip(), email=email.strip())
        saved = self._repo.save(member)
        return ServiceResult.ok(data=saved)

    def update(self, member_id: int, name: str, email: str = "") -> ServiceResult:
        """担当者情報を更新する。"""
        existing = self._repo.find_by_id(member_id)
        if existing is None:
            return ServiceResult.err(f"担当者ID {member_id} が見つかりません。")

        error = self._validate(name, email)
        if error:
            return ServiceResult.err(error)

        existing.name = name.strip()
        existing.email = email.strip()
        saved = self._repo.save(existing)
        return ServiceResult.ok(data=saved)

    def deactivate(self, member_id: int) -> ServiceResult:
        """担当者を論理削除する（is_active=0）。"""
        existing = self._repo.find_by_id(member_id)
        if existing is None:
            return ServiceResult.err(f"担当者ID {member_id} が見つかりません。")

        self._repo.deactivate(member_id)
        return ServiceResult.ok()

    # ------------------------------------------------------------------
    # 内部バリデーション
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(name: str, email: str) -> str:
        """バリデーションエラーメッセージを返す。エラーなしは空文字。"""
        if not name.strip():
            return "担当者名を入力してください。"
        if len(name.strip()) > _MAX_NAME_LENGTH:
            return f"担当者名は{_MAX_NAME_LENGTH}文字以内で入力してください。"
        if email and len(email.strip()) > _MAX_EMAIL_LENGTH:
            return f"メールアドレスは{_MAX_EMAIL_LENGTH}文字以内で入力してください。"
        return ""
