"""presentation/presenters/startup_presenter.py - SCR-001 起動画面の Presenter。"""

from service.auth_service import AuthService
from service.config_service import ConfigService
from service.setup_service import SetupService


class StartupPresenter:
    """起動画面（SCR-001）のビジネスロジック仲介。

    DBパスの確認・manager認証・memberログインを制御する。
    """

    def __init__(self, view: object) -> None:
        self._view = view
        self._auth_service = AuthService()
        self._config_service = ConfigService()
        self._selected_folder: str = ""

    def on_load(self) -> None:
        """画面表示時の初期化。前回パスを読み込んでフォームにセットする。"""
        last_path = self._config_service.get_last_db_path()
        if last_path:
            self._selected_folder = last_path
            self._view.set_db_path(last_path)
            self._view.set_login_enabled(True)

    def on_folder_selected(self, folder_path: str) -> None:
        """フォルダ選択ダイアログで選択された後に呼ばれる。"""
        if not folder_path:
            return
        self._selected_folder = folder_path
        self._view.set_db_path(folder_path)
        self._view.set_login_enabled(True)
        self._view.clear_error()

    def on_login(self, password: str) -> None:
        """ログインボタン押下時の処理。"""
        if not self._selected_folder:
            self._view.show_error("フォルダを選択してください。")
            return

        # 既存プロジェクトを開く
        open_result = SetupService.open_project(self._selected_folder)
        if not open_result.is_ok:
            self._view.show_error(open_result.error_message)
            return

        # パスワード未入力 → memberとしてログイン
        if not password:
            self._config_service.save_last_db_path(self._selected_folder)
            self._view.go_to_kanban_board("member")
            return

        # パスワードあり → manager認証
        auth_result = self._auth_service.authenticate(password)
        if not auth_result.is_ok:
            self._view.show_error(auth_result.error_message)
            return

        self._config_service.save_last_db_path(self._selected_folder)
        self._view.go_to_kanban_board("manager")

    def on_new_project(self, folder_path: str) -> None:
        """新規作成用フォルダが選択された後に呼ばれる。"""
        if not folder_path:
            return
        self._selected_folder = folder_path
        self._view.go_to_initial_setup(folder_path)
