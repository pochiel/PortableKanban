"""service/ticket_service.py - チケットの CRUD・フィルター検索・ステータス変更。"""

from domain.filter_condition import FilterCondition
from domain.service_result import ServiceResult
from domain.tag_value import TagValue
from domain.ticket import Ticket
from repository.settings_repository import SettingsRepository
from repository.tag_value_repository import TagValueRepository
from repository.ticket_change_history_repository import TicketChangeHistoryRepository
from repository.ticket_repository import TicketRepository

_MAX_TITLE_LENGTH = 200


class TicketService:
    """チケットの CRUD・フィルター検索・ステータス変更を担当する。"""

    def __init__(
        self,
        ticket_repo: TicketRepository | None = None,
        tag_value_repo: TagValueRepository | None = None,
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        self._ticket_repo = ticket_repo or TicketRepository()
        self._tag_value_repo = tag_value_repo or TagValueRepository()
        self._settings_repo = settings_repo or SettingsRepository()
        self._history_repo = TicketChangeHistoryRepository()

    # ------------------------------------------------------------------
    # 読み取り
    # ------------------------------------------------------------------

    def get_all(self, filter: FilterCondition | None = None) -> list[Ticket]:
        """フィルター条件に合致するチケット一覧を返す（削除済み除外）。"""
        return self._ticket_repo.find_all(filter=filter)

    def get_by_id(self, ticket_id: int) -> Ticket | None:
        """指定IDのチケットを返す。存在しない / 削除済みでも返す（詳細表示用）。"""
        return self._ticket_repo.find_by_id(ticket_id)

    def get_tag_values(self, ticket_id: int) -> list[TagValue]:
        """指定チケットのタグ値一覧を返す。"""
        return self._tag_value_repo.find_by_ticket(ticket_id)

    def get_prefix(self) -> str:
        """チケット番号プレフィックスを返す。未設定なら空文字。"""
        return self._settings_repo.get("ticket_prefix") or ""

    # ------------------------------------------------------------------
    # 作成・更新・削除
    # ------------------------------------------------------------------

    def create(
        self,
        title: str,
        status_id: int,
        assignee_id: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        note: str = "",
        tag_values: dict[int, str] | None = None,
    ) -> ServiceResult:
        """チケットを新規作成する。

        Args:
            tag_values: {tag_def_id: value} の辞書。空値はスキップ。

        Returns:
            is_ok=True: data に作成した Ticket を持つ。
        """
        error = self._validate(title, start_date, end_date)
        if error:
            return ServiceResult.err(error)

        ticket = Ticket(
            title=title.strip(),
            status_id=status_id,
            assignee_id=assignee_id,
            start_date=start_date or None,
            end_date=end_date or None,
            note=note,
        )
        saved = self._ticket_repo.save(ticket)

        if tag_values:
            self._save_tag_values(saved.id, tag_values)

        # 変更履歴: 新規作成時は old_value=None で記録
        history: list[tuple] = [("status", None, str(status_id))]
        if start_date:
            history.append(("start_date", None, start_date))
        if end_date:
            history.append(("end_date", None, end_date))
        self._history_repo.record_many(
            [(saved.id, f, o, n) for f, o, n in history]
        )

        return ServiceResult.ok(data=saved)

    def update(
        self,
        ticket_id: int,
        title: str,
        status_id: int,
        assignee_id: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        note: str = "",
        tag_values: dict[int, str] | None = None,
    ) -> ServiceResult:
        """チケットを更新する。"""
        existing = self._ticket_repo.find_by_id(ticket_id)
        if existing is None:
            return ServiceResult.err(f"チケットID {ticket_id} が見つかりません。")

        error = self._validate(title, start_date, end_date)
        if error:
            return ServiceResult.err(error)

        # 変更履歴: 変更があったフィールドのみ記録
        history: list[tuple] = []
        if existing.status_id != status_id:
            history.append((ticket_id, "status", str(existing.status_id), str(status_id)))
        if existing.start_date != (start_date or None):
            history.append((ticket_id, "start_date", existing.start_date, start_date or None))
        if existing.end_date != (end_date or None):
            history.append((ticket_id, "end_date", existing.end_date, end_date or None))

        existing.title = title.strip()
        existing.status_id = status_id
        existing.assignee_id = assignee_id
        existing.start_date = start_date or None
        existing.end_date = end_date or None
        existing.note = note
        saved = self._ticket_repo.save(existing)

        if tag_values is not None:
            self._save_tag_values(ticket_id, tag_values)

        if history:
            self._history_repo.record_many(history)

        return ServiceResult.ok(data=saved)

    def soft_delete(self, ticket_id: int) -> ServiceResult:
        """チケットを論理削除する（is_deleted=1）。"""
        existing = self._ticket_repo.find_by_id(ticket_id)
        if existing is None:
            return ServiceResult.err(f"チケットID {ticket_id} が見つかりません。")

        self._ticket_repo.soft_delete(ticket_id)
        return ServiceResult.ok()

    def change_status(self, ticket_id: int, new_status_id: int) -> ServiceResult:
        """チケットのステータスを変更する（ドラッグ&ドロップ用）。"""
        existing = self._ticket_repo.find_by_id(ticket_id)
        if existing is None:
            return ServiceResult.err(f"チケットID {ticket_id} が見つかりません。")

        from repository.status_repository import StatusRepository
        if StatusRepository().find_by_id(new_status_id) is None:
            return ServiceResult.err(f"ステータスID {new_status_id} が存在しません。")

        old_status_id = existing.status_id
        existing.status_id = new_status_id
        self._ticket_repo.save(existing)
        self._history_repo.record(ticket_id, "status", str(old_status_id), str(new_status_id))
        return ServiceResult.ok()

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(title: str, start_date: str | None, end_date: str | None) -> str:
        """バリデーションエラーメッセージを返す。エラーなしは空文字。"""
        if not title.strip():
            return "タイトルを入力してください。"
        if len(title.strip()) > _MAX_TITLE_LENGTH:
            return f"タイトルは{_MAX_TITLE_LENGTH}文字以内で入力してください。"
        if start_date and end_date and start_date > end_date:
            return "開始日は終了予定日より前の日付を指定してください。"
        return ""

    def _save_tag_values(self, ticket_id: int, tag_values: dict[int, str]) -> None:
        """タグ値を保存する。空値はスキップ。"""
        tv_list = [
            TagValue(ticket_id=ticket_id, tag_def_id=def_id, value=value)
            for def_id, value in tag_values.items()
        ]
        self._tag_value_repo.save_all(ticket_id, tv_list)
