"""presentation/views/import_view.py - SCR-008 進捗取り込み画面の View。"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from domain.ticket_diff import TicketDiff
from presentation.presenters.import_presenter import ImportPresenter


class ImportView(QWidget):
    """SCR-008 進捗取り込み画面（別ウィンドウ）。

    ステップUI:
      STEP 1: ファイル選択
      STEP 2a: バリデーションエラー一覧（失敗時）
      STEP 2b: 差分プレビュー（成功時）
      STEP 3: 完了メッセージ
    """

    _STEP_SELECT = 0
    _STEP_ERROR = 1
    _STEP_DIFF = 2
    _STEP_DONE = 3

    def __init__(self) -> None:
        super().__init__()
        self._presenter = ImportPresenter(view=self)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setWindowTitle("PortableKanban - 進捗取り込み")
        self.setMinimumSize(700, 480)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_step_select())   # 0
        self._stack.addWidget(self._build_step_error())    # 1
        self._stack.addWidget(self._build_step_diff())     # 2
        self._stack.addWidget(self._build_step_done())     # 3
        self._stack.setCurrentIndex(self._STEP_SELECT)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self._stack)
        self.setLayout(layout)

    def _build_step_select(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)

        label = QLabel("① 取り込むJSONファイルを選択してください。")
        label.setStyleSheet("font-size: 13px; font-weight: bold;")

        self._path_label = QLabel("（未選択）")
        self._path_label.setStyleSheet("color: gray;")
        self._path_label.setWordWrap(True)

        select_btn = QPushButton("ファイルを選択...")
        select_btn.clicked.connect(self._on_select_clicked)

        btn_row = QHBoxLayout()
        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.close)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)

        layout.addWidget(label)
        layout.addWidget(self._path_label)
        layout.addWidget(select_btn)
        layout.addStretch()
        layout.addLayout(btn_row)
        w.setLayout(layout)
        return w

    def _build_step_error(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(8)

        label = QLabel("バリデーションエラーが発生しました。内容を確認して修正してください。")
        label.setStyleSheet("color: red; font-weight: bold;")
        label.setWordWrap(True)

        self._error_list = QListWidget()

        btn_row = QHBoxLayout()
        back_btn = QPushButton("← 戻る")
        back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(self._STEP_SELECT))
        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(back_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)

        layout.addWidget(label)
        layout.addWidget(self._error_list, stretch=1)
        layout.addLayout(btn_row)
        w.setLayout(layout)
        return w

    def _build_step_diff(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(8)

        label = QLabel("② 変更内容を確認してください。")
        label.setStyleSheet("font-size: 13px; font-weight: bold;")

        self._diff_table = QTableWidget()
        self._diff_table.setColumnCount(4)
        self._diff_table.setHorizontalHeaderLabels(
            ["チケットID", "タイトル", "変更フィールド", "変更内容"]
        )
        self._diff_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._diff_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._diff_table.verticalHeader().setVisible(False)
        self._diff_table.horizontalHeader().setStretchLastSection(True)

        btn_row = QHBoxLayout()
        self._execute_btn = QPushButton("取り込み実行")
        self._execute_btn.setStyleSheet("background: #d4edda; font-weight: bold;")
        self._execute_btn.clicked.connect(self._presenter.on_execute_import)
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.clicked.connect(self._presenter.on_cancel)
        btn_row.addWidget(self._execute_btn)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)

        layout.addWidget(label)
        layout.addWidget(self._diff_table, stretch=1)
        layout.addLayout(btn_row)
        w.setLayout(layout)
        return w

    def _build_step_done(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)

        self._done_label = QLabel("")
        self._done_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._done_label.setStyleSheet("font-size: 14px;")
        self._done_label.setWordWrap(True)

        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.close)

        layout.addStretch()
        layout.addWidget(self._done_label)
        layout.addStretch()
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        w.setLayout(layout)
        return w

    # ------------------------------------------------------------------
    # イベントハンドラ
    # ------------------------------------------------------------------

    def _on_select_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "取り込むJSONファイルを選択",
            "",
            "JSONファイル (*.json);;全ファイル (*)",
        )
        if path:
            self._path_label.setText(path)
            self._presenter.on_select_file(path)

    # ------------------------------------------------------------------
    # Presenter から呼ばれるメソッド
    # ------------------------------------------------------------------

    def show_validation_errors(self, errors: list[str]) -> None:
        self._error_list.clear()
        for e in errors:
            self._error_list.addItem(e)
        self._stack.setCurrentIndex(self._STEP_ERROR)

    def show_diff_preview(self, diffs: list[TicketDiff]) -> None:
        self._diff_table.setRowCount(0)
        for diff in diffs:
            if not diff.has_changes():
                continue
            for fd in diff.diffs:
                row = self._diff_table.rowCount()
                self._diff_table.insertRow(row)
                self._diff_table.setItem(row, 0, QTableWidgetItem(str(diff.ticket_id)))
                self._diff_table.setItem(row, 1, QTableWidgetItem(diff.ticket_title))
                self._diff_table.setItem(row, 2, QTableWidgetItem(fd.field_name))
                self._diff_table.setItem(
                    row, 3, QTableWidgetItem(f"{fd.before}  →  {fd.after}")
                )
        self._stack.setCurrentIndex(self._STEP_DIFF)

    def show_success(self, message: str) -> None:
        self._done_label.setStyleSheet("font-size: 14px; color: green;")
        self._done_label.setText(f"✓ {message}")
        self._stack.setCurrentIndex(self._STEP_DONE)

    def show_error(self, message: str) -> None:
        self._done_label.setStyleSheet("font-size: 13px; color: red;")
        self._done_label.setText(message)
        self._stack.setCurrentIndex(self._STEP_DONE)
