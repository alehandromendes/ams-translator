"""
@description Overlay estilo "Ferramenta de Captura" do Windows: mostra um congelado da
             tela (visível), escurece de leve, linhas-guia sob o cursor e a área
             selecionada em brilho normal. Devolve a região em pixels reais da tela.
@connects instanciado por overlay.gallery ao clicar "Definir região"
"""
from __future__ import annotations

from PIL import Image
from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QImage,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QWidget


def _grab_desktop() -> tuple[QPixmap, QPoint] | tuple[None, QPoint]:
    """Congelado do desktop inteiro. Retorna (pixmap, origem_em_px_reais)."""
    try:
        import mss

        with mss.mss() as sct:
            mon = sct.monitors[0]  # bounding box de todos os monitores
            raw = sct.grab(mon)
            img = Image.frombytes("RGB", raw.size, raw.rgb).convert("RGBA")
            qimg = QImage(img.tobytes("raw", "RGBA"), img.width, img.height,
                          QImage.Format_RGBA8888)
            return QPixmap.fromImage(qimg.copy()), QPoint(mon["left"], mon["top"])
    except Exception:  # noqa: BLE001
        return None, QPoint(0, 0)


class RegionSelector(QWidget):
    selected = Signal(dict)   # {"left", "top", "width", "height"} em px reais
    closed = Signal()         # fechou (com ou sem seleção)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)

        self._shot, self._shot_origin = _grab_desktop()

        geo = QRect()
        for screen in QGuiApplication.screens():
            geo = geo.united(screen.geometry())
        self._geo = geo
        self.setGeometry(geo)

        self._start: QPoint | None = None
        self._end: QPoint | None = None
        self._cursor = QPoint(0, 0)

    def showEvent(self, e) -> None:
        super().showEvent(e)
        self.activateWindow()
        self.raise_()
        self.setFocus(Qt.OtherFocusReason)

    # ---- geometria ------------------------------------------------------
    def _selection(self) -> QRect | None:
        if self._start is None or self._end is None:
            return None
        return QRect(self._start, self._end).normalized().intersected(self.rect())

    def _to_shot(self, r: QRect) -> QRect:
        """widget (px lógicos) → pixels do screenshot."""
        if self._shot is None:
            return r
        sx = self._shot.width() / max(1, self.width())
        sy = self._shot.height() / max(1, self.height())
        return QRect(round(r.x() * sx), round(r.y() * sy),
                     round(r.width() * sx), round(r.height() * sy))

    # ---- desenho ------------------------------------------------------
    def paintEvent(self, _event) -> None:
        p = QPainter(self)

        if self._shot is not None:
            p.drawPixmap(self.rect(), self._shot)
        else:
            p.fillRect(self.rect(), QColor(20, 22, 30))

        p.fillRect(self.rect(), QColor(10, 12, 18, 128))  # escurecimento (~50%)

        sel = self._selection()
        if sel and sel.width() > 1 and sel.height() > 1:
            if self._shot is not None:
                p.drawPixmap(sel, self._shot, self._to_shot(sel))  # área em brilho normal
            p.setPen(QPen(QColor("#4f8cff"), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRect(sel)
            self._badge(p, sel)
        else:
            p.setPen(QPen(QColor(255, 255, 255, 120), 1, Qt.DashLine))
            p.drawLine(self._cursor.x(), self.rect().top(),
                       self._cursor.x(), self.rect().bottom())
            p.drawLine(self.rect().left(), self._cursor.y(),
                       self.rect().right(), self._cursor.y())

        self._hint(p)

    def _badge(self, p: QPainter, sel: QRect) -> None:
        shot = self._to_shot(sel)
        txt = f"{shot.width()} × {shot.height()}"
        p.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
        fm = p.fontMetrics()
        w = fm.horizontalAdvance(txt) + 16
        h = fm.height() + 8
        x = min(sel.x(), self.width() - w - 4)
        y = sel.y() - h - 6
        if y < 4:
            y = sel.y() + 6
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(17, 24, 39, 235))
        p.drawRoundedRect(x, y, w, h, 6, 6)
        p.setPen(QColor("#e3e5e8"))
        p.drawText(x + 8, y + fm.ascent() + 4, txt)

    def _hint(self, p: QPainter) -> None:
        txt = ("Arraste sobre a faixa da legenda  ·  Esc cancela   "
               "(dica: uma faixa baixa e larga fica mais rápida e precisa)")
        p.setFont(QFont("Segoe UI", 10))
        fm = p.fontMetrics()
        w = fm.horizontalAdvance(txt) + 28
        h = fm.height() + 16
        x = (self.width() - w) // 2
        y = 28
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(17, 24, 39, 220))
        p.drawRoundedRect(x, y, w, h, 8, 8)
        p.setPen(QColor("#e3e5e8"))
        p.drawText(x + 14, y + fm.ascent() + 8, txt)

    # ---- mouse / teclado ---------------------------------------------
    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton:
            self._start = e.position().toPoint()
            self._end = self._start
            self.update()

    def mouseMoveEvent(self, e) -> None:
        self._cursor = e.position().toPoint()
        if self._start is not None:
            self._end = self._cursor
        self.update()

    def mouseReleaseEvent(self, e) -> None:
        if e.button() != Qt.LeftButton or self._start is None:
            return
        self._end = e.position().toPoint()
        sel = self._selection()
        if sel and sel.width() > 8 and sel.height() > 8:
            shot = self._to_shot(sel)
            self.selected.emit({
                "left": self._shot_origin.x() + shot.x(),
                "top": self._shot_origin.y() + shot.y(),
                "width": shot.width(),
                "height": shot.height(),
            })
        self.close()

    def keyPressEvent(self, e) -> None:
        if e.key() == Qt.Key_Escape:
            self.close()

    def closeEvent(self, e) -> None:
        self.closed.emit()
        super().closeEvent(e)
