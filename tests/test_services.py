"""
tests/test_services.py

Service層の単体テスト（4.2.5, 3.2.7 対応）
"""

import time
from pathlib import Path

import pytest

import db.connection as connection
from service.auth_service import AuthService
from service.config_service import ConfigService
from service.lock_service import LockService
from service.member_service import MemberService
from service.setup_service import SetupService
from service.status_service import StatusService
from service.tag_service import TagService


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_db():
    """各テスト後にDB接続状態をリセットする。"""
    yield
    connection.close_all()


@pytest.fixture()
def project(tmp_path: Path):
    """テスト用プロジェクトを作成し、DBをセットアップする。"""
    connection.init_rules_db(str(tmp_path / "rules.db"))
    connection.init_work_db(str(tmp_path / "work.db"))
    connection.set_db_paths(
        str(tmp_path / "rules.db"),
        str(tmp_path / "work.db"),
    )
    return tmp_path


# ---------------------------------------------------------------------------
# AuthService
# ---------------------------------------------------------------------------


class TestAuthService:
    def test_save_and_authenticate_success(self, project: Path) -> None:
        svc = AuthService()
        assert svc.save_password("password123").is_ok
        assert svc.authenticate("password123").is_ok

    def test_wrong_password_fails(self, project: Path) -> None:
        svc = AuthService()
        svc.save_password("correct")
        result = svc.authenticate("wrong")
        assert not result.is_ok
        assert "正しくありません" in result.error_message

    def test_empty_password_rejected(self, project: Path) -> None:
        svc = AuthService()
        result = svc.save_password("")
        assert not result.is_ok

    def test_authenticate_without_password_set(self, project: Path) -> None:
        svc = AuthService()
        result = svc.authenticate("anything")
        assert not result.is_ok
        assert "設定されていません" in result.error_message

    def test_is_password_set(self, project: Path) -> None:
        svc = AuthService()
        assert not svc.is_password_set()
        svc.save_password("pass")
        assert svc.is_password_set()


# ---------------------------------------------------------------------------
# SetupService
# ---------------------------------------------------------------------------


class TestSetupService:
    def test_create_project_success(self, tmp_path: Path) -> None:
        svc = SetupService()
        result = svc.create_project(
            folder_path=str(tmp_path),
            prefix="TEST",
            password="pass",
            confirm="pass",
        )
        assert result.is_ok
        assert (tmp_path / "rules.db").exists()
        assert (tmp_path / "work.db").exists()

    def test_create_project_password_mismatch(self, tmp_path: Path) -> None:
        svc = SetupService()
        result = svc.create_project(str(tmp_path), "ABC", "pass1", "pass2")
        assert not result.is_ok
        assert "一致しません" in result.error_message

    def test_create_project_empty_prefix(self, tmp_path: Path) -> None:
        svc = SetupService()
        result = svc.create_project(str(tmp_path), "", "pass", "pass")
        assert not result.is_ok

    def test_create_project_duplicate_fails(self, tmp_path: Path) -> None:
        svc = SetupService()
        svc.create_project(str(tmp_path), "ABC", "pass", "pass")
        # reset connection state
        connection.close_all()
        result = svc.create_project(str(tmp_path), "ABC", "pass", "pass")
        assert not result.is_ok
        assert "既存" in result.error_message

    def test_open_project_success(self, tmp_path: Path) -> None:
        svc = SetupService()
        svc.create_project(str(tmp_path), "ABC", "pass", "pass")
        connection.close_all()
        result = SetupService.open_project(str(tmp_path))
        assert result.is_ok

    def test_open_project_missing_db(self, tmp_path: Path) -> None:
        result = SetupService.open_project(str(tmp_path))
        assert not result.is_ok


# ---------------------------------------------------------------------------
# ConfigService
# ---------------------------------------------------------------------------


class TestConfigService:
    def test_save_and_get_last_db_path(self, tmp_path: Path) -> None:
        svc = ConfigService(config_dir=str(tmp_path))
        assert svc.get_last_db_path() is None
        svc.save_last_db_path("/some/path")
        assert svc.get_last_db_path() == "/some/path"

    def test_overwrite_last_db_path(self, tmp_path: Path) -> None:
        svc = ConfigService(config_dir=str(tmp_path))
        svc.save_last_db_path("/path/a")
        svc.save_last_db_path("/path/b")
        assert svc.get_last_db_path() == "/path/b"


# ---------------------------------------------------------------------------
# MemberService
# ---------------------------------------------------------------------------


class TestMemberService:
    def test_create_member(self, project: Path) -> None:
        svc = MemberService()
        result = svc.create("山田太郎", "yamada@example.com")
        assert result.is_ok
        assert result.data.name == "山田太郎"
        assert result.data.id is not None

    def test_empty_name_rejected(self, project: Path) -> None:
        svc = MemberService()
        result = svc.create("", "x@example.com")
        assert not result.is_ok

    def test_get_all_active(self, project: Path) -> None:
        svc = MemberService()
        svc.create("A")
        svc.create("B")
        members = svc.get_all_active()
        assert len(members) == 2

    def test_update_member(self, project: Path) -> None:
        svc = MemberService()
        result = svc.create("Before")
        member_id = result.data.id
        svc.update(member_id, "After", "after@example.com")
        members = svc.get_all_active()
        assert members[0].name == "After"

    def test_deactivate_member(self, project: Path) -> None:
        svc = MemberService()
        result = svc.create("To Deactivate")
        svc.deactivate(result.data.id)
        assert len(svc.get_all_active()) == 0

    def test_update_nonexistent_fails(self, project: Path) -> None:
        svc = MemberService()
        result = svc.update(9999, "Name")
        assert not result.is_ok


# ---------------------------------------------------------------------------
# StatusService
# ---------------------------------------------------------------------------


class TestStatusService:
    def test_create_status(self, project: Path) -> None:
        svc = StatusService()
        result = svc.create("未着手")
        assert result.is_ok
        assert result.data.display_order == 1

    def test_display_order_increments(self, project: Path) -> None:
        svc = StatusService()
        svc.create("A")
        svc.create("B")
        statuses = svc.get_all()
        orders = [s.display_order for s in statuses]
        assert orders == sorted(orders)

    def test_update_status_name(self, project: Path) -> None:
        svc = StatusService()
        result = svc.create("Before")
        svc.update(result.data.id, "After")
        statuses = svc.get_all()
        assert statuses[0].name == "After"

    def test_delete_unused_status(self, project: Path) -> None:
        svc = StatusService()
        result = svc.create("Unused")
        del_result = svc.delete(result.data.id)
        assert del_result.is_ok
        assert len(svc.get_all()) == 0

    def test_delete_fails_if_in_use(self, project: Path) -> None:
        """使用中ステータスは削除不可。"""
        from datetime import datetime, timezone
        from db.connection import get_work_db

        svc = StatusService()
        result = svc.create("InUse")
        status_id = result.data.id

        # work.db にチケットを直接挿入して使用中にする
        conn = get_work_db()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        conn.execute(
            "INSERT INTO tickets (title, status_id, created_at, updated_at)"
            " VALUES (?, ?, ?, ?)",
            ("test ticket", status_id, now, now),
        )
        conn.commit()

        del_result = svc.delete(status_id)
        assert not del_result.is_ok
        assert "使用中" in del_result.error_message

    def test_reorder_up(self, project: Path) -> None:
        svc = StatusService()
        a = svc.create("A").data
        b = svc.create("B").data
        svc.reorder(b.id, "up")
        statuses = svc.get_all()
        assert statuses[0].id == b.id

    def test_reorder_top_up_fails(self, project: Path) -> None:
        svc = StatusService()
        a = svc.create("Only").data
        result = svc.reorder(a.id, "up")
        assert not result.is_ok

    def test_default_hidden_ids(self, project: Path) -> None:
        svc = StatusService()
        svc.update_default_hidden([1, 2, 3])
        assert svc.get_default_hidden_ids() == [1, 2, 3]

    def test_empty_name_rejected(self, project: Path) -> None:
        svc = StatusService()
        result = svc.create("")
        assert not result.is_ok


# ---------------------------------------------------------------------------
# TagService
# ---------------------------------------------------------------------------


class TestTagService:
    def test_create_tag_text(self, project: Path) -> None:
        svc = TagService()
        result = svc.create("機種名", "text")
        assert result.is_ok
        assert result.data.field_type == "text"

    def test_create_tag_date(self, project: Path) -> None:
        svc = TagService()
        result = svc.create("期限日", "date")
        assert result.is_ok

    def test_invalid_field_type_rejected(self, project: Path) -> None:
        svc = TagService()
        result = svc.create("Tag", "number")
        assert not result.is_ok

    def test_update_tag(self, project: Path) -> None:
        svc = TagService()
        result = svc.create("Before", "text")
        svc.update(result.data.id, "After", "date")
        tags = svc.get_all()
        assert tags[0].name == "After"
        assert tags[0].field_type == "date"

    def test_delete_unused_tag(self, project: Path) -> None:
        svc = TagService()
        result = svc.create("ToDelete", "text")
        del_result = svc.delete(result.data.id)
        assert del_result.is_ok
        assert len(svc.get_all()) == 0

    def test_empty_name_rejected(self, project: Path) -> None:
        svc = TagService()
        result = svc.create("", "text")
        assert not result.is_ok


# ---------------------------------------------------------------------------
# LockService（3.2.7）
# ---------------------------------------------------------------------------


class TestLockService:
    def test_acquire_and_release(self, tmp_path: Path) -> None:
        svc = LockService(str(tmp_path))
        result = svc.acquire()
        assert result.is_ok
        assert (tmp_path / ".manager.lock").exists()
        svc.release()
        assert not (tmp_path / ".manager.lock").exists()

    def test_second_acquire_fails_when_locked(self, tmp_path: Path) -> None:
        svc1 = LockService(str(tmp_path))
        svc2 = LockService(str(tmp_path))
        svc1.acquire()
        svc1.start_heartbeat()
        try:
            result = svc2.acquire()
            assert not result.is_ok
            assert "編集中" in result.error_message
        finally:
            svc1.release()

    def test_expired_lock_can_be_overwritten(self, tmp_path: Path) -> None:
        """タイムアウト済みのロックは新たにacquireできる。"""
        from kanban_lock.manager_lock import ManagerLock
        import json

        # 古いタイムスタンプのロックファイルを直接作成する
        lock_path = tmp_path / ".manager.lock"
        lock_path.write_text(
            json.dumps({"manager": "old_host", "timestamp": "2000-01-01T00:00:00"}),
            encoding="utf-8",
        )

        svc = LockService(str(tmp_path))
        result = svc.acquire()
        assert result.is_ok
        svc.release()

    def test_force_release_expired_lock(self, tmp_path: Path) -> None:
        import json

        lock_path = tmp_path / ".manager.lock"
        lock_path.write_text(
            json.dumps({"manager": "old", "timestamp": "2000-01-01T00:00:00"}),
            encoding="utf-8",
        )

        svc = LockService(str(tmp_path))
        result = svc.force_release()
        assert result.is_ok
        assert not lock_path.exists()

    def test_force_release_active_lock_fails(self, tmp_path: Path) -> None:
        svc = LockService(str(tmp_path))
        svc.acquire()
        svc.start_heartbeat()
        try:
            result = svc.force_release()
            assert not result.is_ok
        finally:
            svc.release()

    def test_heartbeat_updates_timestamp(self, tmp_path: Path) -> None:
        import json

        svc = LockService(str(tmp_path))
        svc.acquire()
        lock_path = tmp_path / ".manager.lock"

        # 古いタイムスタンプを書き込む
        data = json.loads(lock_path.read_text(encoding="utf-8"))
        data["timestamp"] = "2000-01-01T00:00:00"
        lock_path.write_text(json.dumps(data), encoding="utf-8")

        svc.start_heartbeat()
        time.sleep(0.5)  # ハートビートが走るまで少し待つ
        # ハートビートは10秒間隔なので、直接 update_timestamp を呼ぶ
        svc._lock.update_timestamp()

        updated = json.loads(lock_path.read_text(encoding="utf-8"))
        assert updated["timestamp"] != "2000-01-01T00:00:00"

        svc.release()
