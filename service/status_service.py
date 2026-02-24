"""service/status_service.py - ステータス定義の CRUD・表示順管理。"""

from domain.service_result import ServiceResult
from domain.status import Status
from repository.settings_repository import SettingsRepository
from repository.status_repository import StatusRepository

_MAX_NAME_LENGTH = 50


class StatusService:
    """ステータス定義の CRUD と表示順管理を担当する。"""

    def __init__(
        self,
        status_repo: StatusRepository | None = None,
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        self._repo = status_repo or StatusRepository()
        self._settings_repo = settings_repo or SettingsRepository()

    def get_all(self) -> list[Status]:
        """全ステータスを display_order 昇順で返す。"""
        return self._repo.find_all()

    def create(self, name: str) -> ServiceResult:
        """ステータスを末尾に追加する。

        display_order は現在の最大値 + 1 を自動設定する。
        """
        error = self._validate_name(name)
        if error:
            return ServiceResult.err(error)

        max_order = self._repo.get_max_display_order()
        status = Status(name=name.strip(), display_order=max_order + 1)
        saved = self._repo.save(status)
        return ServiceResult.ok(data=saved)

    def update(self, status_id: int, name: str) -> ServiceResult:
        """ステータス名を更新する。"""
        existing = self._repo.find_by_id(status_id)
        if existing is None:
            return ServiceResult.err(f"ステータスID {status_id} が見つかりません。")

        error = self._validate_name(name)
        if error:
            return ServiceResult.err(error)

        existing.name = name.strip()
        saved = self._repo.save(existing)
        return ServiceResult.ok(data=saved)

    def delete(self, status_id: int) -> ServiceResult:
        """ステータスを削除する。使用中チケットが存在する場合は失敗。"""
        existing = self._repo.find_by_id(status_id)
        if existing is None:
            return ServiceResult.err(f"ステータスID {status_id} が見つかりません。")

        if self._repo.is_in_use(status_id):
            return ServiceResult.err(
                "このステータスは使用中のチケットが存在するため削除できません。"
            )

        # default_hidden_status_ids から除外する
        self._remove_from_hidden(status_id)

        self._repo.delete(status_id)
        return ServiceResult.ok()

    def reorder(self, status_id: int, direction: str) -> ServiceResult:
        """ステータスの表示順を1つ上または下に移動する。

        Args:
            direction: "up"（左に移動）または "down"（右に移動）。
        """
        if direction not in ("up", "down"):
            return ServiceResult.err("direction は 'up' または 'down' で指定してください。")

        statuses = self._repo.find_all()
        ids = [s.id for s in statuses]

        if status_id not in ids:
            return ServiceResult.err(f"ステータスID {status_id} が見つかりません。")

        idx = ids.index(status_id)

        if direction == "up" and idx == 0:
            return ServiceResult.err("すでに先頭のステータスです。")
        if direction == "down" and idx == len(statuses) - 1:
            return ServiceResult.err("すでに末尾のステータスです。")

        swap_idx = idx - 1 if direction == "up" else idx + 1
        # display_order を交換する
        a, b = statuses[idx], statuses[swap_idx]
        a.display_order, b.display_order = b.display_order, a.display_order
        self._repo.save(a)
        self._repo.save(b)
        return ServiceResult.ok()

    def get_default_hidden_ids(self) -> list[int]:
        """デフォルト非表示ステータスIDリストを返す。"""
        value = self._settings_repo.get("default_hidden_status_ids")
        if not value:
            return []
        try:
            return [int(x.strip()) for x in value.split(",") if x.strip()]
        except ValueError:
            return []

    def update_default_hidden(self, status_ids: list[int]) -> ServiceResult:
        """デフォルト非表示ステータスIDリストを保存する。"""
        value = ",".join(str(i) for i in status_ids)
        self._settings_repo.set("default_hidden_status_ids", value)
        return ServiceResult.ok()

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_name(name: str) -> str:
        if not name.strip():
            return "ステータス名を入力してください。"
        if len(name.strip()) > _MAX_NAME_LENGTH:
            return f"ステータス名は{_MAX_NAME_LENGTH}文字以内で入力してください。"
        return ""

    def _remove_from_hidden(self, status_id: int) -> None:
        """default_hidden_status_ids から指定IDを除去する。"""
        hidden = self.get_default_hidden_ids()
        if status_id in hidden:
            hidden.remove(status_id)
            self.update_default_hidden(hidden)
