"""presentation/views/kanban_board_view.py - SCR-004 カンバンボード画面の View。"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from domain.filter_condition import FilterCondition
from domain.member import Member
from domain.status import Status
from domain.tag_definition import TagDefinition
from presentation.components.filter_widget import FilterWidget
from presentation.components.kanban_card_widget import KanbanCardWidget
from presentation.components.kanban_column_widget import KanbanColumnWidget
from presentation.presenters.kanban_board_presenter import KanbanBoardPresenter, StatusColumn


class KanbanBoardView(QWidget):
    """SCR-004 カンバンボード画面。

    ログイン後のメイン画面。ステータス列とチケットカードを表示する。
    """

    def __init__(self, role: str, db_folder: str, navigator: object | None = None) -> None:
        super().__init__()
        self._navigator = navigator
        self._presenter = KanbanBoardPresenter(view=self, role=role, db_folder=db_folder)
        self._columns: list[KanbanColumnWidget] = []
        self._build_ui(role)
        self._presenter.on_load()

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _build_ui(self, role: str) -> None:
        # manager 編集中警告バナー
        self._warning_label = QLabel("")
        self._warning_label.setStyleSheet(
            "background: #fff3cd; color: #856404; padding: 6px; font-weight: bold;"
        )
        self._warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._warning_label.hide()

        # フィルターウィジェット（左ペイン）
        self._filter_widget = FilterWidget()
        self._filter_widget.condition_changed.connect(self._on_filter_changed)
        self._filter_widget.setFixedWidth(280)

        # カンバン列エリア（右ペイン・横スクロール）
        self._board_container = QWidget()
        self._board_layout = QHBoxLayout()
        self._board_layout.setContentsMargins(4, 4, 4, 4)
        self._board_layout.setSpacing(8)
        self._board_layout.addStretch()
        self._board_container.setLayout(self._board_layout)

        board_scroll = QScrollArea()
        board_scroll.setWidgetResizable(True)
        board_scroll.setWidget(self._board_container)
        board_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # スプリッター（左:フィルター / 右:ボード）
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._filter_widget)
        splitter.addWidget(board_scroll)
        splitter.setSizes([280, 800])

        # ツールバー行（新規チケット・各機能ボタン）
        toolbar = QHBoxLayout()
        self._new_ticket_btn = QPushButton("+ 新規チケット")
        self._new_ticket_btn.clicked.connect(self._presenter.on_new_ticket)

        # manager 専用ボタン群
        self._settings_btn = QPushButton("⚙ 設定")
        self._settings_btn.clicked.connect(self._on_settings_clicked)
        self._prompt_btn = QPushButton("エクスポート")
        self._prompt_btn.clicked.connect(self._on_prompt_clicked)
        self._import_btn = QPushButton("進捗取り込み")
        self._import_btn.clicked.connect(self._on_import_clicked)
        self._export_btn = QPushButton("テキスト出力")
        self._export_btn.clicked.connect(self._on_export_clicked)

        # ガントチャートは全員利用可
        self._gantt_btn = QPushButton("ガントチャート")
        self._gantt_btn.clicked.connect(self._on_gantt_clicked)

        refresh_btn = QPushButton("↻ 更新")
        refresh_btn.clicked.connect(self.refresh)

        toolbar.addWidget(self._new_ticket_btn)
        toolbar.addStretch()
        toolbar.addWidget(refresh_btn)
        toolbar.addWidget(self._gantt_btn)
        toolbar.addWidget(self._prompt_btn)
        toolbar.addWidget(self._import_btn)
        toolbar.addWidget(self._export_btn)
        toolbar.addWidget(self._settings_btn)

        # 全体レイアウト
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._warning_label)
        layout.addLayout(toolbar)
        layout.addWidget(splitter, stretch=1)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # イベントハンドラ
    # ------------------------------------------------------------------

    def _on_filter_changed(self) -> None:
        self._presenter.on_filter_changed(self._filter_widget.get_condition())

    def _on_settings_clicked(self) -> None:
        if self._navigator:
            self._navigator.show_kanban_settings()

    def _on_gantt_clicked(self) -> None:
        if self._navigator:
            self._navigator.show_gantt()

    def _on_prompt_clicked(self) -> None:
        if self._navigator:
            self._navigator.show_prompt()

    def _on_import_clicked(self) -> None:
        if self._navigator:
            self._navigator.show_import()

    def _on_export_clicked(self) -> None:
        if self._navigator:
            self._navigator.show_export()

    def closeEvent(self, event) -> None:
        self._presenter.on_close()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Presenter から呼ばれるメソッド
    # ------------------------------------------------------------------

    def init_filter(
        self,
        members: list[Member],
        statuses: list[Status],
        tag_defs: list[TagDefinition],
        default_hidden_status_ids: list[int],
    ) -> None:
        """フィルターウィジェットに初期データをセットする。"""
        self._filter_widget.set_members(members)
        self._filter_widget.set_statuses(statuses)
        self._filter_widget.set_tag_definitions(tag_defs)
        self._filter_widget.set_default_hidden_statuses(default_hidden_status_ids)

    def render_board(
        self,
        columns: list[StatusColumn],
        member_map: dict[int, str],
        prefix: str,
        draggable: bool,
    ) -> None:
        """カンバンボード全体を再描画する。"""
        # 既存列を削除
        for col in self._columns:
            self._board_layout.removeWidget(col)
            col.setParent(None)
        self._columns.clear()

        stretch_item = self._board_layout.takeAt(0)  # stretch を一旦外す

        for col_data in columns:
            col = KanbanColumnWidget(
                status=col_data.status, accept_drops=draggable
            )
            col.card_dropped.connect(self._presenter.on_card_dropped)

            for ticket in col_data.tickets:
                display_num = f"{prefix}-{ticket.id}" if prefix else str(ticket.id)
                assignee_name = member_map.get(ticket.assignee_id, "") if ticket.assignee_id else ""
                card = KanbanCardWidget(
                    ticket=ticket,
                    display_number=display_num,
                    assignee_name=assignee_name,
                    on_click=self._presenter.on_card_clicked,
                    draggable=draggable,
                )
                col.add_card(card)

            self._board_layout.addWidget(col)
            self._columns.append(col)

        self._board_layout.addStretch()  # stretch を末尾に戻す

    def set_role(self, role: str) -> None:
        """ロールに応じてUI要素を制御する。"""
        is_manager = role == "manager"
        # 設定画面は manager 専用、それ以外は member も利用可
        self._settings_btn.setVisible(is_manager)

    def show_manager_warning(self, message: str) -> None:
        """manager編集中警告バナーを表示する。"""
        self._warning_label.setText(f"⚠ {message}")
        self._warning_label.show()

    def hide_manager_warning(self) -> None:
        self._warning_label.hide()

    def show_error(self, message: str) -> None:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "エラー", message)

    def get_current_filter(self) -> FilterCondition:
        """現在のフィルター条件を返す（Presenter からの呼び出し用）。"""
        return self._filter_widget.get_condition()

    def restore_filter(self, condition: FilterCondition) -> None:
        """フィルター条件を復元する（reload_and_render 後に呼ぶ）。"""
        self._filter_widget.restore_condition(condition)

    def open_ticket_detail(self, ticket_id: int | None) -> None:
        """チケット詳細画面を開く（navigator 経由）。"""
        if self._navigator:
            self._navigator.show_ticket_detail(ticket_id)

    def cleanup(self) -> None:
        """アプリ終了やボード離脱時のリソース解放（ロック解放など）。"""
        self._presenter.on_close()

    def refresh(self) -> None:
        """チケット詳細や設定から戻った際にボードを最新データで再描画する。

        Bug6: マスタデータ（ステータス・担当者）も再読み込みするため、
        プロジェクト作成直後にステータスを追加した場合も正しく反映される。
        """
        self._presenter.reload_and_render()
