"""service/tag_service.py - タグ定義の CRUD ビジネスロジック。"""

from domain.service_result import ServiceResult
from domain.tag_definition import TagDefinition, VALID_FIELD_TYPES
from repository.tag_repository import TagRepository

_MAX_NAME_LENGTH = 50


class TagService:
    """タグ定義の CRUD を担当する。"""

    def __init__(self, tag_repo: TagRepository | None = None) -> None:
        self._repo = tag_repo or TagRepository()

    def get_all(self) -> list[TagDefinition]:
        """全タグ定義を返す。"""
        return self._repo.find_all()

    def create(self, name: str, field_type: str) -> ServiceResult:
        """タグ定義を新規作成する。

        Returns:
            is_ok=True: 成功。data に作成した TagDefinition を持つ。
        """
        error = self._validate(name, field_type)
        if error:
            return ServiceResult.err(error)

        tag = TagDefinition(name=name.strip(), field_type=field_type)
        saved = self._repo.save(tag)
        return ServiceResult.ok(data=saved)

    def update(self, tag_id: int, name: str, field_type: str) -> ServiceResult:
        """タグ定義を更新する。"""
        existing = self._repo.find_by_id(tag_id)
        if existing is None:
            return ServiceResult.err(f"タグID {tag_id} が見つかりません。")

        error = self._validate(name, field_type)
        if error:
            return ServiceResult.err(error)

        existing.name = name.strip()
        existing.field_type = field_type
        saved = self._repo.save(existing)
        return ServiceResult.ok(data=saved)

    def delete(self, tag_id: int) -> ServiceResult:
        """タグ定義を削除する。使用中チケットが存在する場合は失敗。"""
        existing = self._repo.find_by_id(tag_id)
        if existing is None:
            return ServiceResult.err(f"タグID {tag_id} が見つかりません。")

        if self._repo.is_in_use(tag_id):
            return ServiceResult.err(
                "このタグは使用中のチケットが存在するため削除できません。"
            )

        self._repo.delete(tag_id)
        return ServiceResult.ok()

    # ------------------------------------------------------------------
    # 内部バリデーション
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(name: str, field_type: str) -> str:
        if not name.strip():
            return "タグ名を入力してください。"
        if len(name.strip()) > _MAX_NAME_LENGTH:
            return f"タグ名は{_MAX_NAME_LENGTH}文字以内で入力してください。"
        if field_type not in VALID_FIELD_TYPES:
            return f"field_type は {sorted(VALID_FIELD_TYPES)} のいずれかを指定してください。"
        return ""
