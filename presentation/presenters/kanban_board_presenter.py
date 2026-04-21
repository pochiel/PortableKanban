"""presentation/presenters/kanban_board_presenter.py - SCR-004 カンバンボードの Presenter。"""

import json

from domain.filter_condition import FilterCondition, TagFilter
from domain.member import Member
from domain.status import Status
from domain.ticket import Ticket
from repository.settings_repository import SettingsRepository
from service.lock_service import LockService
from service.status_service import StatusService
from service.ticket_service import TicketService

_SETTINGS_KEY_KANBAN_FILTER = "kanban_filter"


class StatusColumn:
    """カンバン列の描画データ。"""

    def __init__(self, status: Status, tickets: list[Ticket]) -> None:
        self.status = status
        self.tickets = tickets


class KanbanBoardPresenter:
    """カンバンボード画面（SCR-004）のビジネスロジック仲介。"""

    def __init__(self, view: object, role: str, db_folder: str) -> None:
        self._view = view
        self._role = role
        self._ticket_service = TicketService()
        self._status_service = StatusService()
        self._lock_service = LockService(db_folder)
        self._settings_repo = SettingsRepository()
        self._members: list[Member] = []
        self._statuses: list[Status] = []
        self._prefix: str = ""

    # ------------------------------------------------------------------
    # 初期ロード
    # ------------------------------------------------------------------

    def on_load(self) -> None:
        """画面表示時の初期化。"""
        from service.member_service import MemberService

        self._members = MemberService().get_all_active()
        self._statuses = self._status_service.get_all()
        self._prefix = self._ticket_service.get_prefix()

        # manager ロック取得
        if self._role == "manager":
            result = self._lock_service.acquire()
            if result.is_ok:
                self._lock_service.start_heartbeat()
            else:
                # ロック取得失敗 → memberとして使用する（閲覧のみ）
                self._role = "member"
                self._view.show_manager_warning(result.error_message)

        # ロールに応じてUI制御
        self._view.set_role(self._role)

        # ステータスフィルターの初期値（デフォルト非表示を除く）
        hidden_ids = self._status_service.get_default_hidden_ids()
        visible_status_ids = [s.id for s in self._statuses if s.id not in hidden_ids]

        # フィルターウィジェットに初期データをセット
        from service.tag_service import TagService
        self._view.init_filter(
            members=self._members,
            statuses=self._statuses,
            tag_defs=TagService().get_all(),
            default_hidden_status_ids=hidden_ids,
        )

        # 保存済みフィルターがあれば復元、なければデフォルト（非表示ステータスを除外）
        saved_filter = self._load_filter()
        if saved_filter is not None:
            self._view.restore_filter(saved_filter)
            self._render(saved_filter)
        else:
            initial_filter = FilterCondition(status_ids=visible_status_ids)
            self._render(initial_filter)

    def on_close(self) -> None:
        """アプリ終了時のクリーンアップ。"""
        if self._role == "manager":
            self._lock_service.release()

    # ------------------------------------------------------------------
    # フィルター・ボード更新
    # ------------------------------------------------------------------

    def on_filter_changed(self, filter: FilterCondition) -> None:
        """フィルター条件変更時の再描画。"""
        self._save_filter(filter)
        self._render(filter)

    def reload_and_render(self) -> None:
        """マスタデータ（担当者・ステータス）を再読み込みしてボードを再描画する。

        チケット詳細や設定画面から戻った時に呼ぶ。
        設定でステータスが追加された場合も正しく反映される。
        フィルター状態はリセットせず、ユーザーの設定を保持する。
        """
        from service.member_service import MemberService
        from service.tag_service import TagService

        # フィルター状態を保存（init_filter でリセットされる前に）
        saved_filter = self._view.get_current_filter()

        self._members = MemberService().get_all_active()
        self._statuses = self._status_service.get_all()
        self._prefix = self._ticket_service.get_prefix()

        hidden_ids = self._status_service.get_default_hidden_ids()

        self._view.init_filter(
            members=self._members,
            statuses=self._statuses,
            tag_defs=TagService().get_all(),
            default_hidden_status_ids=hidden_ids,
        )

        # フィルター状態を復元
        self._view.restore_filter(saved_filter)
        self._render(saved_filter)

    # ------------------------------------------------------------------
    # カード操作
    # ------------------------------------------------------------------

    def on_card_dropped(self, ticket_id: int, new_status_id: int) -> None:
        """ドラッグ&ドロップでカードが移動した時の処理。"""
        result = self._ticket_service.change_status(ticket_id, new_status_id)
        if not result.is_ok:
            self._view.show_error(result.error_message)
        # フィルターを保持したまま再描画
        self._render(self._view.get_current_filter())

    def on_card_clicked(self, ticket_id: int) -> None:
        """カードクリック時にチケット詳細へ遷移する。"""
        self._view.open_ticket_detail(ticket_id)

    def on_new_ticket(self) -> None:
        """新規チケット作成ボタン押下。"""
        self._view.open_ticket_detail(None)

    # ------------------------------------------------------------------
    # フィルター永続化
    # ------------------------------------------------------------------

    def _save_filter(self, condition: FilterCondition) -> None:
        from datetime import date
        data = {
            "assignee_ids": condition.assignee_ids,
            "status_ids": condition.status_ids,
            "tag_filters": [
                {"tag_def_id": tf.tag_def_id, "value": tf.value, "operator": tf.operator}
                for tf in condition.tag_filters
            ],
            "start_date_from": condition.start_date_from.isoformat() if condition.start_date_from else None,
            "start_date_to": condition.start_date_to.isoformat() if condition.start_date_to else None,
            "end_date_from": condition.end_date_from.isoformat() if condition.end_date_from else None,
            "end_date_to": condition.end_date_to.isoformat() if condition.end_date_to else None,
        }
        try:
            self._settings_repo.set(_SETTINGS_KEY_KANBAN_FILTER, json.dumps(data, ensure_ascii=False))
        except Exception:
            pass

    def _load_filter(self) -> FilterCondition | None:
        from datetime import date
        raw = self._settings_repo.get(_SETTINGS_KEY_KANBAN_FILTER)
        if raw is None:
            return None
        try:
            data = json.loads(raw)
            def _parse_date(s):
                return date.fromisoformat(s) if s else None
            return FilterCondition(
                assignee_ids=data.get("assignee_ids", []),
                status_ids=data.get("status_ids", []),
                tag_filters=[
                    TagFilter(tf["tag_def_id"], tf["value"], tf["operator"])
                    for tf in data.get("tag_filters", [])
                ],
                start_date_from=_parse_date(data.get("start_date_from")),
                start_date_to=_parse_date(data.get("start_date_to")),
                end_date_from=_parse_date(data.get("end_date_from")),
                end_date_to=_parse_date(data.get("end_date_to")),
            )
        except Exception:
            return None

    # ------------------------------------------------------------------
    # 内部描画ヘルパー
    # ------------------------------------------------------------------

    def _render(self, filter: FilterCondition) -> None:
        """フィルター条件に合致するチケットをカンバン列に配置して描画する。"""
        tickets = self._ticket_service.get_all(filter)
        member_map = {m.id: m.name for m in self._members}

        # status_ids フィルターが指定されている場合はその列のみ表示
        if filter.status_ids:
            visible_statuses = [s for s in self._statuses if s.id in filter.status_ids]
        else:
            visible_statuses = self._statuses

        columns: list[StatusColumn] = []
        for status in visible_statuses:
            col_tickets = [t for t in tickets if t.status_id == status.id]
            columns.append(StatusColumn(status=status, tickets=col_tickets))

        self._view.render_board(
            columns=columns,
            member_map=member_map,
            prefix=self._prefix,
            draggable=True,  # manager・member ともにドラッグ&ドロップ可
        )
