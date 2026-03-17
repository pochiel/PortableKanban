"""presentation/presenters/gantt_presenter.py - SCR-006 ガントチャート出力画面の Presenter。"""

from domain.filter_condition import FilterCondition
from domain.ticket import Ticket
from service.gantt_service import GanttService
from service.member_service import MemberService
from service.status_service import StatusService
from service.ticket_service import TicketService


class GanttPresenter:
    """ガントチャート出力画面（SCR-006）のビジネスロジック仲介。"""

    def __init__(self, view: object) -> None:
        self._view = view
        self._ticket_service = TicketService()
        self._member_service = MemberService()
        self._status_service = StatusService()
        self._gantt_service = GanttService()
        self._members: list = []
        self._statuses: list = []
        self._current_tickets: list[Ticket] = []
        self._output_path: str = ""

    def on_load(self) -> None:
        """画面表示時の初期化。"""
        self._members = self._member_service.get_all_active()
        self._statuses = self._status_service.get_all()
        self._view.init_filter(self._members, self._statuses)

        tickets = self._ticket_service.get_all(FilterCondition())
        self._current_tickets = tickets
        self._view.load_preview(tickets, self._members, self._statuses)

    def on_filter_changed(self, filter_condition: FilterCondition) -> None:
        """フィルター条件変更時の再描画。"""
        tickets = self._ticket_service.get_all(filter_condition)
        self._current_tickets = tickets
        self._view.load_preview(tickets, self._members, self._statuses)

    def on_export_html(self, output_path: str) -> None:
        """HTML出力ボタン押下時の処理。"""
        member_map = {m.id: m.name for m in self._members}
        status_map = {s.id: s.name for s in self._statuses}
        prefix = self._ticket_service.get_prefix()

        result = self._gantt_service.generate_html(
            tickets=self._current_tickets,
            member_map=member_map,
            status_map=status_map,
            prefix=prefix,
            output_path=output_path,
        )
        if result.is_ok:
            self._output_path = output_path
            self._view.set_output_ready(output_path)
            self.on_open_browser()
        else:
            self._view.show_error(result.error_message)

    def on_open_browser(self) -> None:
        """ブラウザで開くボタン押下時の処理。"""
        if not self._output_path:
            return
        result = self._gantt_service.open_browser(self._output_path)
        if not result.is_ok:
            self._view.show_error(result.error_message)
