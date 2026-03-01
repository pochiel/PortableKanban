"""tests/test_kanban_board.py - 6.2.4 カンバンボード結合テスト。

Presenter + Service + Repository + DB を通した結合テスト。
Qt ウィジェットは MockView で代替する。
"""

import os
import tempfile
import pytest

from db.connection import set_db_paths, init_rules_db, init_work_db, close_all
from service.status_service import StatusService
from service.member_service import MemberService
from service.ticket_service import TicketService
from domain.filter_condition import FilterCondition


# ------------------------------------------------------------------
# フィクスチャ
# ------------------------------------------------------------------


@pytest.fixture(autouse=True)
def tmp_db(tmp_path):
    rules = str(tmp_path / "rules.db")
    work = str(tmp_path / "work.db")
    init_rules_db(rules)
    init_work_db(work)
    set_db_paths(rules, work)
    yield
    close_all()


def _setup_board():
    """担当者・ステータス・チケットを3件作成してマップを返す。"""
    ms = MemberService()
    ms.create("田中", "tanaka@example.com")
    ms.create("高橋", "takahashi@example.com")
    members = ms.get_all_active()

    ss = StatusService()
    ss.create("未着手")
    ss.create("仕掛り中")
    ss.create("完了")
    statuses = ss.get_all()

    ts = TicketService()
    ts.create("チケット1", statuses[0].id, members[0].id, None, "2026-03-31", "メモ1", {})
    ts.create("チケット2", statuses[0].id, members[1].id, "2026-02-01", "2026-03-15", "", {})
    ts.create("チケット3", statuses[1].id, members[0].id, None, None, "", {})

    return members, statuses, ts


# ------------------------------------------------------------------
# MockView
# ------------------------------------------------------------------


class MockKanbanBoardView:
    """Presenter から呼ばれるメソッドの呼び出しを記録する Mock。"""

    def __init__(self):
        self.rendered_columns = []
        self.role_set = None
        self.warnings = []
        self.errors = []
        self.opened_ticket_ids = []
        self.filter_members = []
        self.filter_statuses = []
        self._filter = FilterCondition()

    def render_board(self, columns, member_map, prefix, draggable):
        self.rendered_columns = columns
        self.last_draggable = draggable

    def set_role(self, role):
        self.role_set = role

    def show_manager_warning(self, message):
        self.warnings.append(message)

    def hide_manager_warning(self):
        pass

    def show_error(self, message):
        self.errors.append(message)

    def open_ticket_detail(self, ticket_id):
        self.opened_ticket_ids.append(ticket_id)

    def init_filter(self, members, statuses, tag_defs, default_hidden_status_ids):
        self.filter_members = members
        self.filter_statuses = statuses

    def get_current_filter(self):
        return self._filter


# ------------------------------------------------------------------
# テスト: 初期ロード
# ------------------------------------------------------------------


class TestKanbanBoardOnLoad:
    def test_load_renders_all_statuses(self, tmp_db):
        members, statuses, ts = _setup_board()
        from presentation.presenters.kanban_board_presenter import KanbanBoardPresenter
        import tempfile

        db_folder = tempfile.gettempdir()
        view = MockKanbanBoardView()
        presenter = KanbanBoardPresenter(view=view, role="member", db_folder=db_folder)
        presenter.on_load()

        # デフォルト非表示なし → 全3ステータス分の列
        assert len(view.rendered_columns) == 3

    def test_load_sets_member_role(self, tmp_db):
        _setup_board()
        from presentation.presenters.kanban_board_presenter import KanbanBoardPresenter

        view = MockKanbanBoardView()
        presenter = KanbanBoardPresenter(view=view, role="member", db_folder=tempfile.gettempdir())
        presenter.on_load()

        assert view.role_set == "member"
        assert view.last_draggable is True  # member もドラッグ&ドロップ可

    def test_load_sets_manager_draggable(self, tmp_db):
        _setup_board()
        from presentation.presenters.kanban_board_presenter import KanbanBoardPresenter

        view = MockKanbanBoardView()
        # manager ロック取得は実ファイルが必要 → db_folder に tmp_path を渡す
        presenter = KanbanBoardPresenter(
            view=view, role="manager", db_folder=tempfile.gettempdir()
        )
        presenter.on_load()
        # manager・member ともに draggable=True
        assert view.last_draggable is True

    def test_tickets_distributed_to_correct_columns(self, tmp_db):
        members, statuses, ts = _setup_board()
        from presentation.presenters.kanban_board_presenter import KanbanBoardPresenter

        view = MockKanbanBoardView()
        presenter = KanbanBoardPresenter(view=view, role="member", db_folder=tempfile.gettempdir())
        presenter.on_load()

        # 未着手に2枚、仕掛り中に1枚
        col_map = {c.status.name: c.tickets for c in view.rendered_columns}
        assert len(col_map["未着手"]) == 2
        assert len(col_map["仕掛り中"]) == 1
        assert len(col_map["完了"]) == 0


# ------------------------------------------------------------------
# テスト: フィルター
# ------------------------------------------------------------------


class TestKanbanBoardFilter:
    def test_filter_by_status(self, tmp_db):
        members, statuses, ts = _setup_board()
        from presentation.presenters.kanban_board_presenter import KanbanBoardPresenter

        view = MockKanbanBoardView()
        presenter = KanbanBoardPresenter(view=view, role="member", db_folder=tempfile.gettempdir())
        presenter.on_load()

        # 「未着手」のみに絞り込む
        f = FilterCondition(status_ids=[statuses[0].id])
        view._filter = f
        presenter.on_filter_changed(f)

        assert len(view.rendered_columns) == 1
        assert view.rendered_columns[0].status.name == "未着手"
        assert len(view.rendered_columns[0].tickets) == 2

    def test_filter_by_assignee(self, tmp_db):
        members, statuses, ts = _setup_board()
        from presentation.presenters.kanban_board_presenter import KanbanBoardPresenter

        view = MockKanbanBoardView()
        presenter = KanbanBoardPresenter(view=view, role="member", db_folder=tempfile.gettempdir())
        presenter.on_load()

        # 田中さんのみに絞り込む（未着手1 + 仕掛り中1 = 2枚）
        f = FilterCondition(assignee_ids=[members[0].id])
        view._filter = f
        presenter.on_filter_changed(f)

        total = sum(len(c.tickets) for c in view.rendered_columns)
        assert total == 2


# ------------------------------------------------------------------
# テスト: カードクリック
# ------------------------------------------------------------------


class TestKanbanBoardCardClick:
    def test_card_click_opens_ticket_detail(self, tmp_db):
        members, statuses, ts = _setup_board()
        tickets = ts.get_all(FilterCondition())
        from presentation.presenters.kanban_board_presenter import KanbanBoardPresenter

        view = MockKanbanBoardView()
        presenter = KanbanBoardPresenter(view=view, role="member", db_folder=tempfile.gettempdir())
        presenter.on_load()
        presenter.on_card_clicked(tickets[0].id)

        assert tickets[0].id in view.opened_ticket_ids

    def test_new_ticket_opens_with_none(self, tmp_db):
        _setup_board()
        from presentation.presenters.kanban_board_presenter import KanbanBoardPresenter

        view = MockKanbanBoardView()
        presenter = KanbanBoardPresenter(view=view, role="member", db_folder=tempfile.gettempdir())
        presenter.on_load()
        presenter.on_new_ticket()

        assert None in view.opened_ticket_ids


# ------------------------------------------------------------------
# テスト: ドラッグ&ドロップ（ステータス変更）
# ------------------------------------------------------------------


class TestKanbanBoardCardDrop:
    def test_card_drop_changes_status(self, tmp_db):
        members, statuses, ts = _setup_board()
        tickets = ts.get_all(FilterCondition())
        # チケット1（未着手）を「完了」に移動
        ticket = next(t for t in tickets if t.title == "チケット1")
        done_status = next(s for s in statuses if s.name == "完了")

        from presentation.presenters.kanban_board_presenter import KanbanBoardPresenter

        view = MockKanbanBoardView()
        presenter = KanbanBoardPresenter(view=view, role="member", db_folder=tempfile.gettempdir())
        presenter.on_load()
        presenter.on_card_dropped(ticket.id, done_status.id)

        # DB に反映されているか確認
        updated = ts.get_by_id(ticket.id)
        assert updated.status_id == done_status.id

    def test_card_drop_invalid_status_shows_error(self, tmp_db):
        members, statuses, ts = _setup_board()
        tickets = ts.get_all(FilterCondition())

        from presentation.presenters.kanban_board_presenter import KanbanBoardPresenter

        view = MockKanbanBoardView()
        presenter = KanbanBoardPresenter(view=view, role="member", db_folder=tempfile.gettempdir())
        presenter.on_load()
        presenter.on_card_dropped(tickets[0].id, 99999)  # 存在しないステータス

        assert len(view.errors) > 0
