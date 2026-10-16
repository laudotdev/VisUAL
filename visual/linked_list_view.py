"""Responsive painter-based singly linked-list diagram."""
from __future__ import annotations

from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont
from PySide6.QtWidgets import QWidget


def reachable_node_positions(snapshot: dict) -> tuple[list[dict], dict[int, int], bool]:
    """Derive presentation positions from the current head/next chain."""
    raw_nodes = snapshot.get("nodes")
    if not isinstance(raw_nodes, list):
        return [], {}, False
    by_id = {
        node.get("id"): node for node in raw_nodes
        if isinstance(node, dict) and isinstance(node.get("id"), int)
    }
    head = snapshot.get("head_ref")
    if head is None:
        return [], {}, False
    ordered, positions, visited = [], {}, set()
    current = head
    cycle = False
    while isinstance(current, int) and current in by_id:
        if current in visited:
            cycle = True
            break
        visited.add(current)
        positions[current] = len(ordered) + 1
        ordered.append(by_id[current])
        current = by_id[current].get("next")
    return ordered, positions, cycle


def node_display_data(node: dict):
    """Return only the trace's actual Node.data field for rendering."""
    return node.get("data") if isinstance(node, dict) and "data" in node else None


def node_rank_label(rank: int) -> str:
    """Return a display label for a node based on its linked-list order."""
    return f"Node {rank}"


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
        node_w, node_h, gap_x, gap_y, margin_x, margin_y = 155, 90, 44, 48, 20, 48
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
        nodes, positions, cycle = reachable_node_positions(self._snapshot)
        head_ref = self._snapshot.get("head_ref")
        traversed_ref = self._snapshot.get("traversed_node_ref")
        if not self._snapshot:
            painter.setPen(QColor("#c5cbd3"))
            painter.drawText(self.rect(), Qt.AlignCenter, "No visualization snapshot available.")
            return
        if head_ref is None:
            painter.setPen(QColor("#c5cbd3"))
            painter.setFont(QFont("Sans Serif", 12, QFont.Bold))
            painter.drawText(self.rect(), Qt.AlignCenter, "Empty Linked List\n\nhead  →  None\n\nNo nodes exist in this list yet.")
            return
        if not nodes:
            painter.setPen(QColor("#f0b35b"))
            painter.drawText(self.rect(), Qt.AlignCenter, "The head reference is unavailable in this snapshot.")
            return

        node_w, node_h, gap_x, gap_y = 148, 62, 44, 48
        margin_x, margin_y = 20, 48
        usable = max(1, width - 2 * margin_x)
        per_row = max(1, (usable + gap_x) // (node_w + gap_x))
        rects = {}
        node_rank = {}
        for i, node in enumerate(nodes):
            row, col = divmod(i, per_row)
            x = margin_x + col * (node_w + gap_x)
            y = margin_y + row * (node_h + gap_y)
            rects[node["id"]] = QRectF(x, y, node_w, node_h)
            node_rank[node["id"]] = i + 1

        # Head marker points to the first node when visible.
        first = nodes[0]
        head_rect = rects[first["id"]]
        painter.setPen(QPen(QColor("#80cbc4"), 2))
        painter.setFont(QFont("Sans Serif", 10, QFont.Bold))
        painter.drawText(int(head_rect.left()), int(head_rect.top() - 18), "HEAD")
        painter.drawLine(int(head_rect.left() + 2), int(head_rect.top() - 8), int(head_rect.left() + 2), int(head_rect.top()))

        for node in nodes:
            rect = rects[node["id"]]
            is_traversed = node["id"] == traversed_ref
            painter.setPen(QPen(QColor("#66bb6a" if is_traversed else "#78a9ff"), 2 if is_traversed else 1.5))
            painter.setBrush(QBrush(QColor("#315c38" if is_traversed else "#29384d")))
            painter.drawRoundedRect(rect, 7, 7)
            split_x = rect.left() + rect.width() * 0.66
            painter.drawLine(int(split_x), int(rect.top()), int(split_x), int(rect.bottom()))

            left_width = split_x - rect.left() - 8
            value_top = rect.top() + 5
            object_top = rect.top() + 30

            painter.setPen(QColor("#f1f3f4"))
            painter.setFont(QFont("Sans Serif", 10, QFont.Bold))
            painter.drawText(QRectF(rect.left() + 4, value_top, left_width, 20), Qt.AlignCenter, str(node_display_data(node)))

            painter.setFont(QFont("Sans Serif", 8))
            painter.setPen(QColor("#b8c7db"))
            painter.drawText(QRectF(rect.left() + 4, object_top, left_width, 16), Qt.AlignCenter, f"{node_rank_label(node_rank[node['id']])}")
            painter.drawText(QRectF(rect.left() + 4, object_top + 14, left_width, 14), Qt.AlignCenter, f"Object #{node['id']}")

            painter.setPen(QColor("#c7d6e8"))
            painter.drawText(QRectF(split_x + 2, rect.top() + 5, rect.right() - split_x - 4, rect.height() - 10), Qt.AlignCenter, "next")

        for node in nodes:
            rect = rects[node["id"]]
            next_id = node.get("next")
            if next_id in rects:
                target = rects[next_id]
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
