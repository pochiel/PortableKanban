"""presentation/views/startup_view.py - SCR-001 起動画面の View。"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from presentation.presenters.startup_presenter import StartupPresenter


class StartupView(QWidget):
    """SCR-001 起動画面。

    DBファイルの場所を指定してログイン、または新規作成を行う。
    navigator は AppController を想定する。go_to_* メソッドで画面遷移を依頼する。
    """

    def __init__(self, navigator: object | None = None) -> None:
        super().__init__()
        self._navigator = navigator
        self._presenter = StartupPresenter(view=self)
        self._build_ui()
        self._presenter.on_load()

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setWindowTitle("PortableKanban - 起動")
        self.setMinimumWidth(460)

        # DBパス欄
        path_layout = QHBoxLayout()
        self._path_label = QLabel("DBフォルダ:")
        self._path_display = QLineEdit()
        self._path_display.setReadOnly(True)
        self._path_display.setPlaceholderText("フォルダを選択してください")
        self._folder_btn = QPushButton("フォルダを選択")
        self._folder_btn.clicked.connect(self._on_folder_btn_clicked)
        path_layout.addWidget(self._path_label)
        path_layout.addWidget(self._path_display, stretch=1)
        path_layout.addWidget(self._folder_btn)

        # パスワード欄
        pw_layout = QHBoxLayout()
        pw_label = QLabel("パスワード:")
        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.setPlaceholderText("未入力でmemberとしてログイン")
        self._password_input.returnPressed.connect(self._on_login_clicked)
        pw_layout.addWidget(pw_label)
        pw_layout.addWidget(self._password_input, stretch=1)

        # ボタン行
        btn_layout = QHBoxLayout()
        self._login_btn = QPushButton("ログイン")
        self._login_btn.setEnabled(False)
        self._login_btn.setDefault(True)
        self._login_btn.clicked.connect(self._on_login_clicked)
        self._new_project_btn = QPushButton("新規作成")
        self._new_project_btn.clicked.connect(self._on_new_project_clicked)
        btn_layout.addStretch()
        btn_layout.addWidget(self._new_project_btn)
        btn_layout.addWidget(self._login_btn)

        # エラーメッセージ
        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: red;")
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.setWordWrap(True)

        # 全体レイアウト
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addLayout(path_layout)
        layout.addLayout(pw_layout)
        layout.addLayout(btn_layout)
        layout.addWidget(self._error_label)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # イベントハンドラ（Presenter を呼ぶだけ）
    # ------------------------------------------------------------------

    def _on_folder_btn_clicked(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "DBフォルダを選択")
        self._presenter.on_folder_selected(folder)

    def _on_login_clicked(self) -> None:
        self._presenter.on_login(password=self._password_input.text())

    def _on_new_project_clicked(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "新規作成先フォルダを選択")
        self._presenter.on_new_project(folder)

    # ------------------------------------------------------------------
    # Presenter から呼ばれるメソッド
    # ------------------------------------------------------------------

    def set_db_path(self, path: str) -> None:
        self._path_display.setText(path)

    def set_login_enabled(self, enabled: bool) -> None:
        self._login_btn.setEnabled(enabled)

    def show_error(self, message: str) -> None:
        self._error_label.setText(message)

    def clear_error(self) -> None:
        self._error_label.clear()

    def go_to_initial_setup(self, folder_path: str) -> None:
        if self._navigator:
            self._navigator.show_initial_setup(folder_path)

    def go_to_kanban_board(self, role: str) -> None:
        if self._navigator:
            self._navigator.show_kanban_board(role)
