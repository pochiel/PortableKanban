"""presentation/views/initial_setup_view.py - SCR-002 初期設定画面の View。"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from presentation.presenters.initial_setup_presenter import InitialSetupPresenter


class InitialSetupView(QWidget):
    """SCR-002 初期設定画面。

    新規作成時のみ表示する。プレフィックス・パスワードを設定してDBを作成する。
    """

    def __init__(self, folder_path: str, navigator: object | None = None) -> None:
        super().__init__()
        self._navigator = navigator
        self._presenter = InitialSetupPresenter(view=self, folder_path=folder_path)
        self._build_ui(folder_path)

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _build_ui(self, folder_path: str) -> None:
        self.setWindowTitle("PortableKanban - 初期設定")
        self.setMinimumWidth(440)

        # フォームレイアウト
        form = QFormLayout()
        form.setSpacing(10)

        # 保存先パス（読み取り専用）
        path_display = QLineEdit(folder_path)
        path_display.setReadOnly(True)
        form.addRow("保存先フォルダ:", path_display)

        # プレフィックス
        self._prefix_input = QLineEdit()
        self._prefix_input.setPlaceholderText("例: ABC（必須）")
        self._prefix_input.setMaxLength(10)
        self._prefix_input.textChanged.connect(self._update_create_btn_state)
        form.addRow("チケットプレフィックス:", self._prefix_input)

        # パスワード
        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.setPlaceholderText("必須")
        self._password_input.textChanged.connect(self._update_create_btn_state)
        form.addRow("パスワード:", self._password_input)

        # パスワード確認
        self._confirm_input = QLineEdit()
        self._confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._confirm_input.setPlaceholderText("必須")
        self._confirm_input.textChanged.connect(self._update_create_btn_state)
        self._confirm_input.returnPressed.connect(self._on_create_clicked)
        form.addRow("パスワード（確認）:", self._confirm_input)

        # ボタン行
        btn_layout = QHBoxLayout()
        self._cancel_btn = QPushButton("キャンセル")
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        self._create_btn = QPushButton("作成")
        self._create_btn.setEnabled(False)
        self._create_btn.setDefault(True)
        self._create_btn.clicked.connect(self._on_create_clicked)
        btn_layout.addStretch()
        btn_layout.addWidget(self._cancel_btn)
        btn_layout.addWidget(self._create_btn)

        # エラーメッセージ
        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: red;")
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.setWordWrap(True)

        # 全体レイアウト
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addLayout(form)
        layout.addLayout(btn_layout)
        layout.addWidget(self._error_label)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # イベントハンドラ
    # ------------------------------------------------------------------

    def _on_create_clicked(self) -> None:
        self._presenter.on_create(
            prefix=self._prefix_input.text(),
            password=self._password_input.text(),
            confirm=self._confirm_input.text(),
        )

    def _on_cancel_clicked(self) -> None:
        self._presenter.on_cancel()

    def _update_create_btn_state(self) -> None:
        """全必須項目が入力済みの場合のみ作成ボタンを活性にする。"""
        enabled = bool(
            self._prefix_input.text().strip()
            and self._password_input.text()
            and self._confirm_input.text()
        )
        self._create_btn.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Presenter から呼ばれるメソッド
    # ------------------------------------------------------------------

    def show_error(self, message: str) -> None:
        self._error_label.setText(message)

    def go_to_kanban_board(self) -> None:
        if self._navigator:
            self._navigator.show_kanban_board("manager")

    def go_to_startup(self) -> None:
        if self._navigator:
            self._navigator.show_startup()
