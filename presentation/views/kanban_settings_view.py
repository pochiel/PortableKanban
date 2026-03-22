"""presentation/views/kanban_settings_view.py - SCR-003 カンバン設定画面の View。

タブ形式で担当者・ステータス・タグ定義を管理する別ウィンドウ。
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from domain.export_template import ExportTemplate
from domain.member import Member
from domain.status import Status
from domain.tag_definition import TagDefinition, FIELD_TYPE_TEXT, FIELD_TYPE_DATE
from presentation.presenters.kanban_settings_presenter import KanbanSettingsPresenter


class KanbanSettingsView(QWidget):
    """SCR-003 カンバン設定画面。manager限定。別ウィンドウで表示する。"""

    def __init__(self) -> None:
        super().__init__()
        self._presenter = KanbanSettingsPresenter(view=self)
        self._members: list[Member] = []
        self._statuses: list[Status] = []
        self._tags: list[TagDefinition] = []
        self._templates: list[ExportTemplate] = []
        self._build_ui()
        self._presenter.on_load()

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setWindowTitle("カンバン設定")
        self.setMinimumSize(640, 500)

        # ステータスバー代わりのメッセージラベル
        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # タブウィジェット
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_member_tab(), "担当者")
        self._tabs.addTab(self._build_status_tab(), "ステータス")
        self._tabs.addTab(self._build_tag_tab(), "タグ定義")
        self._tabs.addTab(self._build_template_tab(), "テンプレート")

        layout = QVBoxLayout()
        layout.addWidget(self._tabs)
        layout.addWidget(self._status_label)
        self.setLayout(layout)

    # ---------- タブ①: 担当者管理 ----------

    def _build_member_tab(self) -> QWidget:
        tab = QWidget()

        # テーブル
        self._member_table = QTableWidget(0, 3)
        self._member_table.setHorizontalHeaderLabels(["名前", "メールアドレス", "状態"])
        self._member_table.horizontalHeader().setStretchLastSection(True)
        self._member_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._member_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        # ボタン
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("追加")
        edit_btn = QPushButton("編集")
        deactivate_btn = QPushButton("無効化")
        add_btn.clicked.connect(self._on_add_member)
        edit_btn.clicked.connect(self._on_edit_member)
        deactivate_btn.clicked.connect(self._on_deactivate_member)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(deactivate_btn)
        btn_layout.addStretch()

        layout = QVBoxLayout()
        layout.addLayout(btn_layout)
        layout.addWidget(self._member_table)
        tab.setLayout(layout)
        return tab

    # ---------- タブ②: ステータス管理 ----------

    def _build_status_tab(self) -> QWidget:
        tab = QWidget()

        # テーブル
        self._status_table = QTableWidget(0, 2)
        self._status_table.setHorizontalHeaderLabels(["ステータス名", "表示順"])
        self._status_table.horizontalHeader().setStretchLastSection(True)
        self._status_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._status_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        # ボタン
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("追加")
        edit_btn = QPushButton("編集")
        delete_btn = QPushButton("削除")
        up_btn = QPushButton("↑")
        down_btn = QPushButton("↓")
        add_btn.clicked.connect(self._on_add_status)
        edit_btn.clicked.connect(self._on_edit_status)
        delete_btn.clicked.connect(self._on_delete_status)
        up_btn.clicked.connect(lambda: self._on_reorder_status("up"))
        down_btn.clicked.connect(lambda: self._on_reorder_status("down"))
        for btn in [add_btn, edit_btn, delete_btn, up_btn, down_btn]:
            btn_layout.addWidget(btn)
        btn_layout.addStretch()

        # デフォルト非表示設定エリア
        self._hidden_group = QGroupBox("デフォルト非表示ステータス")
        self._hidden_layout = QVBoxLayout()
        self._hidden_checkboxes: list[tuple[QCheckBox, int]] = []  # (checkbox, status_id)
        save_hidden_btn = QPushButton("保存")
        save_hidden_btn.clicked.connect(self._on_save_default_hidden)
        self._hidden_layout.addWidget(save_hidden_btn)
        self._hidden_group.setLayout(self._hidden_layout)

        layout = QVBoxLayout()
        layout.addLayout(btn_layout)
        layout.addWidget(self._status_table)
        layout.addWidget(self._hidden_group)
        tab.setLayout(layout)
        return tab

    # ---------- タブ③: タグ定義管理 ----------

    def _build_tag_tab(self) -> QWidget:
        tab = QWidget()

        # テーブル
        self._tag_table = QTableWidget(0, 2)
        self._tag_table.setHorizontalHeaderLabels(["タグ名", "フィールド型"])
        self._tag_table.horizontalHeader().setStretchLastSection(True)
        self._tag_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._tag_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        # ボタン
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("追加")
        edit_btn = QPushButton("編集")
        delete_btn = QPushButton("削除")
        add_btn.clicked.connect(self._on_add_tag)
        edit_btn.clicked.connect(self._on_edit_tag)
        delete_btn.clicked.connect(self._on_delete_tag)
        for btn in [add_btn, edit_btn, delete_btn]:
            btn_layout.addWidget(btn)
        btn_layout.addStretch()

        layout = QVBoxLayout()
        layout.addLayout(btn_layout)
        layout.addWidget(self._tag_table)
        tab.setLayout(layout)
        return tab

    # ---------- タブ④: テンプレート管理 ----------

    def _build_template_tab(self) -> QWidget:
        tab = QWidget()

        # テンプレート一覧
        self._template_list = QListWidget()

        # ボタン行
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("追加")
        edit_btn = QPushButton("編集")
        delete_btn = QPushButton("削除")
        add_btn.clicked.connect(self._on_add_template)
        edit_btn.clicked.connect(self._on_edit_template)
        delete_btn.clicked.connect(self._on_delete_template)
        for btn in [add_btn, edit_btn, delete_btn]:
            btn_layout.addWidget(btn)
        btn_layout.addStretch()

        # Jinja2 変数ヘルプラベル
        help_label = QLabel(
            "テンプレートで使用できる変数: "
            "{{ t.number }}, {{ t.title }}, {{ t.status }}, {{ t.assignee }}, "
            "{{ t.start_date }}, {{ t.end_date }}, {{ t.note }}, {{ t.tags['タグ名'] }}\n"
            "独自フィルター: "
            "{{ t.end_date | jdate }}  →  2026年03月18日(水)  / "
            "tickets | groupby_tag('タグ名')  →  タグでグループ化（日本語タグ名対応）"
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: gray; font-size: 11px;")

        layout = QVBoxLayout()
        layout.addLayout(btn_layout)
        layout.addWidget(self._template_list)
        layout.addWidget(help_label)
        tab.setLayout(layout)
        return tab

    # ------------------------------------------------------------------
    # イベントハンドラ: 担当者タブ
    # ------------------------------------------------------------------

    def _on_add_member(self) -> None:
        dialog = _MemberDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._presenter.on_add_member(dialog.get_name(), dialog.get_email())

    def _on_edit_member(self) -> None:
        member = self._get_selected_member()
        if member is None:
            self.show_error("編集する担当者を選択してください。")
            return
        dialog = _MemberDialog(parent=self, name=member.name, email=member.email)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._presenter.on_edit_member(
                member.id, dialog.get_name(), dialog.get_email()
            )

    def _on_deactivate_member(self) -> None:
        member = self._get_selected_member()
        if member is None:
            self.show_error("無効化する担当者を選択してください。")
            return
        reply = QMessageBox.question(
            self,
            "確認",
            f"「{member.name}」を無効化しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._presenter.on_deactivate_member(member.id)

    def _get_selected_member(self) -> Member | None:
        row = self._member_table.currentRow()
        if row < 0 or row >= len(self._members):
            return None
        return self._members[row]

    # ------------------------------------------------------------------
    # イベントハンドラ: ステータスタブ
    # ------------------------------------------------------------------

    def _on_add_status(self) -> None:
        dialog = _NameDialog(parent=self, title="ステータスを追加", label="ステータス名:")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._presenter.on_add_status(dialog.get_name())

    def _on_edit_status(self) -> None:
        status = self._get_selected_status()
        if status is None:
            self.show_error("編集するステータスを選択してください。")
            return
        dialog = _NameDialog(
            parent=self, title="ステータスを編集", label="ステータス名:", name=status.name
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._presenter.on_edit_status(status.id, dialog.get_name())

    def _on_delete_status(self) -> None:
        status = self._get_selected_status()
        if status is None:
            self.show_error("削除するステータスを選択してください。")
            return
        reply = QMessageBox.question(
            self,
            "確認",
            f"「{status.name}」を削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._presenter.on_delete_status(status.id)

    def _on_reorder_status(self, direction: str) -> None:
        status = self._get_selected_status()
        if status is None:
            self.show_error("移動するステータスを選択してください。")
            return
        self._presenter.on_reorder_status(status.id, direction)

    def _on_save_default_hidden(self) -> None:
        hidden_ids = [
            status_id
            for cb, status_id in self._hidden_checkboxes
            if cb.isChecked()
        ]
        self._presenter.on_update_default_hidden(hidden_ids)

    def _get_selected_status(self) -> Status | None:
        row = self._status_table.currentRow()
        if row < 0 or row >= len(self._statuses):
            return None
        return self._statuses[row]

    # ------------------------------------------------------------------
    # イベントハンドラ: タグタブ
    # ------------------------------------------------------------------

    def _on_add_tag(self) -> None:
        dialog = _TagDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._presenter.on_add_tag(dialog.get_name(), dialog.get_field_type())

    def _on_edit_tag(self) -> None:
        tag = self._get_selected_tag()
        if tag is None:
            self.show_error("編集するタグを選択してください。")
            return
        dialog = _TagDialog(parent=self, name=tag.name, field_type=tag.field_type)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._presenter.on_edit_tag(
                tag.id, dialog.get_name(), dialog.get_field_type()
            )

    def _on_delete_tag(self) -> None:
        tag = self._get_selected_tag()
        if tag is None:
            self.show_error("削除するタグを選択してください。")
            return
        reply = QMessageBox.question(
            self,
            "確認",
            f"「{tag.name}」を削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._presenter.on_delete_tag(tag.id)

    def _get_selected_tag(self) -> TagDefinition | None:
        row = self._tag_table.currentRow()
        if row < 0 or row >= len(self._tags):
            return None
        return self._tags[row]

    # ------------------------------------------------------------------
    # イベントハンドラ: テンプレートタブ
    # ------------------------------------------------------------------

    def _on_add_template(self) -> None:
        dialog = _TemplateDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._presenter.on_add_template(dialog.get_name(), dialog.get_body())

    def _on_edit_template(self) -> None:
        tmpl = self._get_selected_template()
        if tmpl is None:
            self.show_error("編集するテンプレートを選択してください。")
            return
        dialog = _TemplateDialog(parent=self, name=tmpl.name, body=tmpl.template_body)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._presenter.on_edit_template(
                tmpl.id, dialog.get_name(), dialog.get_body()
            )

    def _on_delete_template(self) -> None:
        tmpl = self._get_selected_template()
        if tmpl is None:
            self.show_error("削除するテンプレートを選択してください。")
            return
        reply = QMessageBox.question(
            self,
            "確認",
            f"「{tmpl.name}」を削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._presenter.on_delete_template(tmpl.id)

    def _get_selected_template(self) -> ExportTemplate | None:
        row = self._template_list.currentRow()
        if row < 0 or row >= len(self._templates):
            return None
        return self._templates[row]

    # ------------------------------------------------------------------
    # Presenter から呼ばれるメソッド
    # ------------------------------------------------------------------

    def load_members(self, members: list[Member]) -> None:
        self._members = members
        self._member_table.setRowCount(0)
        for row, m in enumerate(members):
            self._member_table.insertRow(row)
            self._member_table.setItem(row, 0, QTableWidgetItem(m.name))
            self._member_table.setItem(row, 1, QTableWidgetItem(m.email))
            self._member_table.setItem(
                row, 2, QTableWidgetItem("有効" if m.is_active else "無効")
            )

    def load_statuses(self, statuses: list[Status], hidden_ids: list[int]) -> None:
        self._statuses = statuses

        # テーブル更新
        self._status_table.setRowCount(0)
        for row, s in enumerate(statuses):
            self._status_table.insertRow(row)
            self._status_table.setItem(row, 0, QTableWidgetItem(s.name))
            self._status_table.setItem(row, 1, QTableWidgetItem(str(s.display_order)))

        # デフォルト非表示チェックボックス更新
        # 既存チェックボックスをクリア
        for cb, _ in self._hidden_checkboxes:
            cb.setParent(None)
        self._hidden_checkboxes.clear()

        for s in statuses:
            cb = QCheckBox(s.name)
            cb.setChecked(s.id in hidden_ids)
            self._hidden_layout.insertWidget(
                self._hidden_layout.count() - 1, cb  # 保存ボタンの前に挿入
            )
            self._hidden_checkboxes.append((cb, s.id))

    def load_tag_definitions(self, tags: list[TagDefinition]) -> None:
        self._tags = tags
        self._tag_table.setRowCount(0)
        type_labels = {FIELD_TYPE_TEXT: "テキスト", FIELD_TYPE_DATE: "日付"}
        for row, t in enumerate(tags):
            self._tag_table.insertRow(row)
            self._tag_table.setItem(row, 0, QTableWidgetItem(t.name))
            self._tag_table.setItem(
                row, 1, QTableWidgetItem(type_labels.get(t.field_type, t.field_type))
            )

    def load_templates(self, templates: list[ExportTemplate]) -> None:
        self._templates = templates
        self._template_list.clear()
        for t in templates:
            self._template_list.addItem(t.name)

    def show_error(self, message: str) -> None:
        self._status_label.setStyleSheet("color: red;")
        self._status_label.setText(message)

    def show_success(self, message: str) -> None:
        self._status_label.setStyleSheet("color: green;")
        self._status_label.setText(message)


# ---------------------------------------------------------------------------
# ダイアログクラス（インライン定義）
# ---------------------------------------------------------------------------


class _NameDialog(QDialog):
    """シンプルな名前入力ダイアログ。担当者追加以外のシンプルな入力に使用する。"""

    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        label: str,
        name: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(320)

        self._name_input = QLineEdit(name)
        self._name_input.returnPressed.connect(self._try_accept)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._try_accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout()
        form.addRow(label, self._name_input)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _try_accept(self) -> None:
        if self._name_input.text().strip():
            self.accept()

    def get_name(self) -> str:
        return self._name_input.text()


class _MemberDialog(QDialog):
    """担当者追加・編集ダイアログ。名前とメールアドレスを入力する。"""

    def __init__(
        self,
        parent: QWidget | None,
        name: str = "",
        email: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("担当者")
        self.setMinimumWidth(360)

        self._name_input = QLineEdit(name)
        self._email_input = QLineEdit(email)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._try_accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout()
        form.addRow("名前（必須）:", self._name_input)
        form.addRow("メールアドレス:", self._email_input)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _try_accept(self) -> None:
        if self._name_input.text().strip():
            self.accept()

    def get_name(self) -> str:
        return self._name_input.text()

    def get_email(self) -> str:
        return self._email_input.text()


class _TagDialog(QDialog):
    """タグ定義追加・編集ダイアログ。名前とフィールド型を入力する。"""

    _FIELD_TYPES = [
        (FIELD_TYPE_TEXT, "テキスト"),
        (FIELD_TYPE_DATE, "日付"),
    ]

    def __init__(
        self,
        parent: QWidget | None,
        name: str = "",
        field_type: str = FIELD_TYPE_TEXT,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("タグ定義")
        self.setMinimumWidth(320)

        self._name_input = QLineEdit(name)

        self._type_combo = QComboBox()
        for value, label in self._FIELD_TYPES:
            self._type_combo.addItem(label, value)
        # 現在の field_type を選択
        for i, (value, _) in enumerate(self._FIELD_TYPES):
            if value == field_type:
                self._type_combo.setCurrentIndex(i)
                break

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._try_accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout()
        form.addRow("タグ名（必須）:", self._name_input)
        form.addRow("フィールド型:", self._type_combo)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _try_accept(self) -> None:
        if self._name_input.text().strip():
            self.accept()

    def get_name(self) -> str:
        return self._name_input.text()

    def get_field_type(self) -> str:
        return self._type_combo.currentData()


class _TemplateDialog(QDialog):
    """テンプレート追加・編集ダイアログ。名前と Jinja2 本文を入力する。"""

    def __init__(
        self,
        parent: QWidget | None,
        name: str = "",
        body: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("テンプレート編集")
        self.setMinimumSize(640, 480)

        self._name_input = QLineEdit(name)
        self._name_input.setPlaceholderText("必須")

        self._body_edit = QTextEdit()
        self._body_edit.setPlainText(body)
        self._body_edit.setFontFamily("Consolas, MS Gothic, monospace")
        self._body_edit.setPlaceholderText(
            "Jinja2 テンプレートを入力してください。\n"
            "例:\n"
            "{% for t in tickets %}\n"
            "- [{{ t.number }}] {{ t.title }} / {{ t.status }} / 期限: {{ t.end_date | jdate }}\n"
            "{% endfor %}"
        )

        help_label = QLabel(
            "利用可能変数: t.number, t.title, t.status, t.assignee, "
            "t.start_date, t.end_date, t.note, t.tags['タグ名']\n"
            "独自フィルター: "
            "{{ t.end_date | jdate }}  →  2026年03月18日(水)  / "
            "tickets | groupby_tag('タグ名')  →  タグでグループ化（日本語タグ名対応）"
        )
        help_label.setStyleSheet("color: gray; font-size: 11px;")
        help_label.setWordWrap(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._try_accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout()
        form.addRow("テンプレート名:", self._name_input)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(QLabel("テンプレート本文 (Jinja2):"))
        layout.addWidget(self._body_edit, stretch=1)
        layout.addWidget(help_label)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _try_accept(self) -> None:
        if self._name_input.text().strip() and self._body_edit.toPlainText().strip():
            self.accept()
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "入力エラー", "テンプレート名と本文は必須です。")

    def get_name(self) -> str:
        return self._name_input.text()

    def get_body(self) -> str:
        return self._body_edit.toPlainText()
