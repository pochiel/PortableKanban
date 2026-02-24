"""presentation/components/filter_widget.py - 共通フィルターウィジェット（SCR-004/006/007）。"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import QDate

from domain.filter_condition import FilterCondition, TagFilter
from domain.member import Member
from domain.status import Status
from domain.tag_definition import TagDefinition


class FilterWidget(QWidget):
    """担当者・ステータス・タグ・日付によるフィルター条件入力 UI。

    条件変更時に condition_changed シグナルを発火する。
    get_condition() で現在の FilterCondition を取得できる。
    """

    condition_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._members: list[Member] = []
        self._statuses: list[Status] = []
        self._tag_defs: list[TagDefinition] = []
        self._member_checks: list[tuple[QCheckBox, int]] = []
        self._status_checks: list[tuple[QCheckBox, int]] = []
        self._tag_filter_rows: list["_TagFilterRow"] = []
        self._build_ui()

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        # 担当者グループ
        self._member_group = QGroupBox("担当者")
        self._member_inner = QHBoxLayout()
        self._member_inner.setSpacing(4)
        self._member_group.setLayout(self._member_inner)
        layout.addWidget(self._member_group)

        # ステータスグループ
        self._status_group = QGroupBox("ステータス")
        self._status_inner = QHBoxLayout()
        self._status_inner.setSpacing(4)
        self._status_group.setLayout(self._status_inner)
        layout.addWidget(self._status_group)

        # タグ条件グループ
        tag_group = QGroupBox("タグ条件")
        tag_layout = QVBoxLayout()

        add_tag_btn = QPushButton("+ 条件を追加")
        add_tag_btn.clicked.connect(self._on_add_tag_row)
        tag_layout.addWidget(add_tag_btn)

        self._tag_rows_layout = QVBoxLayout()
        tag_layout.addLayout(self._tag_rows_layout)

        # AND/OR 切り替え
        op_layout = QHBoxLayout()
        op_layout.addWidget(QLabel("タグ条件間:"))
        self._and_radio = QRadioButton("AND")
        self._or_radio = QRadioButton("OR")
        self._and_radio.setChecked(True)
        self._and_radio.toggled.connect(self._emit_changed)
        op_layout.addWidget(self._and_radio)
        op_layout.addWidget(self._or_radio)
        op_layout.addStretch()
        tag_layout.addLayout(op_layout)

        tag_group.setLayout(tag_layout)
        layout.addWidget(tag_group)

        # 日付グループ
        date_group = QGroupBox("日付")
        date_form = QFormLayout()

        start_row = QHBoxLayout()
        self._start_from = _DateEdit()
        self._start_to = _DateEdit()
        self._start_from.changed.connect(self._emit_changed)
        self._start_to.changed.connect(self._emit_changed)
        start_row.addWidget(self._start_from)
        start_row.addWidget(QLabel("〜"))
        start_row.addWidget(self._start_to)
        date_form.addRow("開始日:", start_row)

        end_row = QHBoxLayout()
        self._end_from = _DateEdit()
        self._end_to = _DateEdit()
        self._end_from.changed.connect(self._emit_changed)
        self._end_to.changed.connect(self._emit_changed)
        end_row.addWidget(self._end_from)
        end_row.addWidget(QLabel("〜"))
        end_row.addWidget(self._end_to)
        date_form.addRow("終了予定日:", end_row)

        date_group.setLayout(date_form)
        layout.addWidget(date_group)

        layout.addStretch()
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # 外部からデータをセット
    # ------------------------------------------------------------------

    def set_members(self, members: list[Member]) -> None:
        """担当者一覧をセットしてチェックボックスを再生成する。"""
        self._members = members
        self._rebuild_checkboxes(
            self._member_inner,
            self._member_checks,
            [(m.id, m.name) for m in members],
        )

    def set_statuses(self, statuses: list[Status]) -> None:
        """ステータス一覧をセットしてチェックボックスを再生成する。"""
        self._statuses = statuses
        self._rebuild_checkboxes(
            self._status_inner,
            self._status_checks,
            [(s.id, s.name) for s in statuses],
        )

    def set_tag_definitions(self, tags: list[TagDefinition]) -> None:
        """タグ定義一覧をセットする。既存のタグフィルター行も更新する。"""
        self._tag_defs = tags
        for row in self._tag_filter_rows:
            row.set_tag_defs(tags)

    def set_default_hidden_statuses(self, status_ids: list[int]) -> None:
        """デフォルト非表示ステータスのチェックを外す。"""
        for cb, sid in self._status_checks:
            if sid in status_ids:
                cb.setChecked(False)

    # ------------------------------------------------------------------
    # フィルター条件の取得
    # ------------------------------------------------------------------

    def get_condition(self) -> FilterCondition:
        """現在のフィルター条件を FilterCondition として返す。"""
        assignee_ids = [sid for cb, sid in self._member_checks if cb.isChecked()]
        status_ids = [sid for cb, sid in self._status_checks if cb.isChecked()]

        global_op = "and" if self._and_radio.isChecked() else "or"
        tag_filters: list[TagFilter] = []
        for row in self._tag_filter_rows:
            tf = row.get_filter(global_op)
            if tf is not None:
                tag_filters.append(tf)

        return FilterCondition(
            assignee_ids=assignee_ids,
            status_ids=status_ids,
            tag_filters=tag_filters,
            start_date_from=self._start_from.get_date(),
            start_date_to=self._start_to.get_date(),
            end_date_from=self._end_from.get_date(),
            end_date_to=self._end_to.get_date(),
        )

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------

    def _rebuild_checkboxes(
        self,
        layout: QHBoxLayout,
        store: list,
        items: list[tuple[int, str]],
    ) -> None:
        """既存チェックボックスを削除して再生成する。"""
        for cb, _ in store:
            cb.setParent(None)
        store.clear()

        for item_id, label in items:
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.toggled.connect(self._emit_changed)
            layout.addWidget(cb)
            store.append((cb, item_id))

    def _on_add_tag_row(self) -> None:
        row = _TagFilterRow(self._tag_defs, on_remove=self._remove_tag_row)
        row.changed.connect(self._emit_changed)
        self._tag_filter_rows.append(row)
        self._tag_rows_layout.addWidget(row)
        self._emit_changed()

    def _remove_tag_row(self, row: "_TagFilterRow") -> None:
        self._tag_filter_rows.remove(row)
        row.setParent(None)
        self._emit_changed()

    def _emit_changed(self) -> None:
        self.condition_changed.emit()


class _TagFilterRow(QWidget):
    """タグフィルターの1行。タグ名・演算子・値・削除ボタン。"""

    changed = pyqtSignal()

    def __init__(
        self,
        tag_defs: list[TagDefinition],
        on_remove,
    ) -> None:
        super().__init__()
        self._on_remove = on_remove
        self._build_ui(tag_defs)

    def _build_ui(self, tag_defs: list[TagDefinition]) -> None:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self._tag_combo = QComboBox()
        self._op_combo = QComboBox()
        self._op_combo.addItem("含む", "include")
        self._op_combo.addItem("含まない", "not")
        self._value_input = QLineEdit()
        remove_btn = QPushButton("×")
        remove_btn.setFixedWidth(28)

        self.set_tag_defs(tag_defs)

        self._tag_combo.currentIndexChanged.connect(self.changed)
        self._op_combo.currentIndexChanged.connect(self.changed)
        self._value_input.textChanged.connect(self.changed)
        remove_btn.clicked.connect(lambda: self._on_remove(self))

        layout.addWidget(self._tag_combo)
        layout.addWidget(self._op_combo)
        layout.addWidget(self._value_input, stretch=1)
        layout.addWidget(remove_btn)
        self.setLayout(layout)

    def set_tag_defs(self, tag_defs: list[TagDefinition]) -> None:
        current_id = self._tag_combo.currentData() if self._tag_combo.count() > 0 else None
        self._tag_combo.blockSignals(True)
        self._tag_combo.clear()
        for t in tag_defs:
            self._tag_combo.addItem(t.name, t.id)
        if current_id is not None:
            for i in range(self._tag_combo.count()):
                if self._tag_combo.itemData(i) == current_id:
                    self._tag_combo.setCurrentIndex(i)
                    break
        self._tag_combo.blockSignals(False)

    def get_filter(self, global_op: str) -> TagFilter | None:
        """現在の設定を TagFilter で返す。タグ未選択なら None。"""
        tag_def_id = self._tag_combo.currentData()
        if tag_def_id is None:
            return None
        value = self._value_input.text()
        op_data = self._op_combo.currentData()
        operator = "not" if op_data == "not" else global_op
        return TagFilter(tag_def_id=tag_def_id, value=value, operator=operator)


class _DateEdit(QWidget):
    """クリア可能な日付入力ウィジェット。"""

    changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._edit = QDateEdit()
        self._edit.setCalendarPopup(True)
        self._edit.setSpecialValueText("未設定")
        self._edit.setMinimumDate(QDate(2000, 1, 1))
        self._edit.setDate(self._edit.minimumDate())  # 初期値 = minimumDate → 未設定
        self._edit.dateChanged.connect(self.changed)

        clear_btn = QPushButton("×")
        clear_btn.setFixedWidth(22)
        clear_btn.clicked.connect(self._clear)

        layout.addWidget(self._edit)
        layout.addWidget(clear_btn)
        self.setLayout(layout)

    def _clear(self) -> None:
        self._edit.setDate(self._edit.minimumDate())
        self.changed.emit()

    def get_date(self):
        """date を返す。未設定（minimumDate）なら None。"""
        from datetime import date as date_type
        qd = self._edit.date()
        if qd == self._edit.minimumDate():
            return None
        return date_type(qd.year(), qd.month(), qd.day())
