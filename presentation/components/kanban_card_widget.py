"""presentation/components/kanban_card_widget.py - カンバンカード1枚のウィジェット。"""

from PyQt6.QtCore import Qt, QMimeData, QPoint
from PyQt6.QtGui import QDrag, QFont, QMouseEvent
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from domain.ticket import Ticket


class KanbanCardWidget(QFrame):
    """カンバンボード上の1チケットカード。

    表示項目: チケット番号・タイトル・担当者名・終了予定日
    manager権限時はドラッグ可能。クリックで on_click コールバックを呼ぶ。
    """

    _MIME_TYPE = "application/x-kanban-ticket-id"

    def __init__(
        self,
        ticket: Ticket,
        display_number: str,
        assignee_name: str,
        on_click,
        draggable: bool = False,
    ) -> None:
        super().__init__()
        self._ticket = ticket
        self._on_click = on_click
        self._draggable = draggable
        self._drag_start: QPoint | None = None
        self._build_ui(display_number, assignee_name)

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _build_ui(self, display_number: str, assignee_name: str) -> None:
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setStyleSheet(
            "KanbanCardWidget {"
            "  background: white;"
            "  border: 1px solid #ccc;"
            "  border-radius: 4px;"
            "}"
            "KanbanCardWidget:hover {"
            "  border: 1px solid #888;"
            "}"
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        number_label = QLabel(display_number)
        number_label.setStyleSheet("color: #666; font-size: 10px;")

        title_label = QLabel(self._ticket.title)
        title_label.setWordWrap(True)
        font = title_label.font()
        font.setWeight(QFont.Weight.Medium)
        title_label.setFont(font)

        meta_parts = []
        if assignee_name:
            meta_parts.append(assignee_name)
        if self._ticket.end_date:
            meta_parts.append(f"〜{self._ticket.end_date}")
        meta_label = QLabel(" / ".join(meta_parts))
        meta_label.setStyleSheet("color: #555; font-size: 11px;")

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)
        layout.addWidget(number_label)
        layout.addWidget(title_label)
        layout.addWidget(meta_label)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # ドラッグ&ドロップ (manager のみ)
    # ------------------------------------------------------------------

    def set_draggable(self, enabled: bool) -> None:
        self._draggable = enabled

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._draggable:
            return
        if self._drag_start is None:
            return
        if (event.position().toPoint() - self._drag_start).manhattanLength() < 10:
            return

        mime = QMimeData()
        mime.setData(
            self._MIME_TYPE, str(self._ticket.id).encode()
        )

        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)
        self._drag_start = None

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._drag_start is not None
            and (event.position().toPoint() - self._drag_start).manhattanLength() < 10
        ):
            # クリック（ドラッグ距離が小さい）
            self._on_click(self._ticket.id)
        self._drag_start = None
        super().mouseReleaseEvent(event)

    @property
    def ticket_id(self) -> int:
        return self._ticket.id

    @classmethod
    def mime_type(cls) -> str:
        return cls._MIME_TYPE
