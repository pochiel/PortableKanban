"""presentation/views/ticket_detail_view.py - SCR-005 チケット詳細・編集画面の View。"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import QDate

from domain.member import Member
from domain.status import Status
from domain.tag_definition import TagDefinition, FIELD_TYPE_DATE
from domain.tag_value import TagValue
from domain.ticket import Ticket
from presentation.presenters.ticket_detail_presenter import TicketDetailPresenter


class TicketDetailView(QWidget):
    """SCR-005 チケット詳細・編集画面。

    ticket_id=None なら新規作成モード、int なら編集モード。
    member 権限時は入力欄をdisableにして表示のみ。
    """

    def __init__(
        self,
        ticket_id: int | None,
        role: str,
        navigator: object | None = None,
    ) -> None:
        super().__init__()
        self._navigator = navigator
        self._role = role
        self._tag_defs: list[TagDefinition] = []
        self._tag_widgets: dict[int, QWidget] = {}  # tag_def_id → 入力ウィジェット
        self._presenter = TicketDetailPresenter(
            view=self, ticket_id=ticket_id, role=role
        )
        self._build_ui(ticket_id)
        self._presenter.on_load()

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _build_ui(self, ticket_id: int | None) -> None:
        self._is_new = ticket_id is None  # Bug3対応: 新規かどうかを保持
        title_str = "チケット詳細" if ticket_id else "新規チケット"
        self.setWindowTitle(f"PortableKanban - {title_str}")

        # 基本フォーム
        form = QFormLayout()
        form.setSpacing(10)

        # チケット番号（編集不可）
        self._number_label = QLabel("（採番前）")
        self._number_label.setStyleSheet("font-weight: bold;")
        if ticket_id:
            form.addRow("チケット番号:", self._number_label)

        # タイトル
        self._title_input = QLineEdit()
        self._title_input.setPlaceholderText("必須")
        form.addRow("タイトル:", self._title_input)

        # 担当者
        self._assignee_combo = QComboBox()
        self._assignee_combo.addItem("-- 担当者を選択 --", None)
        form.addRow("担当者:", self._assignee_combo)

        # ステータス
        self._status_combo = QComboBox()
        form.addRow("ステータス:", self._status_combo)

        # 開始日
        self._start_date_edit = _OptionalDateEdit()
        form.addRow("開始日:", self._start_date_edit)

        # 終了予定日
        self._end_date_edit = _OptionalDateEdit()
        form.addRow("終了予定日:", self._end_date_edit)

        # 備考
        self._note_edit = QTextEdit()
        self._note_edit.setFixedHeight(80)
        form.addRow("備考:", self._note_edit)

        # タグエリア（動的生成）
        self._tag_form = QFormLayout()
        self._tag_form.setSpacing(6)
        tag_container = QWidget()
        tag_container.setLayout(self._tag_form)

        # ボタン行
        btn_layout = QHBoxLayout()
        self._back_btn = QPushButton("戻る")
        self._back_btn.clicked.connect(self._presenter.on_cancel)
        self._delete_btn = QPushButton("削除")
        self._delete_btn.setStyleSheet("color: red;")
        self._delete_btn.clicked.connect(self._on_delete_clicked)
        self._save_btn = QPushButton("保存")
        self._save_btn.setDefault(True)
        self._save_btn.clicked.connect(self._on_save_clicked)

        btn_layout.addWidget(self._back_btn)
        btn_layout.addStretch()
        # Bug3: 常にレイアウトに追加し、新規時は非表示にする（floating window 防止）
        btn_layout.addWidget(self._delete_btn)
        if self._is_new:
            self._delete_btn.setVisible(False)
        btn_layout.addWidget(self._save_btn)

        # エラーメッセージ
        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: red;")
        self._error_label.setWordWrap(True)

        # スクロール対応
        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.addLayout(form)
        content_layout.addWidget(QLabel("タグ"))
        content_layout.addWidget(tag_container)
        content_layout.addStretch()
        content.setLayout(content_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll, stretch=1)
        layout.addWidget(self._error_label)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # イベントハンドラ
    # ------------------------------------------------------------------

    def _on_save_clicked(self) -> None:
        self._presenter.on_save(
            title=self._title_input.text(),
            status_id=self._status_combo.currentData(),
            assignee_id=self._assignee_combo.currentData(),
            start_date=self._start_date_edit.get_iso_str(),
            end_date=self._end_date_edit.get_iso_str(),
            note=self._note_edit.toPlainText(),
            tag_values=self._collect_tag_values(),
        )

    def _on_delete_clicked(self) -> None:
        reply = QMessageBox.question(
            self,
            "確認",
            "このチケットを削除しますか？（取り消し不可）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._presenter.on_delete()

    def _collect_tag_values(self) -> dict[int, str]:
        result: dict[int, str] = {}
        for tag_def_id, widget in self._tag_widgets.items():
            if isinstance(widget, QLineEdit):
                result[tag_def_id] = widget.text()
            elif isinstance(widget, _OptionalDateEdit):
                result[tag_def_id] = widget.get_iso_str() or ""
        return result

    # ------------------------------------------------------------------
    # Presenter から呼ばれるメソッド
    # ------------------------------------------------------------------

    def load_members(self, members: list[Member]) -> None:
        self._assignee_combo.clear()
        self._assignee_combo.addItem("未アサイン", None)
        for m in members:
            self._assignee_combo.addItem(m.name, m.id)

    def load_statuses(self, statuses: list[Status]) -> None:
        self._status_combo.clear()
        for s in statuses:
            self._status_combo.addItem(s.name, s.id)

    def load_tag_definitions(self, tags: list[TagDefinition]) -> None:
        """タグ定義に合わせて入力ウィジェットを動的生成する。"""
        # 既存ウィジェットをクリア
        while self._tag_form.rowCount() > 0:
            self._tag_form.removeRow(0)
        self._tag_widgets.clear()
        self._tag_defs = tags

        for t in tags:
            if t.field_type == FIELD_TYPE_DATE:
                widget = _OptionalDateEdit()
            else:
                widget = QLineEdit()
                widget.setPlaceholderText("（未入力）")
            self._tag_form.addRow(f"{t.name}:", widget)
            self._tag_widgets[t.id] = widget

    def load_ticket(self, ticket: Ticket, tag_values: list[TagValue], prefix: str) -> None:
        """チケットデータをフォームに反映する。"""
        if ticket.id and prefix:
            self._number_label.setText(f"{prefix}-{ticket.id}")

        self._title_input.setText(ticket.title)

        # 担当者
        for i in range(self._assignee_combo.count()):
            if self._assignee_combo.itemData(i) == ticket.assignee_id:
                self._assignee_combo.setCurrentIndex(i)
                break

        # ステータス
        for i in range(self._status_combo.count()):
            if self._status_combo.itemData(i) == ticket.status_id:
                self._status_combo.setCurrentIndex(i)
                break

        # 日付
        if ticket.start_date:
            self._start_date_edit.set_iso_str(ticket.start_date)
        if ticket.end_date:
            self._end_date_edit.set_iso_str(ticket.end_date)

        # 備考
        self._note_edit.setPlainText(ticket.note or "")

        # タグ値
        tv_map = {tv.tag_def_id: tv.value for tv in tag_values}
        for tag_def_id, widget in self._tag_widgets.items():
            value = tv_map.get(tag_def_id, "")
            if isinstance(widget, QLineEdit):
                widget.setText(value)
            elif isinstance(widget, _OptionalDateEdit):
                widget.set_iso_str(value)

    def set_editable(self, editable: bool) -> None:
        """ロールに応じて入力欄を有効/無効にする。"""
        self._title_input.setReadOnly(not editable)
        self._assignee_combo.setEnabled(editable)
        self._status_combo.setEnabled(editable)
        self._start_date_edit.setEnabled(editable)
        self._end_date_edit.setEnabled(editable)
        self._note_edit.setReadOnly(not editable)
        self._save_btn.setVisible(editable)
        # Bug3: 新規チケットでは削除ボタンを表示しない
        if not self._is_new:
            self._delete_btn.setVisible(editable)
        for w in self._tag_widgets.values():
            w.setEnabled(editable)

    def set_default_start_date(self) -> None:
        """Bug4: 新規チケットの開始日を本日にセットする。"""
        from datetime import date
        self._start_date_edit.set_iso_str(date.today().isoformat())

    def set_default_status(self, status_id: int | None) -> None:
        if status_id is None:
            return
        for i in range(self._status_combo.count()):
            if self._status_combo.itemData(i) == status_id:
                self._status_combo.setCurrentIndex(i)
                break

    def show_error(self, message: str) -> None:
        self._error_label.setText(message)

    def go_to_kanban_board(self) -> None:
        if self._navigator:
            self._navigator.show_kanban_board_back()


class _SmartDateEdit(QDateEdit):
    """Bug5: カレンダーポップアップを常に現在月で開く QDateEdit サブクラス。

    日付が minimumDate（「未設定」センチネル）の場合、
    カレンダーのページを今日の年月に設定してから表示する。
    """

    def showPopup(self) -> None:
        if self.date() == self.minimumDate():
            today = QDate.currentDate()
            cal = self.calendarWidget()
            if cal is not None:
                cal.setCurrentPage(today.year(), today.month())
        super().showPopup()


class _OptionalDateEdit(QWidget):
    """クリアボタン付き日付入力。空の場合は None を返す。"""

    def __init__(self) -> None:
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._edit = _SmartDateEdit()
        self._edit.setCalendarPopup(True)
        self._edit.setSpecialValueText("未設定")
        self._edit.setMinimumDate(QDate(2000, 1, 1))
        self._edit.setDate(self._edit.minimumDate())

        clear_btn = QPushButton("×")
        clear_btn.setFixedWidth(22)
        clear_btn.clicked.connect(self._clear)

        layout.addWidget(self._edit)
        layout.addWidget(clear_btn)
        self.setLayout(layout)

    def _clear(self) -> None:
        self._edit.setDate(self._edit.minimumDate())

    def get_iso_str(self) -> str | None:
        qd = self._edit.date()
        if qd == self._edit.minimumDate():
            return None
        return f"{qd.year():04d}-{qd.month():02d}-{qd.day():02d}"

    def set_iso_str(self, iso: str) -> None:
        try:
            y, m, d = (int(x) for x in iso.split("-"))
            self._edit.setDate(QDate(y, m, d))
        except (ValueError, AttributeError):
            self._clear()

    def setEnabled(self, enabled: bool) -> None:
        self._edit.setEnabled(enabled)
        super().setEnabled(enabled)
