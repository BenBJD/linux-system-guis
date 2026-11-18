"""Loading modal with smooth custom-painted spinner and background worker execution,
plus structured option catalog row widgets for dialog lists.
"""

from collections.abc import Callable
from typing import Any, TypeVar

from PyQt6.QtCore import QEventLoop, QRectF, QSize, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

T = TypeVar("T")


class LoadingSpinner(QWidget):
    """Smooth custom-painted rotating arc spinner."""

    def __init__(self, size: int = 36, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle: int = 0
        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._advance)

    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _advance(self) -> None:
        self._angle = (self._angle + 12) % 360
        self.update()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.start()

    def hideEvent(self, event) -> None:  # noqa: N802
        self.stop()
        super().hideEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        pen_width = 3.5
        margin = pen_width + 2.0
        rect = QRectF(
            margin,
            margin,
            self.width() - 2 * margin,
            self.height() - 2 * margin,
        )

        # Subtle circular track
        track_pen = QPen(QColor("#2d3036"), pen_width)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawEllipse(rect)

        # Rotating active arc (Qt angles are in 1/16th of a degree, counter-clockwise)
        arc_pen = QPen(QColor("#4c8bf5"), pen_width)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arc_pen)
        start_angle = int(-self._angle * 16)
        span_angle = int(-110 * 16)
        painter.drawArc(rect, start_angle, span_angle)
        painter.end()


class LoadingModal(QFrame):
    """In-window modal overlay (or non-activating popup when parentless) displaying an animated
    spinner and status text while background tasks run, without creating transient Wayland
    xdg_toplevel surfaces or orphaned xdg_activation_v1 startup notification tokens.
    """

    _active_instance: "LoadingModal | None" = None

    def __init__(
        self,
        title: str = "Loading...",
        subtitle: str = "Reading system configuration...",
        parent: QWidget | None = None,
    ) -> None:
        if parent is not None:
            super().__init__(parent)
            self.setObjectName("loadingModalOverlay")
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            self.setGeometry(parent.rect())
        else:
            super().__init__(
                None,
                Qt.WindowType.ToolTip
                | Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.BypassWindowManagerHint,
            )
            self.setObjectName("loadingModalOverlay")
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
            self.setFixedSize(420, 114)

        self.setStyleSheet(
            """
            QFrame#loadingModalOverlay {
                background-color: rgba(15, 17, 20, 165);
                border: none;
            }
            QFrame#loadingModalCard {
                background-color: #202226;
                border: 1px solid #3a3d45;
                border-radius: 6px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
            """
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.card = QFrame(self)
        self.card.setObjectName("loadingModalCard")
        self.card.setFixedSize(420, 114)

        root = QHBoxLayout(self.card)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(18)

        self.spinner = LoadingSpinner(size=38, parent=self.card)
        root.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_title = QLabel(title, self.card)
        self.lbl_title.setStyleSheet("color: #e3e5e8; font-size: 14px; font-weight: 600;")
        text_col.addWidget(self.lbl_title)

        self.lbl_subtitle = QLabel(subtitle, self.card)
        self.lbl_subtitle.setWordWrap(True)
        self.lbl_subtitle.setStyleSheet("color: #9ea4b0; font-size: 12px;")
        text_col.addWidget(self.lbl_subtitle)

        root.addLayout(text_col, stretch=1)
        outer.addWidget(self.card, alignment=Qt.AlignmentFlag.AlignCenter)

    def sync_to_parent(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())

    def set_status(self, title: str | None = None, subtitle: str | None = None) -> None:
        if title is not None:
            self.lbl_title.setText(title)
        if subtitle is not None:
            self.lbl_subtitle.setText(subtitle)


class _BackgroundWorker(QThread):
    """Runs a callable in a background QThread so the GUI event loop stays responsive."""

    finishedWork = pyqtSignal()

    def __init__(self, fn: Callable[[], Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fn = fn
        self.result: Any = None
        self.error: BaseException | None = None

    def run(self) -> None:
        try:
            self.result = self._fn()
        except BaseException as exc:  # noqa: BLE001
            self.error = exc
        finally:
            self.finishedWork.emit()


def run_with_loading_modal(
    parent: QWidget | None,
    title: str,
    subtitle: str,
    task_fn: Callable[[], T],
    *,
    force_show: bool = False,
) -> T:
    """Execute ``task_fn`` in a background thread while displaying a modal spinner dialog
    so the UI thread never freezes.

    When running in headless tests where no top-level window is visible (and ``force_show``
    is False), ``task_fn`` executes directly without opening a window.
    """
    app = QApplication.instance()
    existing_modal = LoadingModal._active_instance
    has_visible_window = (
        force_show
        or (existing_modal is not None and existing_modal.isVisible())
        or (
            isinstance(app, QApplication)
            and any(w.isVisible() for w in app.topLevelWidgets())
        )
    )
    if not has_visible_window:
        return task_fn()

    owns_modal = False
    if existing_modal is not None and existing_modal.isVisible():
        modal = existing_modal
        modal.set_status(title=title, subtitle=subtitle)
        modal.sync_to_parent()
    else:
        host = parent.window() if isinstance(parent, QWidget) else None
        modal = LoadingModal(title=title, subtitle=subtitle, parent=host)
        LoadingModal._active_instance = modal
        owns_modal = True
        modal.sync_to_parent()
        modal.show()
        modal.raise_()

    QApplication.processEvents()

    loop = QEventLoop()
    worker = _BackgroundWorker(task_fn, parent=modal)
    worker.finishedWork.connect(loop.quit)
    worker.start()
    loop.exec()
    worker.wait()

    if owns_modal:
        if LoadingModal._active_instance is modal:
            LoadingModal._active_instance = None
        modal.close()
        modal.deleteLater()

    if worker.error is not None:
        raise worker.error
    return worker.result


class OptionCatalogRowWidget(QFrame):
    """Spacious, structured row widget for searchable option/attribute catalog dialogs."""

    def __init__(
        self,
        directive: str,
        title: str,
        description: str,
        note: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("optionCatalogRow")
        self.setStyleSheet(
            """
            QFrame#optionCatalogRow {
                background: transparent;
                border: none;
                border-bottom: 1px solid #2b2e36;
            }
            QLabel {
                border: none;
                background: transparent;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(10)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #e6edf3; font-size: 13px; font-weight: 600;")
        top_row.addWidget(lbl_title)

        lbl_code = QLabel(directive)
        lbl_code.setStyleSheet(
            "font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #79c0ff; "
            "background-color: #24272e; border: 1px solid #363a45; border-radius: 3px; "
            "padding: 2px 7px;"
        )
        top_row.addWidget(lbl_code)

        top_row.addStretch()

        if note and note.lower() not in ("safe", "standard", "safe match", "user interface"):
            lbl_note = QLabel(note)
            lbl_note.setStyleSheet(
                "color: #9ea4b0; background-color: #252830; border-radius: 3px; "
                "font-size: 11px; padding: 2px 6px;"
            )
            top_row.addWidget(lbl_note)

        layout.addLayout(top_row)

        lbl_desc = QLabel(description)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #a9b0bc; font-size: 12px; line-height: 1.4;")
        layout.addWidget(lbl_desc)


def populate_option_catalog_list(
    list_widget: QListWidget,
    entries: list[tuple[str, str, str, str]],
) -> None:
    """Populate ``list_widget`` with structured ``OptionCatalogRowWidget`` rows.

    Each tuple in ``entries`` is ``(directive_token, title, description, note)``.
    Stores ``directive_token`` in ``Qt.ItemDataRole.UserRole`` and searchable text in
    ``Qt.ItemDataRole.UserRole + 1``.
    """
    list_widget.clear()
    list_widget.setSpacing(2)
    list_widget.setUniformItemSizes(False)
    list_widget.setStyleSheet(
        """
        QListWidget {
            background-color: #18191c;
            border: 1px solid #32353e;
            border-radius: 4px;
            padding: 4px;
        }
        QListWidget::item {
            border-radius: 4px;
            padding: 0px;
        }
        QListWidget::item:hover {
            background-color: #22252c;
        }
        QListWidget::item:selected {
            background-color: #1f3252;
            border: 1px solid #3574d4;
        }
        """
    )

    for directive, title, desc, note in entries:
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, directive)
        search_corpus = f"{directive} {title} {desc} {note}".lower()
        item.setData(Qt.ItemDataRole.UserRole + 1, search_corpus)

        row_widget = OptionCatalogRowWidget(directive, title, desc, note)
        hint = row_widget.sizeHint()
        item.setSizeHint(QSize(hint.width(), max(68, hint.height() + 6)))

        list_widget.addItem(item)
        list_widget.setItemWidget(item, row_widget)
