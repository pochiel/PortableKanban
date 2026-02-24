"""presentation/views/gantt_view.py - SCR-006 ガントチャート出力画面の View。"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from domain.member import Member
from domain.status import Status
from domain.ticket import Ticket
from presentation.components.filter_widget import FilterWidget
from presentation.presenters.gantt_presenter import GanttPresenter


class GanttView(QWidget):
    """SCR-006 ガントチャート出力画面（別ウィンドウ）。

    FilterWidget でチケットを絞り込み、plotly HTML を生成・出力する。
    """

    def __init__(self) -> None:
        super().__init__()
        self._presenter = GanttPresenter(view=self)
        self._build_ui()
        self._presenter.on_load()

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setWindowTitle("PortableKanban - ガントチャート出力")
        self.setMinimumSize(900, 560)

        # フィルターウィジェット（左ペイン）
        self._filter_widget = FilterWidget()
        self._filter_widget.condition_changed.connect(self._on_filter_changed)
        self._filter_widget.setFixedWidth(260)

        # プレビューテーブル（右ペイン）
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["番号", "タイトル", "担当者", "開始日", "終了予定日"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)

        # スプリッター
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._filter_widget)
        splitter.addWidget(self._table)
        splitter.setSizes([260, 640])

        # ボタン行
        btn_layout = QHBoxLayout()
        self._export_btn = QPushButton("HTML出力...")
        self._export_btn.clicked.connect(self._on_export_clicked)
        self._browser_btn = QPushButton("ブラウザで開く")
        self._browser_btn.setEnabled(False)
        self._browser_btn.clicked.connect(self._presenter.on_open_browser)
        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.close)

        btn_layout.addWidget(self._export_btn)
        btn_layout.addWidget(self._browser_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)

        # エラーメッセージ
        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: red;")
        self._error_label.setWordWrap(True)

        # 全体レイアウト
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(splitter, stretch=1)
        layout.addWidget(self._error_label)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # イベントハンドラ
    # ------------------------------------------------------------------

    def _on_filter_changed(self) -> None:
        self._presenter.on_filter_changed(self._filter_widget.get_condition())

    def _on_export_clicked(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "HTML ファイルの保存先を選択",
            "gantt.html",
            "HTML ファイル (*.html)",
        )
        if path:
            self._presenter.on_export_html(path)

    # ------------------------------------------------------------------
    # Presenter から呼ばれるメソッド
    # ------------------------------------------------------------------

    def init_filter(self, members: list[Member], statuses: list[Status]) -> None:
        self._filter_widget.set_members(members)
        self._filter_widget.set_statuses(statuses)

    def load_preview(
        self,
        tickets: list[Ticket],
        members: list[Member],
        statuses: list[Status],
    ) -> None:
        """チケット一覧をテーブルに表示する。"""
        member_map = {m.id: m.name for m in members}
        status_map = {s.id: s.name for s in statuses}
        prefix = ""
        try:
            from service.ticket_service import TicketService
            prefix = TicketService().get_prefix()
        except Exception:
            pass

        self._table.setRowCount(0)
        for t in tickets:
            row = self._table.rowCount()
            self._table.insertRow(row)
            display_num = f"{prefix}-{t.id}" if prefix else str(t.id)
            assignee = member_map.get(t.assignee_id, "") if t.assignee_id else ""
            no_date_mark = "（未設定）"
            items = [
                display_num,
                t.title,
                assignee,
                t.start_date or no_date_mark,
                t.end_date or no_date_mark,
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)
                if col in (3, 4) and text == no_date_mark:
                    item.setForeground(Qt.GlobalColor.gray)
                self._table.setItem(row, col, item)

    def set_output_ready(self, path: str) -> None:
        """出力完了後にブラウザで開くボタンを活性にする。"""
        self._browser_btn.setEnabled(True)
        self._error_label.setText(f"出力完了: {path}")
        self._error_label.setStyleSheet("color: green;")

    def show_error(self, message: str) -> None:
        self._error_label.setText(message)
        self._error_label.setStyleSheet("color: red;")
