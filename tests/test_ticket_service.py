"""
tests/test_ticket_service.py

チケット管理機能 / フィルター機能の単体テスト（WBS 5.1.4, 5.2.6）
"""

from datetime import date
from pathlib import Path

import pytest

import db.connection as connection
from domain.filter_condition import FilterCondition, TagFilter
from service.ticket_service import TicketService


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_db():
    yield
    connection.close_all()


@pytest.fixture()
def project(tmp_path: Path):
    connection.init_rules_db(str(tmp_path / "rules.db"))
    connection.init_work_db(str(tmp_path / "work.db"))
    connection.set_db_paths(
        str(tmp_path / "rules.db"),
        str(tmp_path / "work.db"),
    )
    return tmp_path


@pytest.fixture()
def svc(project: Path) -> TicketService:
    return TicketService()


def _create(svc: TicketService, title: str = "テスト", status_id: int = 1, **kw):
    """テスト用にチケットを作成して返す。"""
    result = svc.create(title=title, status_id=status_id, **kw)
    assert result.is_ok, result.error_message
    return result.data


# ---------------------------------------------------------------------------
# 5.1 チケット CRUD
# ---------------------------------------------------------------------------


class TestTicketCreate:
    def test_create_minimal(self, svc: TicketService) -> None:
        result = svc.create(title="タイトル", status_id=1)
        assert result.is_ok
        assert result.data.id is not None
        assert result.data.title == "タイトル"

    def test_create_full(self, svc: TicketService) -> None:
        result = svc.create(
            title="フル",
            status_id=2,
            assignee_id=3,
            start_date="2026-01-01",
            end_date="2026-03-31",
            note="備考",
        )
        assert result.is_ok
        t = result.data
        assert t.assignee_id == 3
        assert t.start_date == "2026-01-01"
        assert t.end_date == "2026-03-31"
        assert t.note == "備考"

    def test_empty_title_rejected(self, svc: TicketService) -> None:
        result = svc.create(title="  ", status_id=1)
        assert not result.is_ok
        assert "タイトル" in result.error_message

    def test_date_order_validation(self, svc: TicketService) -> None:
        result = svc.create(
            title="T", status_id=1, start_date="2026-03-31", end_date="2026-01-01"
        )
        assert not result.is_ok
        assert "開始日" in result.error_message


class TestTicketUpdate:
    def test_update_title(self, svc: TicketService) -> None:
        t = _create(svc, "Before")
        result = svc.update(t.id, "After", status_id=1)
        assert result.is_ok
        updated = svc.get_by_id(t.id)
        assert updated.title == "After"

    def test_update_nonexistent(self, svc: TicketService) -> None:
        result = svc.update(9999, "T", status_id=1)
        assert not result.is_ok


class TestTicketSoftDelete:
    def test_soft_delete(self, svc: TicketService) -> None:
        t = _create(svc)
        result = svc.soft_delete(t.id)
        assert result.is_ok
        # 削除済みは get_all に含まれない
        tickets = svc.get_all()
        assert all(tk.id != t.id for tk in tickets)

    def test_soft_delete_nonexistent(self, svc: TicketService) -> None:
        result = svc.soft_delete(9999)
        assert not result.is_ok


class TestChangeStatus:
    def test_change_status(self, svc: TicketService) -> None:
        # status_id=1 → 2 に変更（rules.db にステータスを2件登録してから実施）
        from service.status_service import StatusService
        ss = StatusService()
        ss.create("未着手")
        ss.create("完了")
        statuses = ss.get_all()
        t = _create(svc, status_id=statuses[0].id)
        result = svc.change_status(t.id, statuses[1].id)
        assert result.is_ok
        updated = svc.get_by_id(t.id)
        assert updated.status_id == statuses[1].id

    def test_change_status_invalid_status_id_returns_error(self, svc: TicketService) -> None:
        from service.status_service import StatusService
        ss = StatusService()
        ss.create("未着手")
        statuses = ss.get_all()
        t = _create(svc, status_id=statuses[0].id)
        result = svc.change_status(t.id, 99999)
        assert not result.is_ok


class TestTagValues:
    def test_create_with_tags(self, svc: TicketService) -> None:
        result = svc.create(
            title="T", status_id=1, tag_values={1: "alpha", 2: "beta"}
        )
        assert result.is_ok
        tvs = svc.get_tag_values(result.data.id)
        assert len(tvs) == 2
        values = {tv.tag_def_id: tv.value for tv in tvs}
        assert values[1] == "alpha"
        assert values[2] == "beta"

    def test_empty_tag_value_skipped(self, svc: TicketService) -> None:
        result = svc.create(title="T", status_id=1, tag_values={1: "", 2: "val"})
        assert result.is_ok
        tvs = svc.get_tag_values(result.data.id)
        assert len(tvs) == 1
        assert tvs[0].value == "val"

    def test_update_replaces_tags(self, svc: TicketService) -> None:
        t = _create(svc, tag_values={1: "old"})
        svc.update(t.id, "T", status_id=1, tag_values={1: "new"})
        tvs = svc.get_tag_values(t.id)
        assert tvs[0].value == "new"


# ---------------------------------------------------------------------------
# 5.2 フィルター機能
# ---------------------------------------------------------------------------


class TestAssigneeFilter:
    def test_filter_by_assignee(self, svc: TicketService) -> None:
        _create(svc, "A", assignee_id=1)
        _create(svc, "B", assignee_id=2)
        _create(svc, "C", assignee_id=None)

        result = svc.get_all(FilterCondition(assignee_ids=[1]))
        assert len(result) == 1
        assert result[0].title == "A"

    def test_multi_assignee_or(self, svc: TicketService) -> None:
        _create(svc, "A", assignee_id=1)
        _create(svc, "B", assignee_id=2)
        _create(svc, "C", assignee_id=3)

        result = svc.get_all(FilterCondition(assignee_ids=[1, 2]))
        assert len(result) == 2

    def test_empty_assignee_ids_returns_all(self, svc: TicketService) -> None:
        _create(svc, assignee_id=1)
        _create(svc, assignee_id=2)
        result = svc.get_all(FilterCondition(assignee_ids=[]))
        assert len(result) == 2


class TestStatusFilter:
    def test_filter_by_status(self, svc: TicketService) -> None:
        _create(svc, status_id=1)
        _create(svc, status_id=2)
        result = svc.get_all(FilterCondition(status_ids=[1]))
        assert len(result) == 1
        assert result[0].status_id == 1

    def test_multi_status_or(self, svc: TicketService) -> None:
        _create(svc, status_id=1)
        _create(svc, status_id=2)
        _create(svc, status_id=3)
        result = svc.get_all(FilterCondition(status_ids=[1, 3]))
        assert len(result) == 2


class TestTagFilter:
    def test_and_filter(self, svc: TicketService) -> None:
        """AND フィルター: 条件を満たすチケットのみ返す。"""
        t1 = _create(svc, "T1", tag_values={1: "alpha"})
        t2 = _create(svc, "T2", tag_values={1: "beta"})

        result = svc.get_all(
            FilterCondition(tag_filters=[TagFilter(1, "alpha", "and")])
        )
        ids = [t.id for t in result]
        assert t1.id in ids
        assert t2.id not in ids

    def test_or_filter(self, svc: TicketService) -> None:
        """OR フィルター: どれか一つ満たせば返す。"""
        t1 = _create(svc, "T1", tag_values={1: "alpha"})
        t2 = _create(svc, "T2", tag_values={2: "beta"})
        t3 = _create(svc, "T3")

        result = svc.get_all(
            FilterCondition(
                tag_filters=[
                    TagFilter(1, "alpha", "or"),
                    TagFilter(2, "beta", "or"),
                ]
            )
        )
        ids = [t.id for t in result]
        assert t1.id in ids
        assert t2.id in ids
        assert t3.id not in ids

    def test_not_filter(self, svc: TicketService) -> None:
        """NOT フィルター: 条件を満たさないチケットのみ返す。"""
        t1 = _create(svc, "T1", tag_values={1: "alpha"})
        t2 = _create(svc, "T2", tag_values={1: "beta"})

        result = svc.get_all(
            FilterCondition(tag_filters=[TagFilter(1, "alpha", "not")])
        )
        ids = [t.id for t in result]
        assert t1.id not in ids
        assert t2.id in ids

    def test_partial_match(self, svc: TicketService) -> None:
        """タグ値は部分一致（LIKE %value%）で検索する。"""
        t = _create(svc, tag_values={1: "アルファ機種"})
        result = svc.get_all(
            FilterCondition(tag_filters=[TagFilter(1, "アルファ", "and")])
        )
        assert any(tk.id == t.id for tk in result)


class TestDateFilter:
    def test_start_date_from(self, svc: TicketService) -> None:
        _create(svc, start_date="2026-01-01")
        _create(svc, start_date="2026-06-01")
        result = svc.get_all(
            FilterCondition(start_date_from=date(2026, 3, 1))
        )
        assert len(result) == 1
        assert result[0].start_date == "2026-06-01"

    def test_end_date_to(self, svc: TicketService) -> None:
        _create(svc, end_date="2026-01-31")
        _create(svc, end_date="2026-12-31")
        result = svc.get_all(
            FilterCondition(end_date_to=date(2026, 3, 1))
        )
        assert len(result) == 1
        assert result[0].end_date == "2026-01-31"

    def test_combined_date_range(self, svc: TicketService) -> None:
        _create(svc, start_date="2026-01-01", end_date="2026-01-31")
        _create(svc, start_date="2026-03-01", end_date="2026-03-31")
        result = svc.get_all(
            FilterCondition(
                start_date_from=date(2026, 2, 1),
                start_date_to=date(2026, 4, 1),
            )
        )
        assert len(result) == 1
        assert result[0].start_date == "2026-03-01"


class TestCombinedFilter:
    def test_status_and_assignee(self, svc: TicketService) -> None:
        _create(svc, status_id=1, assignee_id=1)
        _create(svc, status_id=2, assignee_id=1)
        _create(svc, status_id=1, assignee_id=2)

        result = svc.get_all(
            FilterCondition(status_ids=[1], assignee_ids=[1])
        )
        assert len(result) == 1

    def test_no_filter_returns_all(self, svc: TicketService) -> None:
        _create(svc)
        _create(svc)
        assert len(svc.get_all()) == 2

    def test_deleted_excluded_by_default(self, svc: TicketService) -> None:
        t = _create(svc)
        svc.soft_delete(t.id)
        assert len(svc.get_all()) == 0
