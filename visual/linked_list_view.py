"""Responsive painter-based singly linked-list diagram."""
from __future__ import annotations

from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont
from PySide6.QtWidgets import QWidget


class LinkedListView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._snapshot: dict = {}
        self.setMinimumHeight(170)
        self.setMinimumWidth(260)

    def sizeHint(self) -> QSize:
        return QSize(500, self.heightForWidth(500))

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        count = len(self._snapshot.get("nodes", []))
        if count == 0:
            return 190
        node_w, node_h, gap_x, gap_y, margin_x, margin_y = 148, 62, 44, 48, 20, 48
        usable = max(1, width - 2 * margin_x)
        per_row = max(1, (usable + gap_x) // (node_w + gap_x))
        rows = (count + per_row - 1) // per_row
        return margin_y + rows * node_h + max(0, rows - 1) * gap_y + 30

    def set_snapshot(self, snapshot: dict) -> None:
        self._snapshot = snapshot or {}
        self.setMinimumHeight(self.heightForWidth(max(self.width(), 260)))
        self.updateGeometry()
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#202124"))
        width = max(1, self.width())
        nodes = self._snapshot.get("nodes", [])
        head_ref = self._snapshot.get("head_ref")
        traversed_ref = self._snapshot.get("traversed_node_ref")
        if not nodes:
            painter.setPen(QColor("#c5cbd3"))
            painter.drawText(self.rect(), Qt.AlignCenter, "head  →  None\n\n(empty linked list)")
            return

        node_w, node_h, gap_x, gap_y = 148, 62, 44, 48
        margin_x, margin_y = 20, 48
        usable = max(1, width - 2 * margin_x)
        per_row = max(1, (usable + gap_x) // (node_w + gap_x))
        positions = {}
        for i, node in enumerate(nodes):
            row, col = divmod(i, per_row)
            x = margin_x + col * (node_w + gap_x)
            y = margin_y + row * (node_h + gap_y)
            positions[node["id"]] = QRectF(x, y, node_w, node_h)

        # Head marker points to the first node when visible.
        first = nodes[0]
        head_rect = positions[first["id"]]
        painter.setPen(QPen(QColor("#80cbc4"), 2))
        painter.setFont(QFont("Sans Serif", 10, QFont.Bold))
        painter.drawText(int(head_rect.left()), int(head_rect.top() - 18), "HEAD")
        painter.drawLine(int(head_rect.left() + 2), int(head_rect.top() - 8), int(head_rect.left() + 2), int(head_rect.top()))

        for node in nodes:
            rect = positions[node["id"]]
            is_traversed = node["id"] == traversed_ref
            painter.setPen(QPen(QColor("#66bb6a" if is_traversed else "#78a9ff"), 2 if is_traversed else 1.5))
            painter.setBrush(QBrush(QColor("#315c38" if is_traversed else "#29384d")))
            painter.drawRoundedRect(rect, 7, 7)
            split_x = rect.left() + rect.width() * 0.66
            painter.drawLine(int(split_x), int(rect.top()), int(split_x), int(rect.bottom()))
            painter.setPen(QColor("#f1f3f4"))
            painter.setFont(QFont("Sans Serif", 10, QFont.Bold))
            painter.drawText(QRectF(rect.left() + 4, rect.top() + 5, split_x - rect.left() - 8, 24), Qt.AlignCenter, str(node.get("data")))
            painter.setFont(QFont("Sans Serif", 8))
            painter.setPen(QColor("#b8c7db"))
            painter.drawText(QRectF(rect.left() + 4, rect.top() + 31, split_x - rect.left() - 8, 20), Qt.AlignCenter, f"Node #{node['id']}")
            painter.setPen(QColor("#c7d6e8"))
            painter.drawText(QRectF(split_x + 2, rect.top() + 5, rect.right() - split_x - 4, rect.height() - 10), Qt.AlignCenter, "next")

        for node in nodes:
            rect = positions[node["id"]]
            next_id = node.get("next")
            if next_id in positions:
                target = positions[next_id]
                if target.top() == rect.top() and target.left() > rect.left():
                    start_x, start_y = rect.right(), rect.center().y()
                    end_x, end_y = target.left(), target.center().y()
                else:
                    start_x, start_y = rect.center().x(), rect.bottom()
                    end_x, end_y = target.center().x(), target.top()
                painter.setPen(QPen(QColor("#80cbc4"), 2))
                painter.drawLine(int(start_x), int(start_y), int(end_x - 7), int(end_y))
                painter.drawLine(int(end_x - 7), int(end_y), int(end_x - 13), int(end_y - 4))
                painter.drawLine(int(end_x - 7), int(end_y), int(end_x - 13), int(end_y + 4))
            else:
                painter.setPen(QColor("#c5cbd3"))
                painter.setFont(QFont("Sans Serif", 9))
                painter.drawText(QRectF(rect.right() - 10, rect.bottom() + 4, 90, 20), Qt.AlignLeft, "None")
