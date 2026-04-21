"""presentation/views/export_view.py - SCR-007 テキストエクスポート画面の View。"""

from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt

from domain.export_template import ExportTemplate
from domain.filter_condition import FilterCondition
from domain.member import Member
from domain.status import Status
from domain.tag_definition import TagDefinition
from presentation.components.filter_widget import FilterWidget
from presentation.presenters.export_presenter import ExportPresenter


class ExportView(QWidget):
    """SCR-007 テキストエクスポート画面（別ウィンドウ）。

    テンプレート選択 + フィルターでチケットを絞り込んで Jinja2 でテキスト生成する。
    """

    def __init__(self, initial_filter: FilterCondition | None = None) -> None:
        super().__init__()
        self._presenter = ExportPresenter(view=self)
        self._build_ui()
        self._presenter.on_load(initial_filter=initial_filter)

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setWindowTitle("PortableKanban - テキストエクスポート")
        self.setMinimumSize(900, 560)

        # テンプレート選択
        tmpl_row = QHBoxLayout()
        tmpl_row.addWidget(QLabel("テンプレート:"))
        self._template_combo = QComboBox()
        self._template_combo.currentIndexChanged.connect(self._on_template_changed)
        tmpl_row.addWidget(self._template_combo, stretch=1)

        # フィルター（左ペイン）
        self._filter_widget = FilterWidget()
        self._filter_widget.condition_changed.connect(self._on_filter_changed)
        self._filter_widget.setFixedWidth(260)

        # プレビューエリア（右ペイン）
        self._preview_edit = QTextEdit()
        self._preview_edit.setReadOnly(True)
        self._preview_edit.setFontFamily("MS Gothic, Consolas, monospace")

        # スプリッター
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._filter_widget)
        splitter.addWidget(self._preview_edit)
        splitter.setSizes([260, 640])

        # ステータスラベル
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)

        # ボタン行
        btn_layout = QHBoxLayout()
        export_btn = QPushButton("エクスポート...")
        export_btn.clicked.connect(self._on_export_clicked)
        copy_btn = QPushButton("クリップボードにコピー")
        copy_btn.clicked.connect(self._presenter.on_copy_to_clipboard)
        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(export_btn)
        btn_layout.addWidget(copy_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)

        # 全体レイアウト
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addLayout(tmpl_row)
        layout.addWidget(splitter, stretch=1)
        layout.addWidget(self._status_label)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # イベントハンドラ
    # ------------------------------------------------------------------

    def _on_template_changed(self, index: int) -> None:
        template_id = self._template_combo.itemData(index)
        if template_id is not None:
            self._presenter.on_template_changed(template_id)

    def _on_filter_changed(self) -> None:
        self._presenter.on_filter_changed(self._filter_widget.get_condition())

    def _on_export_clicked(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "テキストファイルの保存先を選択",
            "export.txt",
            "テキストファイル (*.txt);;全ファイル (*)",
        )
        if path:
            self._presenter.on_export(path)

    # ------------------------------------------------------------------
    # Presenter から呼ばれるメソッド
    # ------------------------------------------------------------------

    def load_templates(self, templates: list[ExportTemplate]) -> None:
        self._template_combo.blockSignals(True)
        self._template_combo.clear()
        for t in templates:
            self._template_combo.addItem(t.name, t.id)
        self._template_combo.blockSignals(False)
        if templates:
            self._template_combo.setCurrentIndex(0)

    def get_current_filter(self) -> FilterCondition:
        return self._filter_widget.get_condition()

    def restore_filter(self, condition: FilterCondition) -> None:
        self._filter_widget.restore_condition(condition)

    def init_filter(
        self,
        members: list[Member],
        statuses: list[Status],
        tag_defs: list[TagDefinition],
    ) -> None:
        self._filter_widget.set_members(members)
        self._filter_widget.set_statuses(statuses)
        self._filter_widget.set_tag_definitions(tag_defs)

    def show_preview(self, text: str) -> None:
        self._preview_edit.setPlainText(text)
        self._status_label.setText("")

    def show_error(self, message: str) -> None:
        self._status_label.setText(message)
