"""
@description Painel lateral "digitar e traduzir" — direção inversa (português → chinês
             simplificado). Traduz ao clicar, no Ctrl+Enter, ou 0,8 s após parar de digitar.
@connects instanciado por overlay.gallery; usa overlay.translator.translate_text
"""
from __future__ import annotations

import threading

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import icons


class ReversePanel(QWidget):
    _result = Signal(str, bool, int)

    def __init__(self, cfg: dict) -> None:
        super().__init__()
        self.cfg = cfg
        self._seq = 0

        self.setObjectName("ReversePanel")
        self.setMinimumWidth(270)
        self.setMaximumWidth(480)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        title = QLabel("Digitar e traduzir")
        title.setObjectName("HeaderTitle")
        self.sub = QLabel("português → 中文 (simplificado)")
        self.sub.setObjectName("HeaderSub")
        lay.addWidget(title)
        lay.addWidget(self.sub)

        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("Digite em português…  (Ctrl+Enter traduz)")
        self.input.setFixedHeight(150)
        lay.addWidget(self.input)

        self.btn = QPushButton("Traduzir")
        self.btn.setObjectName("Primary")
        self.btn.setIcon(icons.icon("arrow-right", "#ffffff"))
        self.btn.setLayoutDirection(Qt.RightToLeft)
        self.btn.clicked.connect(self.translate_now)
        lay.addWidget(self.btn)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("O texto em chinês aparece aqui.")
        of = QFont()
        of.setPointSize(16)
        self.output.setFont(of)
        lay.addWidget(self.output, 1)

        self.btn_copy = QPushButton(icons.icon("copy"), "  Copiar 中文")
        self.btn_copy.clicked.connect(self._copy)
        lay.addWidget(self.btn_copy)

        for seq in ("Ctrl+Return", "Ctrl+Enter"):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.WidgetWithChildrenShortcut)
            sc.activated.connect(self.translate_now)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(800)
        self._debounce.timeout.connect(self.translate_now)
        self.input.textChanged.connect(self._debounce.start)

        self._result.connect(self._on_result)

    def translate_now(self) -> None:
        self._debounce.stop()
        txt = self.input.toPlainText().strip()
        if not txt:
            self.output.setPlainText("")
            return
        self._seq += 1
        seq = self._seq
        self.btn.setEnabled(False)
        self.output.setPlaceholderText("traduzindo…")
        threading.Thread(target=self._work, args=(txt, seq), daemon=True).start()

    def _work(self, txt: str, seq: int) -> None:
        from . import translator

        res, ok = translator.translate_text(
            txt,
            self.cfg.get("reverse_source", "pt"),
            self.cfg.get("reverse_target", "zh-CN"),
        )
        self._result.emit(res, ok, seq)

    def _on_result(self, res: str, ok: bool, seq: int) -> None:
        if seq != self._seq:
            return
        self.btn.setEnabled(True)
        self.output.setPlaceholderText("O texto em chinês aparece aqui.")
        self.output.setPlainText(
            res if ok else "(tradução falhou — clique em Traduzir de novo)"
        )

    def _copy(self) -> None:
        t = self.output.toPlainText().strip()
        if t and not t.startswith("("):
            QApplication.clipboard().setText(t)
