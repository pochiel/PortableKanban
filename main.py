"""main.py - PortableKanban エントリーポイント・AppController。

AppController がアプリのライフサイクルと画面遷移を管理する。
View は AppController を navigator として受け取り、
show_*() メソッドで遷移を依頼する。
"""

import sys

from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget


class AppController:
    """アプリ起動・QApplicationの初期化・画面管理を担当する。

    View に注入する navigator として機能する。
    画面遷移メソッド:
      show_startup()                 - SCR-001 起動画面
      show_initial_setup(folder)     - SCR-002 初期設定画面
      show_kanban_board(role)        - SCR-004 カンバンボード
      show_ticket_detail(ticket_id)  - SCR-005 チケット詳細（Noneで新規）
      show_kanban_board_back()       - SCR-005 → SCR-004 戻り
      show_kanban_settings()         - SCR-003 設定（別ウィンドウ）
    """

    def __init__(self) -> None:
        self._app = QApplication(sys.argv)
        self._app.setApplicationName("PortableKanban")

        self._window = QMainWindow()
        self._window.setWindowTitle("PortableKanban")
        self._window.setMinimumSize(900, 600)

        self._stack = QStackedWidget()
        self._window.setCentralWidget(self._stack)

        # 現在ログイン中のロール・DBフォルダ
        self._role: str = ""
        self._db_folder: str = ""

        # カンバンボードビューの参照（チケット詳細から戻るために保持）
        self._kanban_view = None

        # 別ウィンドウ（複数同時表示しない）
        self._kanban_settings_window = None
        self._gantt_window = None
        self._prompt_window = None
        self._import_window = None
        self._export_window = None
        self._last_export_filter = None

        # ウィンドウ閉じるイベントでカンバンボードのクリーンアップを実行
        self._window.closeEvent = self._on_window_close

    # ------------------------------------------------------------------
    # 起動
    # ------------------------------------------------------------------

    def run(self) -> int:
        """アプリを起動する。終了コードを返す。"""
        self.show_startup()
        self._window.show()
        return self._app.exec()

    # ------------------------------------------------------------------
    # 画面遷移（navigator インターフェース）
    # ------------------------------------------------------------------

    def show_startup(self) -> None:
        """SCR-001 起動画面を表示する。"""
        from presentation.views.startup_view import StartupView

        self._kanban_view = None
        view = StartupView(navigator=self)
        self._switch_to(view)
        self._window.setWindowTitle("PortableKanban - 起動")

    def show_initial_setup(self, folder_path: str) -> None:
        """SCR-002 初期設定画面を表示する。"""
        from presentation.views.initial_setup_view import InitialSetupView

        view = InitialSetupView(folder_path=folder_path, navigator=self)
        self._switch_to(view)
        self._window.setWindowTitle("PortableKanban - 初期設定")

    def show_kanban_board(self, role: str) -> None:
        """SCR-004 カンバンボード画面を表示する。

        ログイン直後に呼ばれる。db_folder は ConfigService から読む
        （StartupPresenter が save_last_db_path を先に実行済み）。
        """
        from service.config_service import ConfigService
        from presentation.views.kanban_board_view import KanbanBoardView

        self._role = role
        self._db_folder = ConfigService().get_last_db_path() or ""

        view = KanbanBoardView(role=role, db_folder=self._db_folder, navigator=self)
        self._kanban_view = view
        self._switch_to(view)
        self._window.setWindowTitle(f"PortableKanban - カンバンボード [{role}]")

    def show_ticket_detail(self, ticket_id: int | None) -> None:
        """SCR-005 チケット詳細・編集画面を表示する。

        ticket_id=None なら新規作成モード。
        カンバンボードビューは破棄せずスタックに保持する。
        """
        from presentation.views.ticket_detail_view import TicketDetailView

        view = TicketDetailView(ticket_id=ticket_id, role=self._role, navigator=self)
        # カンバンボードを残したままスタックに積む
        self._stack.addWidget(view)
        self._stack.setCurrentWidget(view)
        title = "チケット詳細" if ticket_id else "新規チケット"
        self._window.setWindowTitle(f"PortableKanban - {title}")

    def show_kanban_board_back(self) -> None:
        """SCR-005 からカンバンボードへ戻る。

        チケット詳細ウィジェットをスタックから除去し、
        カンバンボードを最新データで再描画する。
        """
        current = self._stack.currentWidget()
        if current is self._kanban_view:
            return  # すでにカンバンボード
        self._stack.removeWidget(current)
        current.deleteLater()
        if self._kanban_view is not None:
            self._stack.setCurrentWidget(self._kanban_view)
            self._kanban_view.refresh()
        self._window.setWindowTitle(
            f"PortableKanban - カンバンボード [{self._role}]"
        )

    def show_kanban_settings(self) -> None:
        """SCR-003 カンバン設定画面を別ウィンドウで表示する。"""
        from presentation.views.kanban_settings_view import KanbanSettingsView

        if (
            self._kanban_settings_window is None
            or not self._kanban_settings_window.isVisible()
        ):
            self._kanban_settings_window = KanbanSettingsView()
            self._hook_refresh_on_close(self._kanban_settings_window)
        self._kanban_settings_window.show()
        self._kanban_settings_window.raise_()

    def show_gantt(self) -> None:
        """SCR-006 ガントチャート出力画面を別ウィンドウで表示する。"""
        from presentation.views.gantt_view import GanttView

        if self._gantt_window is None or not self._gantt_window.isVisible():
            self._gantt_window = GanttView()
        self._gantt_window.show()
        self._gantt_window.raise_()

    def show_prompt(self) -> None:
        """SCR-009 プロンプト生成画面を別ウィンドウで表示する。"""
        from presentation.views.prompt_view import PromptView

        if self._prompt_window is None or not self._prompt_window.isVisible():
            self._prompt_window = PromptView()
        self._prompt_window.show()
        self._prompt_window.raise_()

    def show_import(self) -> None:
        """SCR-008 進捗取り込み画面を別ウィンドウで表示する。"""
        from presentation.views.import_view import ImportView

        # 取り込みは毎回フレッシュに開く
        self._import_window = ImportView()
        self._hook_refresh_on_close(self._import_window)
        self._import_window.show()
        self._import_window.raise_()

    def show_export(self) -> None:
        """SCR-007 テキストエクスポート画面を別ウィンドウで表示する。"""
        from presentation.views.export_view import ExportView

        if self._export_window is None or not self._export_window.isVisible():
            self._export_window = ExportView(initial_filter=self._last_export_filter)
            self._hook_refresh_on_close(self._export_window)

            from PyQt6.QtCore import QEvent, QObject
            controller = self

            class _SaveFilterHook(QObject):
                def eventFilter(self, obj, event):
                    if event.type() == QEvent.Type.Close:
                        controller._last_export_filter = obj.get_current_filter()
                    return False

            hook = _SaveFilterHook(self._export_window)
            self._export_window.installEventFilter(hook)
            self._export_window._save_filter_hook = hook
        self._export_window.show()
        self._export_window.raise_()

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------

    def show_ticket_detail_replace(self, ticket_id: int) -> None:
        """現在のチケット詳細を別のチケット詳細に置き換える（コピー後の遷移用）。"""
        from presentation.views.ticket_detail_view import TicketDetailView

        current = self._stack.currentWidget()
        if current is not self._kanban_view:
            self._stack.removeWidget(current)
            current.deleteLater()

        view = TicketDetailView(ticket_id=ticket_id, role=self._role, navigator=self)
        self._stack.addWidget(view)
        self._stack.setCurrentWidget(view)
        self._window.setWindowTitle("PortableKanban - チケット詳細")

    def _hook_refresh_on_close(self, window) -> None:
        """別ウィンドウが閉じられたときにカンバンボードを自動更新するフックを設定する。"""
        from PyQt6.QtCore import QEvent, QObject, QTimer

        controller = self

        class _CloseHook(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.Close:
                    if controller._kanban_view is not None:
                        QTimer.singleShot(0, controller._kanban_view.refresh)
                return False

        hook = _CloseHook(window)
        window.installEventFilter(hook)
        window._close_hook = hook  # Python参照を保持してGC防止

    def _switch_to(self, widget: object) -> None:
        """QStackedWidget の全ページをクリアして新しいウィジェットに差し替える。"""
        while self._stack.count() > 0:
            old = self._stack.widget(0)
            self._stack.removeWidget(old)
            old.deleteLater()

        self._stack.addWidget(widget)
        self._stack.setCurrentWidget(widget)

    def _on_window_close(self, event) -> None:
        """メインウィンドウ終了時にカンバンボードのリソースを解放する。"""
        if self._kanban_view is not None:
            self._kanban_view.cleanup()
        event.accept()


def main() -> None:
    controller = AppController()
    sys.exit(controller.run())


if __name__ == "__main__":
    main()
