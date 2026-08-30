"""
@description Diálogo de atalhos globais — layout compacto, uma linha por ação, com
             até 2 campos de tecla (clique no campo e aperte). 4 ações: capturar
             região / tela inteira / página anterior / próxima.
@connects aberto por overlay.gallery; devolve {"region","full","prev","next"} -> list[str]
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import icons

_MODS = [
    (Qt.ControlModifier, "ctrl"),
    (Qt.AltModifier, "alt"),
    (Qt.ShiftModifier, "shift"),
    (Qt.MetaModifier, "windows"),
]
_MOD_KEYS = {Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta}


def _qt_to_kbd(key: int, mods) -> str | None:
    if key in _MOD_KEYS or key == 0:
        return None
    text = QKeySequence(key).toString()
    if not text:
        return None
    parts = [name for flag, name in _MODS if mods & flag]
    parts.append(text.lower())
    return "+".join(parts)


class _KeyField(QPushButton):
    """Clique → escuta a próxima combinação. Backspace/Delete limpa. Esc cancela."""

    def __init__(self, value: str = "", optional: bool = False) -> None:
        super().__init__()
        self._value = value.strip().lower()
        self._optional = optional
        self._listening = False
        self.setObjectName("KeyField")
        self.setCheckable(False)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFixedHeight(30)
        self.setMinimumWidth(118)
        self.clicked.connect(self._start)
        self._refresh()

    def value(self) -> str:
        return self._value

    def _refresh(self) -> None:
        if self._listening:
            self.setText("aperte a tecla…")
        elif self._value:
            self.setText(self._value.upper())
        else:
            self.setText("+ tecla" if self._optional else "definir")
        self.setProperty("state",
                         "listening" if self._listening
                         else ("set" if self._value else "empty"))
        self.style().unpolish(self)
        self.style().polish(self)

    def _start(self) -> None:
        if self._listening:
            return
        self._listening = True
        self.setFocus(Qt.OtherFocusReason)
        self.grabKeyboard()
        self._refresh()

    def _stop(self) -> None:
        self._listening = False
        self.releaseKeyboard()
        self._refresh()

    def focusOutEvent(self, e) -> None:
        if self._listening:
            self._stop()
        super().focusOutEvent(e)

    def keyPressEvent(self, e) -> None:
        if not self._listening:
            return super().keyPressEvent(e)
        k = e.key()
        if k == Qt.Key_Escape:
            self._stop()
            return
        if k in (Qt.Key_Backspace, Qt.Key_Delete):
            self._value = ""
            self._stop()
            return
        combo = _qt_to_kbd(k, e.modifiers())
        if combo:
            self._value = combo
            self._stop()


class _Row(QWidget):
    def __init__(self, grid: QGridLayout, r: int, icon_name: str,
                 label: str, sub: str, values: list[str]) -> None:
        super().__init__()
        ic = QLabel()
        ic.setPixmap(icons.pixmap(icon_name, 17, "#cfd3da"))
        ic.setFixedWidth(24)

        txt = QWidget()
        tl = QVBoxLayout(txt)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(1)
        a = QLabel(label)
        a.setObjectName("RowTitle")
        b = QLabel(sub)
        b.setObjectName("RowSub")
        tl.addWidget(a)
        tl.addWidget(b)

        self.f1 = _KeyField(values[0] if values else "")
        self.f2 = _KeyField(values[1] if len(values) > 1 else "", optional=True)

        fields = QHBoxLayout()
        fields.setContentsMargins(0, 0, 0, 0)
        fields.setSpacing(6)
        fields.addWidget(self.f1)
        fields.addWidget(self.f2)
        fw = QWidget()
        fw.setLayout(fields)

        grid.addWidget(ic, r, 0)
        grid.addWidget(txt, r, 1)
        grid.addWidget(fw, r, 2, Qt.AlignRight)

    def values(self) -> list[str]:
        out: list[str] = []
        for v in (self.f1.value(), self.f2.value()):
            if v and v not in out:
                out.append(v)
        return out


class HotkeyDialog(QDialog):
    def __init__(self, groups: dict[str, list[str]], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Atalhos globais")
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(14)

        hint = QLabel(
            "Funcionam <b>com o jogo em foco</b>. Clique no campo e aperte a "
            "combinação. Backspace limpa, Esc cancela. Evite teclas do jogo."
        )
        hint.setWordWrap(True)
        hint.setObjectName("DialogHint")
        root.addWidget(hint)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(1, 1)

        self._region = _Row(grid, 0, "region", "Capturar região",
                            "print da faixa pré-configurada", groups.get("region", []))
        self._full = _Row(grid, 1, "monitor", "Capturar tela inteira",
                          "print da tela toda", groups.get("full", []))
        self._prev = _Row(grid, 2, "chevron-left", "Página anterior",
                          "volta uma tradução na galeria", groups.get("prev", []))
        self._next = _Row(grid, 3, "chevron-right", "Próxima página",
                          "avança uma tradução na galeria", groups.get("next", []))
        root.addLayout(grid)

        root.addStretch(1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Salvar")
        ok.setObjectName("Primary")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        footer.addWidget(cancel)
        footer.addWidget(ok)
        root.addLayout(footer)

        self.setFixedWidth(520)
        self.adjustSize()

    def result_groups(self) -> dict[str, list[str]]:
        return {
            "region": self._region.values(),
            "full": self._full.values(),
            "prev": self._prev.values(),
            "next": self._next.values(),
        }
