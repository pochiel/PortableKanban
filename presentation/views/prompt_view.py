"""presentation/views/prompt_view.py - SCR-009 プロンプト生成画面の View。"""

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from presentation.presenters.prompt_presenter import PromptPresenter


class PromptView(QWidget):
    """SCR-009 プロンプト生成画面（別ウィンドウ）。

    AIプロンプトタブとJSONフォーマットタブを持つ。
    """

    def __init__(self) -> None:
        super().__init__()
        self._presenter = PromptPresenter(view=self)
        self._build_ui()
        self._presenter.on_load()

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setWindowTitle("PortableKanban - エクスポート")
        self.setMinimumSize(700, 540)

        # タブウィジェット
        self._tabs = QTabWidget()

        self._prompt_edit = QTextEdit()
        self._prompt_edit.setReadOnly(True)
        self._prompt_edit.setFontFamily("MS Gothic, Consolas, monospace")
        self._tabs.addTab(self._prompt_edit, "データベース")

        self._format_edit = QTextEdit()
        self._format_edit.setReadOnly(True)
        self._format_edit.setFontFamily("MS Gothic, Consolas, monospace")
        self._tabs.addTab(self._format_edit, "JSONフォーマット")

        # ステータス表示
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: green;")

        # ボタン行
        btn_layout = QHBoxLayout()
        copy_btn = QPushButton("クリップボードにコピー")
        copy_btn.clicked.connect(self._on_copy_clicked)
        regen_btn = QPushButton("再生成")
        regen_btn.clicked.connect(self._presenter.on_regenerate)
        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.close)

        btn_layout.addWidget(copy_btn)
        btn_layout.addWidget(regen_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)

        # 全体レイアウト
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self._tabs, stretch=1)
        layout.addWidget(self._status_label)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # イベントハンドラ
    # ------------------------------------------------------------------

    def _on_copy_clicked(self) -> None:
        current = self._tabs.currentWidget()
        if current is self._prompt_edit:
            self._presenter.on_copy_to_clipboard(self._prompt_edit.toPlainText())
        else:
            self._presenter.on_copy_to_clipboard(self._format_edit.toPlainText())

    # ------------------------------------------------------------------
    # Presenter から呼ばれるメソッド
    # ------------------------------------------------------------------

    def show_prompt(self, prompt: str) -> None:
        self._prompt_edit.setPlainText(prompt)

    def show_format(self, fmt: str) -> None:
        self._format_edit.setPlainText(fmt)

    def show_copied(self) -> None:
        self._status_label.setText("クリップボードにコピーしました。")
