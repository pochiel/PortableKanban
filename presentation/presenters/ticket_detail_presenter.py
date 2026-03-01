"""presentation/presenters/ticket_detail_presenter.py - SCR-005 チケット詳細・編集画面の Presenter。"""

from domain.member import Member
from domain.service_result import ServiceResult
from domain.status import Status
from domain.tag_definition import TagDefinition
from domain.tag_value import TagValue
from domain.ticket import Ticket
from service.member_service import MemberService
from service.status_service import StatusService
from service.tag_service import TagService
from service.ticket_service import TicketService


class TicketDetailPresenter:
    """チケット詳細・編集画面（SCR-005）のビジネスロジック仲介。

    ticket_id が None の場合は新規作成モード。
    """

    def __init__(self, view: object, ticket_id: int | None, role: str) -> None:
        self._view = view
        self._ticket_id = ticket_id
        self._role = role
        self._ticket_service = TicketService()
        self._member_service = MemberService()
        self._status_service = StatusService()
        self._tag_service = TagService()

    def on_load(self) -> None:
        """画面表示時に必要なデータを読み込む。"""
        members = self._member_service.get_all_active()
        statuses = self._status_service.get_all()
        tag_defs = self._tag_service.get_all()

        self._view.load_members(members)
        self._view.load_statuses(statuses)
        self._view.load_tag_definitions(tag_defs)

        # 新規作成・内容編集は member も可、削除のみ manager 限定
        can_delete = self._role == "manager"
        self._view.set_editable(True, can_delete=can_delete)

        if self._ticket_id is not None:
            ticket = self._ticket_service.get_by_id(self._ticket_id)
            tag_values = self._ticket_service.get_tag_values(self._ticket_id)
            prefix = self._ticket_service.get_prefix()
            self._view.load_ticket(ticket, tag_values, prefix)
        else:
            # 新規作成: デフォルト値をセット
            default_status = statuses[0] if statuses else None
            self._view.set_default_status(default_status.id if default_status else None)
            # Bug4: 開始日を今日にセット
            self._view.set_default_start_date()

    def on_save(
        self,
        title: str,
        status_id: int,
        assignee_id: int | None,
        start_date: str | None,
        end_date: str | None,
        note: str,
        tag_values: dict[int, str],
    ) -> None:
        """保存ボタン押下時の処理。"""
        if not title.strip():
            self._view.show_error("タイトルを入力してください。")
            return
        if assignee_id is None:
            self._view.show_error("担当者を選択してください。")
            return

        if self._ticket_id is None:
            result = self._ticket_service.create(
                title=title,
                status_id=status_id,
                assignee_id=assignee_id,
                start_date=start_date or None,
                end_date=end_date or None,
                note=note,
                tag_values=tag_values,
            )
        else:
            result = self._ticket_service.update(
                ticket_id=self._ticket_id,
                title=title,
                status_id=status_id,
                assignee_id=assignee_id,
                start_date=start_date or None,
                end_date=end_date or None,
                note=note,
                tag_values=tag_values,
            )

        if result.is_ok:
            self._view.go_to_kanban_board()
        else:
            self._view.show_error(result.error_message)

    def on_delete(self) -> None:
        """削除ボタン押下時の処理（論理削除）。"""
        if self._ticket_id is None:
            return
        result = self._ticket_service.soft_delete(self._ticket_id)
        if result.is_ok:
            self._view.go_to_kanban_board()
        else:
            self._view.show_error(result.error_message)

    def on_cancel(self) -> None:
        """戻るボタン押下時の処理。"""
        self._view.go_to_kanban_board()
