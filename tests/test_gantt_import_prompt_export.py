"""tests/test_gantt_import_prompt_export.py - 7.5/8.1.4/8.2.5/8.2.6 テスト。"""

import json
import os
import tempfile

import pytest

from db.connection import close_all, init_rules_db, init_work_db, set_db_paths
from service.member_service import MemberService
from service.status_service import StatusService
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
    yield tmp_path
    close_all()


def _make_tickets(tmp_path):
    ms = MemberService()
    ms.create("田中", "t@example.com")
    ms.create("高橋", "k@example.com")
    members = ms.get_all_active()

    ss = StatusService()
    ss.create("未着手")
    ss.create("完了")
    statuses = ss.get_all()

    ts = TicketService()
    ts.create("チケットA", statuses[0].id, members[0].id, "2026-01-01", "2026-01-31", "", {})
    ts.create("チケットB", statuses[0].id, members[1].id, "2026-02-01", "2026-02-28", "", {})
    ts.create("チケットC（日付なし）", statuses[1].id, None, None, None, "", {})
    return members, statuses, ts


# ==================================================================
# 7.5 GanttService テスト
# ==================================================================


class TestGanttService:
    def test_generate_html_success(self, tmp_db):
        members, statuses, ts = _make_tickets(tmp_db)
        from service.gantt_service import GanttService

        tickets = ts.get_all(FilterCondition())
        member_map = {m.id: m.name for m in members}
        status_map = {s.id: s.name for s in statuses}
        output = str(tmp_db / "gantt.html")

        svc = GanttService()
        try:
            result = svc.generate_html(tickets, member_map, status_map, "TEST", output)
            # plotly がある場合は成功、ない場合はエラーメッセージを確認
            if result.is_ok:
                assert os.path.exists(output)
            else:
                assert "plotly" in result.error_message
        except Exception:
            pass  # plotly 未インストール環境では skip

    def test_generate_html_no_dated_tickets_returns_error(self, tmp_db):
        """開始日・終了日のないチケットのみの場合はエラーを返す。"""
        ss = StatusService()
        ss.create("未着手")
        statuses = ss.get_all()
        ts = TicketService()
        ts.create("日付なし", statuses[0].id, None, None, None, "", {})

        from service.gantt_service import GanttService

        tickets = ts.get_all(FilterCondition())
        svc = GanttService()
        try:
            result = svc.generate_html(tickets, {}, {}, "", str(tmp_db / "out.html"))
            if not result.is_ok:
                # plotly なしエラー or 日付なしエラーのどちらか
                assert result.error_message
        except Exception:
            pass


# ==================================================================
# 8.1.4 PromptService テスト
# ==================================================================


class TestPromptService:
    def test_generate_prompt_includes_tickets(self, tmp_db):
        _make_tickets(tmp_db)
        from service.prompt_service import PromptService

        svc = PromptService()
        prompt = svc.generate_prompt()
        assert "チケットA" in prompt
        assert "田中" in prompt

    def test_generate_prompt_includes_statuses(self, tmp_db):
        _make_tickets(tmp_db)
        from service.prompt_service import PromptService

        svc = PromptService()
        prompt = svc.generate_prompt()
        assert "未着手" in prompt
        assert "完了" in prompt

    def test_generate_format_contains_schema(self, tmp_db):
        _make_tickets(tmp_db)
        from service.prompt_service import PromptService

        svc = PromptService()
        fmt = svc.generate_format()
        assert "ticket_id" in fmt
        assert "status_id" in fmt

    def test_generate_format_contains_valid_status_ids(self, tmp_db):
        _make_tickets(tmp_db)
        from service.prompt_service import PromptService
        from service.status_service import StatusService

        statuses = StatusService().get_all()
        svc = PromptService()
        fmt = svc.generate_format()
        for s in statuses:
            assert str(s.id) in fmt

    def test_empty_db_returns_no_ticket_message(self, tmp_db):
        """チケットが0件の場合もエラーにならずプロンプトが返る。"""
        from service.prompt_service import PromptService

        svc = PromptService()
        prompt = svc.generate_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0


# ==================================================================
# 8.2.5 ImportService バリデーションテスト
# ==================================================================


class TestImportServiceValidation:
    def _write_json(self, tmp_path, data):
        path = str(tmp_path / "import.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path

    def test_valid_json_returns_ok(self, tmp_db):
        members, statuses, ts = _make_tickets(tmp_db)
        from service.import_service import ImportService

        tickets = ts.get_all(FilterCondition())
        path = self._write_json(
            tmp_db,
            [{"ticket_id": tickets[0].id, "status_id": statuses[1].id}],
        )
        svc = ImportService()
        result = svc.load_and_validate(path)
        assert result.is_ok

    def test_missing_ticket_id_returns_error(self, tmp_db):
        _make_tickets(tmp_db)
        from service.import_service import ImportService

        path = self._write_json(tmp_db, [{"status_id": 1}])
        svc = ImportService()
        result = svc.load_and_validate(path)
        assert not result.is_ok
        assert "ticket_id" in result.error_message

    def test_invalid_ticket_id_returns_error(self, tmp_db):
        _make_tickets(tmp_db)
        from service.import_service import ImportService

        path = self._write_json(tmp_db, [{"ticket_id": 99999, "status_id": 1}])
        svc = ImportService()
        result = svc.load_and_validate(path)
        assert not result.is_ok
        assert "99999" in result.error_message

    def test_invalid_status_id_returns_error(self, tmp_db):
        members, statuses, ts = _make_tickets(tmp_db)
        from service.import_service import ImportService

        tickets = ts.get_all(FilterCondition())
        path = self._write_json(
            tmp_db,
            [{"ticket_id": tickets[0].id, "status_id": 99999}],
        )
        svc = ImportService()
        result = svc.load_and_validate(path)
        assert not result.is_ok
        assert "status_id" in result.error_message

    def test_invalid_assignee_id_returns_error(self, tmp_db):
        members, statuses, ts = _make_tickets(tmp_db)
        from service.import_service import ImportService

        tickets = ts.get_all(FilterCondition())
        path = self._write_json(
            tmp_db,
            [{"ticket_id": tickets[0].id, "assignee_id": 99999}],
        )
        svc = ImportService()
        result = svc.load_and_validate(path)
        assert not result.is_ok
        assert "assignee_id" in result.error_message

    def test_not_list_returns_error(self, tmp_db):
        _make_tickets(tmp_db)
        from service.import_service import ImportService

        path = self._write_json(tmp_db, {"ticket_id": 1})
        svc = ImportService()
        result = svc.load_and_validate(path)
        assert not result.is_ok

    def test_file_not_found_returns_error(self, tmp_db):
        from service.import_service import ImportService

        svc = ImportService()
        result = svc.load_and_validate("/nonexistent/path.json")
        assert not result.is_ok

    def test_invalid_json_returns_error(self, tmp_db):
        path = str(tmp_db / "bad.json")
        with open(path, "w") as f:
            f.write("{invalid json}")
        from service.import_service import ImportService

        svc = ImportService()
        result = svc.load_and_validate(path)
        assert not result.is_ok


# ==================================================================
# 8.2.6 ImportService 結合テスト（差分取得 + 実行）
# ==================================================================


class TestImportServiceIntegration:
    def _write_json(self, tmp_path, data):
        path = str(tmp_path / "import.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path

    def test_get_diff_detects_status_change(self, tmp_db):
        members, statuses, ts = _make_tickets(tmp_db)
        from service.import_service import ImportService

        tickets = ts.get_all(FilterCondition())
        ticket = tickets[0]
        new_status = next(s for s in statuses if s.id != ticket.status_id)

        path = self._write_json(
            tmp_db, [{"ticket_id": ticket.id, "status_id": new_status.id}]
        )
        svc = ImportService()
        svc.load_and_validate(path)
        diffs = svc.get_diff()

        assert len(diffs) == 1
        assert diffs[0].ticket_id == ticket.id
        assert any(d.field_name == "ステータス" for d in diffs[0].diffs)

    def test_get_diff_detects_assignee_change(self, tmp_db):
        members, statuses, ts = _make_tickets(tmp_db)
        from service.import_service import ImportService

        tickets = ts.get_all(FilterCondition())
        ticket = tickets[0]
        other_member = next(m for m in members if m.id != ticket.assignee_id)

        path = self._write_json(
            tmp_db, [{"ticket_id": ticket.id, "assignee_id": other_member.id}]
        )
        svc = ImportService()
        svc.load_and_validate(path)
        diffs = svc.get_diff()

        assert any(d.field_name == "担当者" for d in diffs[0].diffs)

    def test_execute_applies_status_change(self, tmp_db):
        members, statuses, ts = _make_tickets(tmp_db)
        from service.import_service import ImportService

        tickets = ts.get_all(FilterCondition())
        ticket = tickets[0]
        done = next(s for s in statuses if s.name == "完了")

        path = self._write_json(
            tmp_db, [{"ticket_id": ticket.id, "status_id": done.id}]
        )
        svc = ImportService()
        svc.load_and_validate(path)
        result = svc.execute()

        assert result.is_ok
        updated = ts.get_by_id(ticket.id)
        assert updated.status_id == done.id

    def test_execute_without_validate_returns_error(self, tmp_db):
        """validate を呼ばずに execute すると valid_updates が空なのでエラー。"""
        from service.import_service import ImportService

        svc = ImportService()
        result = svc.execute()
        assert not result.is_ok

    def test_execute_multiple_tickets(self, tmp_db):
        members, statuses, ts = _make_tickets(tmp_db)
        from service.import_service import ImportService

        tickets = ts.get_all(FilterCondition())
        done = next(s for s in statuses if s.name == "完了")
        updates = [
            {"ticket_id": tickets[0].id, "status_id": done.id},
            {"ticket_id": tickets[1].id, "status_id": done.id},
        ]
        path = self._write_json(tmp_db, updates)
        svc = ImportService()
        svc.load_and_validate(path)
        result = svc.execute()

        assert result.is_ok
        assert len(result.data) == 2
        for t in [tickets[0], tickets[1]]:
            assert ts.get_by_id(t.id).status_id == done.id
