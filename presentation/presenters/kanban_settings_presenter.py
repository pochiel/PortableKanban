"""presentation/presenters/kanban_settings_presenter.py - SCR-003 カンバン設定画面の Presenter。"""

from domain.member import Member
from domain.status import Status
from domain.tag_definition import TagDefinition
from service.member_service import MemberService
from service.status_service import StatusService
from service.tag_service import TagService


class KanbanSettingsPresenter:
    """カンバン設定画面（SCR-003）のビジネスロジック仲介。

    担当者・ステータス・タグ定義の CRUD を制御する。
    """

    def __init__(self, view: object) -> None:
        self._view = view
        self._member_service = MemberService()
        self._status_service = StatusService()
        self._tag_service = TagService()

    # ------------------------------------------------------------------
    # 初期ロード
    # ------------------------------------------------------------------

    def on_load(self) -> None:
        """画面表示時に全データを読み込む。"""
        self._reload_members()
        self._reload_statuses()
        self._reload_tags()

    # ------------------------------------------------------------------
    # 担当者操作
    # ------------------------------------------------------------------

    def on_add_member(self, name: str, email: str) -> None:
        result = self._member_service.create(name, email)
        if result.is_ok:
            self._view.show_success("担当者を追加しました。")
            self._reload_members()
        else:
            self._view.show_error(result.error_message)

    def on_edit_member(self, member_id: int, name: str, email: str) -> None:
        result = self._member_service.update(member_id, name, email)
        if result.is_ok:
            self._view.show_success("担当者を更新しました。")
            self._reload_members()
        else:
            self._view.show_error(result.error_message)

    def on_deactivate_member(self, member_id: int) -> None:
        result = self._member_service.deactivate(member_id)
        if result.is_ok:
            self._view.show_success("担当者を無効化しました。")
            self._reload_members()
        else:
            self._view.show_error(result.error_message)

    # ------------------------------------------------------------------
    # ステータス操作
    # ------------------------------------------------------------------

    def on_add_status(self, name: str) -> None:
        result = self._status_service.create(name)
        if result.is_ok:
            self._view.show_success("ステータスを追加しました。")
            self._reload_statuses()
        else:
            self._view.show_error(result.error_message)

    def on_edit_status(self, status_id: int, name: str) -> None:
        result = self._status_service.update(status_id, name)
        if result.is_ok:
            self._view.show_success("ステータスを更新しました。")
            self._reload_statuses()
        else:
            self._view.show_error(result.error_message)

    def on_delete_status(self, status_id: int) -> None:
        result = self._status_service.delete(status_id)
        if result.is_ok:
            self._view.show_success("ステータスを削除しました。")
            self._reload_statuses()
        else:
            self._view.show_error(result.error_message)

    def on_reorder_status(self, status_id: int, direction: str) -> None:
        result = self._status_service.reorder(status_id, direction)
        if result.is_ok:
            self._reload_statuses()
        else:
            self._view.show_error(result.error_message)

    def on_update_default_hidden(self, status_ids: list[int]) -> None:
        result = self._status_service.update_default_hidden(status_ids)
        if result.is_ok:
            self._view.show_success("デフォルト非表示設定を保存しました。")
        else:
            self._view.show_error(result.error_message)

    # ------------------------------------------------------------------
    # タグ操作
    # ------------------------------------------------------------------

    def on_add_tag(self, name: str, field_type: str) -> None:
        result = self._tag_service.create(name, field_type)
        if result.is_ok:
            self._view.show_success("タグを追加しました。")
            self._reload_tags()
        else:
            self._view.show_error(result.error_message)

    def on_edit_tag(self, tag_id: int, name: str, field_type: str) -> None:
        result = self._tag_service.update(tag_id, name, field_type)
        if result.is_ok:
            self._view.show_success("タグを更新しました。")
            self._reload_tags()
        else:
            self._view.show_error(result.error_message)

    def on_delete_tag(self, tag_id: int) -> None:
        result = self._tag_service.delete(tag_id)
        if result.is_ok:
            self._view.show_success("タグを削除しました。")
            self._reload_tags()
        else:
            self._view.show_error(result.error_message)

    # ------------------------------------------------------------------
    # 内部リロードヘルパー
    # ------------------------------------------------------------------

    def _reload_members(self) -> None:
        self._view.load_members(self._member_service.get_all_active())

    def _reload_statuses(self) -> None:
        hidden_ids = self._status_service.get_default_hidden_ids()
        self._view.load_statuses(self._status_service.get_all(), hidden_ids)

    def _reload_tags(self) -> None:
        self._view.load_tag_definitions(self._tag_service.get_all())
