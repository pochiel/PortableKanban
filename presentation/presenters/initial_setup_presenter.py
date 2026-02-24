"""presentation/presenters/initial_setup_presenter.py - SCR-002 初期設定画面の Presenter。"""

from service.config_service import ConfigService
from service.setup_service import SetupService


class InitialSetupPresenter:
    """初期設定画面（SCR-002）のビジネスロジック仲介。

    新規プロジェクト（DBファイル一式）の作成を制御する。
    """

    def __init__(self, view: object, folder_path: str) -> None:
        self._view = view
        self._folder_path = folder_path
        self._config_service = ConfigService()

    def on_create(self, prefix: str, password: str, confirm: str) -> None:
        """作成ボタン押下時の処理。"""
        result = SetupService().create_project(
            folder_path=self._folder_path,
            prefix=prefix,
            password=password,
            confirm=confirm,
        )
        if not result.is_ok:
            self._view.show_error(result.error_message)
            return

        self._config_service.save_last_db_path(self._folder_path)
        self._view.go_to_kanban_board()

    def on_cancel(self) -> None:
        """キャンセルボタン押下時の処理。"""
        self._view.go_to_startup()
