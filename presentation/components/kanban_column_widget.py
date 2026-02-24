"""presentation/components/kanban_column_widget.py - カンバンの1列（ステータス列）ウィジェット。"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from domain.status import Status
from presentation.components.kanban_card_widget import KanbanCardWidget


class KanbanColumnWidget(QFrame):
    """カンバンボードの1列（ステータス列）。

    ヘッダーにステータス名、ボディにカードを縦積みで表示する。
    card_dropped シグナルでドロップ時の (ticket_id, status_id) を通知する。
    """

    card_dropped = pyqtSignal(int, int)  # (ticket_id, new_status_id)

    def __init__(self, status: Status, accept_drops: bool = False) -> None:
        super().__init__()
        self._status = status
        self._cards: list[KanbanCardWidget] = []
        self._build_ui()
        self.setAcceptDrops(accept_drops)

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumWidth(160)
        self.setStyleSheet(
            "KanbanColumnWidget { background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; }"
        )

        # ヘッダー
        header = QLabel(self._status.name)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = header.font()
        font.setWeight(QFont.Weight.Bold)
        header.setFont(font)
        header.setStyleSheet(
            "background: #ddd; padding: 6px; border-radius: 4px 4px 0 0;"
        )

        # カード用スクロール領域
        self._card_container = QWidget()
        self._card_layout = QVBoxLayout()
        self._card_layout.setContentsMargins(4, 4, 4, 4)
        self._card_layout.setSpacing(6)
        self._card_layout.addStretch()
        self._card_container.setLayout(self._card_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._card_container)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(header)
        layout.addWidget(scroll)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # カード操作
    # ------------------------------------------------------------------

    def set_status(self, status: Status) -> None:
        self._status = status

    def add_card(self, card: KanbanCardWidget) -> None:
        """カードを末尾（stretch の前）に追加する。"""
        count = self._card_layout.count()
        self._card_layout.insertWidget(count - 1, card)
        self._cards.append(card)

    def clear_cards(self) -> None:
        """全カードを削除する。"""
        for card in self._cards:
            self._card_layout.removeWidget(card)
            card.setParent(None)
        self._cards.clear()

    @property
    def status_id(self) -> int:
        return self._status.id

    # ------------------------------------------------------------------
    # ドロップ受け入れ（manager のみ）
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasFormat(KanbanCardWidget.mime_type()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        data = event.mimeData().data(KanbanCardWidget.mime_type())
        ticket_id = int(data.data().decode())
        self.card_dropped.emit(ticket_id, self._status.id)
        event.acceptProposedAction()
