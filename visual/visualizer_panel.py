"""VisUAL step-through panel, separate from the IDE Output and Terminal."""
from __future__ import annotations

from html import escape
import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QScrollArea, QGroupBox, QPlainTextEdit,
)

from .linked_list_view import LinkedListView
from .presentation import format_variable_explanations
from ui.panel_icons import ICON_SIZE, panel_icon


class VisualizerPanel(QWidget):
    # Keep the visualization viewport stable while allowing its contents to scroll.
    VISUALIZATION_VIEWPORT_HEIGHT = 320

    close_requested = Signal()
    source_requested = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.snapshots: list[dict] = []
        self.program_output: list[str] = []
        self.current_index = 0
        self._build_ui()

    @staticmethod
    def _explanation_html(event_type: str, explanation: str) -> str:
        """Render trace prose as readable rich text, including inline code."""
        text = escape(f"{event_type}: {explanation}", quote=False)
        text = re.sub(r"`([^`]+)`", r'<span style="color:#8be9fd; font-weight:800">\1</span>', text)
        return text.replace("\n", "<br>")

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        top = QHBoxLayout()
        title = QLabel("VisUAL · Linked List")
        title.setStyleSheet("font-size: 15px; font-weight: 600;")
        top.addWidget(title)
        top.addStretch()
        self.close_button = QPushButton()
        self.close_button.setIcon(panel_icon("close"))
        self.close_button.setIconSize(ICON_SIZE)
        self.close_button.setToolTip("Close VisUAL")
        self.close_button.clicked.connect(self.close_requested.emit)
        top.addWidget(self.close_button)
        root.addLayout(top)

        self.status_label = QLabel("Run a supported linked-list program to begin.")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        self.diagram = LinkedListView()
        self.visualization_scroll = QScrollArea()
        self.visualization_scroll.setWidgetResizable(True)
        self.visualization_scroll.setWidget(self.diagram)
        self.visualization_scroll.setFixedHeight(self.VISUALIZATION_VIEWPORT_HEIGHT)
        root.addWidget(self.visualization_scroll)

        nav = QHBoxLayout()
        self.start_button = QPushButton()
        self.start_button.setIcon(panel_icon("first"))
        self.start_button.setIconSize(ICON_SIZE)
        self.start_button.setToolTip("Jump to first step")
        self.previous_button = QPushButton("← Previous")
        self.next_button = QPushButton("Next →")
        self.end_button = QPushButton()
        self.end_button.setIcon(panel_icon("last"))
        self.end_button.setIconSize(ICON_SIZE)
        self.end_button.setToolTip("Jump to last step")
        self.step_label = QLabel("Step 0 / 0")
        self.step_label.setAlignment(Qt.AlignCenter)
        self.start_button.clicked.connect(self.start_step)
        self.previous_button.clicked.connect(self.previous_step)
        self.next_button.clicked.connect(self.next_step)
        self.end_button.clicked.connect(self.end_step)
        nav.addWidget(self.start_button)
        nav.addWidget(self.previous_button)
        nav.addWidget(self.step_label, 1)
        nav.addWidget(self.next_button)
        nav.addWidget(self.end_button)
        root.addLayout(nav)

        explanation_group = QGroupBox("Step explanation")
        explanation_group.setFixedHeight(75)
        explanation_layout = QVBoxLayout(explanation_group)
        self.explanation = QLabel("No trace loaded.")
        self.explanation.setWordWrap(True)
        self.explanation.setTextInteractionFlags(Qt.TextSelectableByMouse)
        explanation_layout.addWidget(self.explanation)
        root.addWidget(explanation_group)

        bottom = QHBoxLayout()
        variables_group = QGroupBox("Variable Explanation")
        variables_layout = QVBoxLayout(variables_group)
        self.variables = QTextEdit()
        self.variables.setReadOnly(True)
        self.variables.setMaximumHeight(180)
        variables_layout.addWidget(self.variables)
        output_group = QGroupBox("Program output")
        output_layout = QVBoxLayout(output_group)
        self.program_output_view = QPlainTextEdit()
        self.program_output_view.setReadOnly(True)
        self.program_output_view.setMaximumHeight(115)
        output_layout.addWidget(self.program_output_view)
        bottom.addWidget(variables_group, 1)
        bottom.addWidget(output_group, 1)
        root.addLayout(bottom)
        self.setMinimumWidth(340)
        self.setStyleSheet("""
            QWidget { font-family: 'Inter', 'Segoe UI', sans-serif; font-weight: 700; }
            QLabel { font-size: 11px; }
            QGroupBox { font-size: 12px; font-weight: 800; }
            QPushButton { font-size: 11px; font-weight: 800; padding: 5px 8px; }
            QPlainTextEdit { font-family: 'JetBrains Mono', 'Cascadia Mono', monospace; font-weight: 700; font-size: 10px; }
        """)

    def load_trace(self, snapshots: list[dict], output: list[str], status: str, error: str | None = None):
        self.snapshots = snapshots or []
        self.program_output = output or []
        self.current_index = 0
        self.program_output_view.setPlainText("\n".join(self.program_output) or "(no output yet)")
        if error:
            self.status_label.setText(f"Visualization failed: {error}")
        else:
            self.status_label.setText(f"Trace ready · {len(self.snapshots)} recorded states · {status}")
        self._render_step()

    def previous_step(self):
        if self.current_index > 0:
            self.current_index -= 1
            self._render_step()

    def start_step(self):
        if self.snapshots and self.current_index != 0:
            self.current_index = 0
            self._render_step()

    def next_step(self):
        if self.current_index < len(self.snapshots) - 1:
            self.current_index += 1
            self._render_step()

    def end_step(self):
        if self.snapshots and self.current_index != len(self.snapshots) - 1:
            self.current_index = len(self.snapshots) - 1
            self._render_step()

    def _render_step(self):
        total = len(self.snapshots)
        has_trace = total > 0
        self.previous_button.setEnabled(has_trace and self.current_index > 0)
        self.next_button.setEnabled(has_trace and self.current_index < total - 1)
        self.start_button.setEnabled(has_trace and self.current_index > 0)
        self.end_button.setEnabled(has_trace and self.current_index < total - 1)
        self.step_label.setText(f"Step {self.current_index + 1 if has_trace else 0} / {total}")
        if not has_trace:
            self.diagram.set_snapshot({})
            self.explanation.setText("No trace was produced.")
            self.variables.clear()
            return
        snapshot = self.snapshots[self.current_index]
        source = snapshot.get("source", {})
        self.source_requested.emit(
            int(source.get("line", 1)), int(source.get("column", 1))
        )
        self.diagram.set_snapshot(snapshot)
        self.explanation.setText(self._explanation_html(
            snapshot.get("event_type", "step"), snapshot.get("explanation", "")
        ))
        entries = snapshot.get("variable_explanations", {})
        self.variables.setHtml(
            format_variable_explanations(entries)
            or "(no relevant variables)"
        )   
        self.program_output_view.setPlainText("\n".join(
            snapshot.get("program_output", self.program_output)
        ) or "(no output yet)")
