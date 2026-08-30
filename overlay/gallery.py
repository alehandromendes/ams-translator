"""
@description Janela principal — galeria paginada das capturas traduzidas (cronológica,
             máx. N páginas) com filmstrip de miniaturas, cabeçalho, atalhos globais
             configuráveis por gravação, e toggle original/traduzido.
@connects entry point do pacote (python -m overlay); usa worker, capture, region_selector,
          hotkey_dialog, style
"""
from __future__ import annotations

import sys
import time
from datetime import datetime

from PIL import Image
from PySide6.QtCore import Qt, QObject, QRectF, QSize, Signal, QTimer
from PySide6.QtGui import (
    QAction,
    QColor,
    QIcon,
    QImage,
    QKeySequence,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import capture, config, icons, style
from .frameless import FramelessMixin
from .hotkey_dialog import HotkeyDialog
from .region_selector import RegionSelector
from .reverse_panel import ReversePanel
from .win_hotkey import WinHotkeys, is_elevated
from .worker import TranslateWorker

try:
    import keyboard  # type: ignore
except Exception:  # noqa: BLE001
    keyboard = None

THUMB = QSize(172, 96)
TITLEBAR_H = 38
ACTIONBAR_H = 46


def pil_to_qpixmap(img: Image.Image) -> QPixmap:
    rgba = img.convert("RGBA")
    qimg = QImage(rgba.tobytes("raw", "RGBA"), rgba.width, rgba.height,
                  QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimg.copy())


def qimage_to_pil(qimg: QImage) -> Image.Image:
    qimg = qimg.convertToFormat(QImage.Format_RGBA8888)
    w, h = qimg.width(), qimg.height()
    buf = qimg.constBits()
    data = buf.tobytes() if hasattr(buf, "tobytes") else bytes(buf)
    return Image.frombytes("RGBA", (w, h), data[: w * h * 4]).convert("RGB")


class HotkeyBridge(QObject):
    triggered = Signal()


# a lib `keyboard` usa nomes canônicos ("page up"), não os apelidos do config
_KBD_ALIASES = {
    "pgup": "page up", "pageup": "page up", "pgdn": "page down",
    "pgdown": "page down", "pagedown": "page down", "del": "delete",
    "ins": "insert", "return": "enter", "escape": "esc",
}


def _kbd_name(hk: str) -> str:
    parts = [p.strip() for p in hk.lower().split("+")]
    return "+".join(_KBD_ALIASES.get(p, p) for p in parts)


class ImageView(QGraphicsView):
    """Mostra a captura encaixada no espaço disponível (sem distorcer) e permite
    Ctrl+scroll pra dar zoom. Imagem menor que o visor fica em 100%."""

    zoomChanged = Signal(int)   # % atual

    def __init__(self) -> None:
        super().__init__()
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._item = QGraphicsPixmapItem()
        self._item.setTransformationMode(Qt.SmoothTransformation)
        self._scene.addItem(self._item)

        self.setRenderHints(QPainter.SmoothPixmapTransform | QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setFrameShape(QFrame.NoFrame)
        self.setBackgroundBrush(QColor("#0f1012"))
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setAlignment(Qt.AlignCenter)
        self._empty = True
        self._user_zoom = False

    def set_pixmap(self, pm: QPixmap) -> None:
        self._empty = pm.isNull()
        self._item.setPixmap(pm)
        self._scene.setSceneRect(QRectF(pm.rect()))
        self.fit()

    def fit(self) -> None:
        self._user_zoom = False
        self.resetTransform()
        if self._empty:
            self.zoomChanged.emit(100)
            return
        pm = self._item.pixmap().size()
        vp = self.viewport().size()
        if pm.width() > vp.width() or pm.height() > vp.height():
            self.fitInView(self._item, Qt.KeepAspectRatio)
        self.centerOn(self._item)
        self.zoomChanged.emit(self._zoom_pct())

    def bigger_than_viewport(self) -> bool:
        if self._empty:
            return False
        pm = self._item.pixmap().size()
        vp = self.viewport().size()
        return pm.width() > vp.width() or pm.height() > vp.height()

    def _zoom_pct(self) -> int:
        return max(1, round(self.transform().m11() * 100))

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        if not self._user_zoom:
            self.fit()

    def wheelEvent(self, e) -> None:
        if (e.modifiers() & Qt.ControlModifier) and not self._empty:
            f = 1.18 if e.angleDelta().y() > 0 else 1 / 1.18
            cur = self.transform().m11()
            if 0.05 <= cur * f <= 10.0:
                self.scale(f, f)
                self._user_zoom = True
                self.zoomChanged.emit(self._zoom_pct())
            e.accept()
        else:
            super().wheelEvent(e)


class ViewerPane(QWidget):
    """ImageView + setas de navegação + dica de zoom no canto."""

    prev = Signal()
    next = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.view = ImageView()
        self.view.setParent(self)
        self.view.zoomChanged.connect(self._on_zoom)

        self.empty_lbl = QLabel(self)
        self.empty_lbl.setObjectName("ViewerEmpty")
        self.empty_lbl.setAlignment(Qt.AlignCenter)
        self.empty_lbl.setWordWrap(True)
        self.empty_lbl.hide()

        self.zoom_hint = QLabel("Ctrl + scroll para dar zoom", self)
        self.zoom_hint.setObjectName("ZoomHint")
        self.zoom_hint.hide()

        self.b_prev = QToolButton(self)
        self.b_prev.setObjectName("NavChevron")
        self.b_prev.setIcon(icons.icon("chevron-left", "#e6e9ee", sw=2.4))
        self.b_prev.setIconSize(QSize(22, 22))
        self.b_prev.setCursor(Qt.PointingHandCursor)
        self.b_prev.clicked.connect(self.prev)

        self.b_next = QToolButton(self)
        self.b_next.setObjectName("NavChevron")
        self.b_next.setIcon(icons.icon("chevron-right", "#e6e9ee", sw=2.4))
        self.b_next.setIconSize(QSize(22, 22))
        self.b_next.setCursor(Qt.PointingHandCursor)
        self.b_next.clicked.connect(self.next)

    # ---- API usada pela Gallery ------------------------------------
    def show_image(self, pm: QPixmap) -> None:
        self.empty_lbl.hide()
        self.view.show()
        self.view.set_pixmap(pm)
        self._refresh_hint()

    def show_message(self, text: str) -> None:
        self.view.hide()
        self.zoom_hint.hide()
        self.empty_lbl.setText(text)
        self.empty_lbl.show()

    def set_enabled(self, prev_on: bool, next_on: bool) -> None:
        self.b_prev.setVisible(prev_on)
        self.b_next.setVisible(next_on)

    # ---- interno --------------------------------------------------
    def _on_zoom(self, pct: int) -> None:
        self._refresh_hint(pct)

    def _refresh_hint(self, pct: int | None = None) -> None:
        if self.view.isHidden() or self.view._empty:
            self.zoom_hint.hide()
            return
        if pct is None:
            pct = self.view._zoom_pct()
        show = self.view.bigger_than_viewport() or self.view._user_zoom
        if show:
            self.zoom_hint.setText(f"Ctrl + scroll: zoom  ·  {pct}%")
            self.zoom_hint.adjustSize()
            self.zoom_hint.show()
            self._place_hint()
        else:
            self.zoom_hint.hide()

    def _place_hint(self) -> None:
        self.zoom_hint.move(self.width() - self.zoom_hint.width() - 14, 12)
        self.zoom_hint.raise_()

    def resizeEvent(self, e) -> None:
        self.view.setGeometry(self.rect())
        self.empty_lbl.setGeometry(self.rect())
        s = 46
        y = (self.height() - s) // 2
        self.b_prev.setGeometry(10, y, s, s)
        self.b_next.setGeometry(self.width() - s - 10, y, s, s)
        self.b_prev.raise_()
        self.b_next.raise_()
        self._refresh_hint()
        super().resizeEvent(e)


class Gallery(FramelessMixin, QMainWindow):
    def __init__(self, cfg: dict) -> None:
        super().__init__()
        self.cfg = cfg
        self._pending_capture: str | None = None   # 'region' após definir a área
        self.max_pages = max(1, int(cfg.get("max_pages", 10)))
        self.auto_gap = max(0.0, float(cfg.get("auto_advance_gap_seconds", 60)))
        self.pages: list[dict] = []      # cronológico: [0] mais antigo … [-1] mais novo
        self.cur = -1
        self._next_id = 1
        self._last_capture_ts = 0.0
        self._selector: RegionSelector | None = None
        self._show_translated = True
        self._hotkey_handlers: list = []      # handlers da lib `keyboard` (fallback)
        self._win_hotkeys: WinHotkeys | None = None
        self._hotkey_state = "—"
        self._film_guard = False

        self.setWindowTitle("Tradutor de Legendas")
        self.resize(1180, 820)
        self.setMinimumSize(960, 580)
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self._apply_always_on_top()

        root = QWidget()
        root.setObjectName("Root")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_titlebar())
        outer.addWidget(self._build_actionbar())
        outer.addWidget(self._build_body(), 1)
        self.setCentralWidget(root)

        self._build_statusbar()
        self.statusBar().showMessage("Iniciando…")

        # worker
        self.worker = TranslateWorker(cfg)
        self.worker.result_ready.connect(self._on_result)
        self.worker.status.connect(self._on_worker_status)
        self.worker.queue_size.connect(self._on_queue)
        self.worker.start()

        # atalhos globais — Win32 RegisterHotKey + lib `keyboard` em paralelo
        # (o que funcionar sobre o jogo dispara; debounce evita disparo duplo).
        # Conexão QUEUED: o callback do WM_HOTKEY / hook roda dentro do despacho
        # de mensagens do Win32 — a captura de verdade (que esconde a janela,
        # abre o seletor, dorme…) tem que rodar num ponto limpo do event loop,
        # senão o PRIMEIRO atalho, disparado enquanto a janela ainda se ajusta,
        # se perde.
        self._last_fire: dict[str, float] = {}
        self._bridge_region = HotkeyBridge()
        self._bridge_full = HotkeyBridge()
        self._bridge_prev = HotkeyBridge()
        self._bridge_next = HotkeyBridge()
        self._bridge_region.triggered.connect(
            lambda: self._fire("region", self.capture_region), Qt.QueuedConnection)
        self._bridge_full.triggered.connect(
            lambda: self._fire("full", self.capture_fullscreen), Qt.QueuedConnection)
        self._bridge_prev.triggered.connect(
            lambda: self._fire("prev", self.prev_page), Qt.QueuedConnection)
        self._bridge_next.triggered.connect(
            lambda: self._fire("next", self.next_page), Qt.QueuedConnection)
        if WinHotkeys is not None:
            self._win_hotkeys = WinHotkeys()
        self._register_hotkeys()

        self._refresh_region_label()
        self._refresh_hotkey_label()
        self._render()

    # ================================================================
    # construção da UI
    # ================================================================
    def _vsep(self) -> QFrame:
        s = QFrame()
        s.setObjectName("BarSep")
        s.setFixedWidth(1)
        return s

    def _winbtn(self, name: str, slot, danger: bool = False) -> QToolButton:
        b = QToolButton()
        b.setObjectName("WinBtnClose" if danger else "WinBtn")
        b.setProperty("titlebar_button", True)
        b.setFixedSize(46, TITLEBAR_H)
        b.setIcon(icons.icon(name, "#c9ccd3", sw=1.7))
        b.setIconSize(QSize(15, 15))
        b.setFocusPolicy(Qt.NoFocus)
        b.clicked.connect(slot)
        return b

    def _build_titlebar(self) -> QWidget:
        """Linha 1: só marca (esquerda) + botões da janela (direita). É a área
        arrastável — deixada folgada de propósito."""
        bar = QFrame()
        bar.setObjectName("TitleBar")
        bar.setFixedHeight(TITLEBAR_H)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 0, 0, 0)
        lay.setSpacing(0)

        logo = QLabel()
        try:
            if config.ICON_PATH.exists():
                logo.setPixmap(QIcon(str(config.ICON_PATH)).pixmap(18, 18))
            else:
                logo.setPixmap(icons.pixmap("languages", 18, "#4f8cff"))
        except Exception:  # noqa: BLE001
            logo.setPixmap(icons.pixmap("languages", 18, "#4f8cff"))
        name = QLabel("Tradutor de Legendas")
        name.setObjectName("TitleName")
        lay.addWidget(logo)
        lay.addSpacing(8)
        lay.addWidget(name)
        lay.addStretch(1)

        self.btn_min = self._winbtn("minimize", self.showMinimized)
        self.btn_max = self._winbtn("maximize", self._toggle_max)
        self.btn_close = self._winbtn("close", self.close, danger=True)
        for b in (self.btn_min, self.btn_max, self.btn_close):
            lay.addWidget(b)

        self._titlebar = bar
        return bar

    def _build_actionbar(self) -> QWidget:
        """Linha 2: botões de ação + checkboxes (espaço à vontade)."""
        bar = QFrame()
        bar.setObjectName("ActionBar")
        bar.setFixedHeight(ACTIONBAR_H)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 0, 12, 0)
        lay.setSpacing(3)

        def act(ic, text, slot, color=None, tip=None):
            b = QToolButton()
            b.setObjectName("BarBtn")
            b.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            b.setIcon(icons.icon(ic, color) if color else icons.icon(ic))
            b.setIconSize(QSize(16, 16))
            b.setText("  " + text)
            b.setFocusPolicy(Qt.NoFocus)
            if tip:
                b.setToolTip(tip)
            b.clicked.connect(slot)
            lay.addWidget(b)

        act("region", "Capturar região", self.capture_region)
        act("monitor", "Capturar tela inteira", self.capture_fullscreen)
        act("region", "Definir região", self.pick_region, color="#9aa0a8")
        act("paste", "Colar imagem", self.paste_image)
        act("languages", "Traduzir jogo", self.open_game_translate,
            tip="Traduz os textos do jogo (mod de tradução) para PT-BR.")
        act("keyboard", "Atalhos", self.edit_hotkeys)
        if WinHotkeys is not None and not is_elevated():
            act("shield", "Reabrir como admin", self._relaunch_admin,
                tip="Se o atalho não pegar por cima de um jogo elevado.")

        lay.addSpacing(6)
        lay.addWidget(self._vsep())
        lay.addSpacing(10)

        self.chk_view = QCheckBox("Ver traduzido")
        self.chk_view.setChecked(True)
        self.chk_view.setFocusPolicy(Qt.NoFocus)
        self.chk_view.toggled.connect(self._toggle_view)
        self.chk_top = QCheckBox("Sempre no topo")
        self.chk_top.setChecked(bool(self.cfg.get("always_on_top", True)))
        self.chk_top.setFocusPolicy(Qt.NoFocus)
        self.chk_top.toggled.connect(self._on_top_toggle)
        self.chk_reverse = QCheckBox("PT → 中文")
        self.chk_reverse.setToolTip("Painel lateral: digitar em português e traduzir p/ chinês")
        self.chk_reverse.setChecked(bool(self.cfg.get("reverse_panel_visible", True)))
        self.chk_reverse.setFocusPolicy(Qt.NoFocus)
        self.chk_reverse.toggled.connect(self._toggle_reverse)
        for c in (self.chk_view, self.chk_top, self.chk_reverse):
            lay.addWidget(c)
            lay.addSpacing(10)

        lay.addStretch(1)
        return bar

    def _build_statusbar(self) -> None:
        self.hotkey_pill = QLabel("atalho: —")
        self.hotkey_pill.setObjectName("Pill")
        self.queue_pill = QLabel("fila: 0")
        self.queue_pill.setObjectName("Pill")
        self.region_lbl = QLabel("região: —")
        self.region_lbl.setObjectName("HeaderSub")
        sb = self.statusBar()
        sb.addPermanentWidget(self.region_lbl)
        sb.addPermanentWidget(self.hotkey_pill)
        sb.addPermanentWidget(self.queue_pill)

    def _build_body(self) -> QWidget:
        split = QSplitter()
        split.setHandleWidth(1)
        split.setChildrenCollapsible(False)

        # ---- filmstrip -------------------------------------------------
        self.film = QListWidget()
        self.film.setObjectName("Film")
        self.film.setFixedWidth(210)
        self.film.setIconSize(THUMB)
        self.film.setSpacing(0)
        self.film.setUniformItemSizes(True)
        self.film.currentRowChanged.connect(self._on_film_select)
        split.addWidget(self.film)

        # ---- painel principal --------------------------------------
        panel = QWidget()
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(14, 14, 14, 14)
        pl.setSpacing(12)

        self.viewer_pane = ViewerPane()
        self.viewer_pane.prev.connect(self.prev_page)
        self.viewer_pane.next.connect(self.next_page)
        pl.addWidget(self.viewer_pane, 1)

        # navegação
        self.btn_prev = QPushButton(icons.icon("chevron-left"), "  Anterior")
        self.btn_next = QPushButton("Próxima  ")
        self.btn_next.setIcon(icons.icon("chevron-right"))
        self.btn_next.setLayoutDirection(Qt.RightToLeft)
        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_next.clicked.connect(self.next_page)
        self.nav_lbl = QLabel("—")
        self.nav_lbl.setObjectName("NavLabel")
        self.nav_lbl.setAlignment(Qt.AlignCenter)

        self.btn_retry = QPushButton(icons.icon("refresh"), "  Retraduzir")
        self.btn_retry.clicked.connect(self.retranslate_current)
        self.btn_copy = QPushButton(icons.icon("copy"), "  Copiar")
        self.btn_save = QPushButton(icons.icon("save"), "  Salvar")
        self.btn_copy.clicked.connect(self.copy_text)
        self.btn_save.clicked.connect(self.save_image)

        nav = QHBoxLayout()
        nav.setSpacing(8)
        nav.addWidget(self.btn_prev)
        nav.addStretch(1)
        nav.addWidget(self.nav_lbl, 3)
        nav.addStretch(1)
        nav.addWidget(self.btn_retry)
        nav.addWidget(self.btn_copy)
        nav.addWidget(self.btn_save)
        nav.addWidget(self.btn_next)
        pl.addLayout(nav)

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setFixedHeight(140)
        self.text.setPlaceholderText("As linhas reconhecidas (CN → PT) aparecem aqui.")
        pl.addWidget(self.text)

        split.addWidget(panel)
        split.setStretchFactor(1, 1)

        # ---- painel "digitar e traduzir" (direita) -----------------
        self.reverse_panel = ReversePanel(self.cfg)
        split.addWidget(self.reverse_panel)
        split.setStretchFactor(2, 0)
        self.reverse_panel.setVisible(bool(self.cfg.get("reverse_panel_visible", True)))
        self._split = split
        QTimer.singleShot(0, lambda: split.setSizes([210, 720, 340]))
        return split

    # ================================================================
    # atalhos globais
    # ================================================================
    def _fire(self, kind: str, action) -> None:
        now = time.monotonic()
        if now - self._last_fire.get(kind, 0.0) < 0.35:   # debounce (Win32 + keyboard)
            return
        self._last_fire[kind] = now
        action()

    def _groups(self) -> dict[str, list[str]]:
        return {
            "region": list(self.cfg.get("hotkeys_region", [])),
            "full": list(self.cfg.get("hotkeys_fullscreen", [])),
            "prev": list(self.cfg.get("nav_prev_hotkeys", [])),
            "next": list(self.cfg.get("nav_next_hotkeys", [])),
        }

    def _register_hotkeys(self) -> None:
        self._unregister_hotkeys()
        groups = self._groups()
        emit = {
            "region": self._bridge_region.triggered.emit,
            "full": self._bridge_full.triggered.emit,
            "prev": self._bridge_prev.triggered.emit,
            "next": self._bridge_next.triggered.emit,
        }
        total = sum(len(v) for v in groups.values())
        if total == 0:
            self._hotkey_state = "nenhum atalho"
            return

        ok = 0
        # rastreio separado pras teclas de CAPTURA (região + tela inteira): só o
        # Win32 RegisterHotKey funciona por cima de um jogo em foco; o hook da lib
        # `keyboard` cai quando o jogo roda elevado. Se a captura só pegou no hook,
        # o usuário precisa saber.
        cap_win = 0        # combos de captura registrados no Win32
        cap_hook = 0       # combos de captura registrados no hook
        cap_total = 0
        taken: list[str] = []
        for name, combos in groups.items():
            if not combos:
                continue
            is_capture = name in ("region", "full")
            # Win32 RegisterHotKey CAPTURA a tecla (não passa pro jogo). Ótimo p/
            # F-keys, PÉSSIMO p/ setas de navegação sem modificador — o jogo perde
            # as setas. Por isso nav sem modificador só usa o hook da lib `keyboard`
            # (que não suprime a tecla).
            for hk in combos:
                bare_arrow = hk in ("left", "right", "up", "down")
                if is_capture:
                    cap_total += 1
                if self._win_hotkeys is not None and not bare_arrow:
                    if not self._win_hotkeys.bind([hk], emit[name]):
                        ok += 1
                        if is_capture:
                            cap_win += 1
                if keyboard is not None:
                    try:
                        self._hotkey_handlers.append(
                            keyboard.add_hotkey(_kbd_name(hk), emit[name]))
                        ok += 1
                        if is_capture:
                            cap_hook += 1
                    except Exception:  # noqa: BLE001
                        pass
        if self._win_hotkeys is not None:
            taken = list(self._win_hotkeys.taken)

        if taken and ok == 0:
            self._hotkey_state = f"{', '.join(taken).upper()} em uso por outro app"
            self.statusBar().showMessage(
                f"{', '.join(taken).upper()} já está em uso por outro programa "
                "(GeForce Experience, OBS, ShareX…). Escolha outra tecla em Atalhos."
            )
        elif cap_total and cap_win == 0 and cap_hook == 0:
            self._hotkey_state = "falhou"
            extra = (f"  {', '.join(taken).upper()} já está em uso." if taken else
                     "  Escolha outra tecla em Atalhos.")
            self.statusBar().showMessage(
                "Não consegui registrar a tecla de captura." + extra
            )
        elif cap_total and cap_win == 0:
            # só o hook pegou — pode não funcionar por cima do jogo
            self._hotkey_state = "só hook (pode falhar no jogo)"
            hint = (f"“{', '.join(taken).upper()}” já está em uso por outro app — "
                    "escolha outra tecla em Atalhos."
                    if taken else
                    "Se o jogo não responder à tecla, tente “Reabrir como admin” "
                    "ou escolha outra tecla em Atalhos.")
            self.statusBar().showMessage("Atalho de captura registrado só via hook. " + hint)
        elif ok:
            self._hotkey_state = "ativo" + ("" if is_elevated() else " (sem admin)")
            msg = f"{total} atalho(s) globais ativos."
            if not groups["prev"] and not groups["next"]:
                msg += "  Dica: configure atalhos de navegação em Atalhos p/ passar as traduções sem sair do jogo."
            elif not is_elevated():
                msg += "  Se o jogo ignorar, use “Reabrir como admin”."
            self.statusBar().showMessage(msg)
        else:
            self._hotkey_state = "falhou"
            self.statusBar().showMessage(
                "Não consegui registrar os atalhos globais. Use os botões / Ctrl+V, "
                "ou “Reabrir como admin”."
            )

    def _unregister_hotkeys(self) -> None:
        if self._win_hotkeys is not None:
            self._win_hotkeys.clear()
        for h in self._hotkey_handlers:
            try:
                if keyboard is not None:
                    keyboard.remove_hotkey(h)
            except Exception:  # noqa: BLE001
                pass
        self._hotkey_handlers.clear()

    def _relaunch_admin(self) -> None:
        from .win_hotkey import relaunch_as_admin

        if relaunch_as_admin():
            QApplication.quit()
        else:
            self.statusBar().showMessage("Não consegui reabrir como administrador (UAC negado?).")

    def edit_hotkeys(self) -> None:
        dlg = HotkeyDialog(self._groups(), self)
        if dlg.exec():
            g = dlg.result_groups()
            self.cfg["hotkeys_region"] = g["region"] or list(config.DEFAULTS["hotkeys_region"])
            self.cfg["hotkeys_fullscreen"] = g["full"]
            self.cfg["nav_prev_hotkeys"] = g["prev"]
            self.cfg["nav_next_hotkeys"] = g["next"]
            config.save(self.cfg)
            self._register_hotkeys()
            self._refresh_hotkey_label()

    def _refresh_hotkey_label(self) -> None:
        reg = self.cfg.get("hotkeys_region", [])
        full = self.cfg.get("hotkeys_fullscreen", [])
        txt = " / ".join(h.upper() for h in reg) if reg else "—"
        state = self._hotkey_state
        if state.startswith("ativo") and "sem admin" not in state:
            color = "#3fb950"
        elif "sem admin" in state or "só hook" in state:
            color = "#d6a13a"
        elif state.startswith("falhou") or "em uso" in state:
            color = "#e5534b"
        else:
            color = "#6a6f78"
        self.hotkey_pill.setText(
            f'<span style="color:{color};font-size:10px">●</span>&nbsp; atalho: {txt}'
        )
        prev = self.cfg.get("nav_prev_hotkeys", [])
        nxt = self.cfg.get("nav_next_hotkeys", [])
        nav = ""
        if prev or nxt:
            nav = (f"\nAnterior: {' / '.join(h.upper() for h in prev) or '—'}"
                   f"\nPróxima: {' / '.join(h.upper() for h in nxt) or '—'}")
        self.hotkey_pill.setToolTip(f"Estado: {state}\nCapturar: {txt}{nav}")

    # ================================================================
    # região
    # ================================================================
    def pick_region(self, then_capture: bool = False) -> None:
        if then_capture:
            self._pending_capture = "region"
        # esconde a própria janela ANTES do congelado da tela
        self._was_visible = self.isVisible()
        self.hide()
        QApplication.processEvents()
        time.sleep(0.12)

        self._selector = RegionSelector()
        self._selector.selected.connect(self._on_region)
        self._selector.closed.connect(self._after_region)
        self._selector.show()
        self._selector.activateWindow()
        self._selector.raise_()

    def _after_region(self) -> None:
        pending = self._pending_capture == "region"
        self._pending_capture = None
        if pending and self.cfg.get("region"):
            # acabou de definir a região por causa de um atalho — captura já.
            # a janela segue escondida, então não entra no print nem pisca;
            # só reexibe depois da captura.
            QTimer.singleShot(180, self._capture_then_show)
            return
        if getattr(self, "_was_visible", True):
            self.show()

    def _capture_then_show(self) -> None:
        try:
            self._do_capture(self.cfg.get("region"))
        finally:
            if getattr(self, "_was_visible", True):
                self.show()
                self.raise_()

    def _on_region(self, region: dict) -> None:
        self.cfg["region"] = region
        config.save(self.cfg)
        self._refresh_region_label()
        self.statusBar().showMessage(
            f"Região salva: {region['width']}×{region['height']} "
            f"@ ({region['left']},{region['top']})"
        )

    def _refresh_region_label(self) -> None:
        r = self.cfg.get("region")
        if r:
            self.region_lbl.setText(f"região: {r['width']}×{r['height']}")
        else:
            self.region_lbl.setText("região: tela inteira")

    # ================================================================
    # captura
    # ================================================================
    def capture_region(self) -> None:
        if not self.cfg.get("region"):
            self.statusBar().showMessage("Sem região definida — selecione a área primeiro.")
            self.pick_region(then_capture=True)
            return
        self._do_capture(self.cfg["region"])

    def capture_fullscreen(self) -> None:
        self._do_capture(None)

    # compat
    def capture_now(self) -> None:
        self.capture_region()

    def _do_capture(self, region: dict | None) -> None:
        hide = bool(self.cfg.get("hide_window_on_capture", True)) and self.isVisible()
        if hide:
            self.setWindowOpacity(0.0)
            QApplication.processEvents()
            time.sleep(0.12)
        try:
            img = capture.grab(region, int(self.cfg.get("monitor", 1)))
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Erro na captura", str(e))
            return
        finally:
            if hide:
                self.setWindowOpacity(1.0)
        self._enqueue(img, source="tela inteira" if region is None else "captura")

    def paste_image(self) -> None:
        """Ctrl+V — traduz uma imagem da área de transferência (print, recorte, etc.)."""
        md = QApplication.clipboard().mimeData()
        if not md.hasImage():
            self.statusBar().showMessage("Nada de imagem na área de transferência.")
            return
        qimg = QApplication.clipboard().image()
        if qimg.isNull():
            self.statusBar().showMessage("Não consegui ler a imagem colada.")
            return
        self._enqueue(qimage_to_pil(qimg), source="colada")

    def open_game_translate(self) -> None:
        from .game_translate import GameTranslateDialog

        GameTranslateDialog(self).exec()

    def _enqueue(self, img: Image.Image, source: str = "captura") -> None:
        job_id = self._next_id
        self._next_id += 1
        now = time.monotonic()
        gap = now - self._last_capture_ts if self._last_capture_ts else 1e9
        self._last_capture_ts = now

        page = {
            "id": job_id,
            "ts": datetime.now(),
            "source": source,
            "original": img,
            "translated": None,
            "lines": [],
            "done": False,
            "thumb": pil_to_qpixmap(img).scaled(
                THUMB, Qt.KeepAspectRatio, Qt.SmoothTransformation
            ),
        }
        self.pages.append(page)
        popped = False
        if len(self.pages) > self.max_pages:
            self.pages.pop(0)
            popped = True

        if len(self.pages) == 1 or gap >= self.auto_gap:
            # primeira captura, ou intervalo ≥ auto_gap → mostra a nova
            self.cur = len(self.pages) - 1
        elif popped:
            # rajada rápida: fica onde está; só corrige o índice se o buffer girou
            self.cur = max(0, self.cur - 1)

        self._sync_filmstrip()
        self._render()
        self.worker.submit(job_id, img)

    # ================================================================
    # resultados do worker
    # ================================================================
    def _on_result(self, res: dict) -> None:
        target = next((p for p in self.pages if p["id"] == res["id"]), None)
        if target is None:
            return
        target["translated"] = res.get("translated")
        target["lines"] = res.get("lines", [])
        target["translated_ok"] = res.get("translated_ok", True)
        target["done"] = True
        shown = target["translated"] or target["original"]
        target["thumb"] = pil_to_qpixmap(shown).scaled(
            THUMB, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self._sync_filmstrip()
        if self._current() is target:
            self._render()

    def _on_worker_status(self, msg: str) -> None:
        self.statusBar().showMessage(msg)

    def _on_queue(self, n: int) -> None:
        self.queue_pill.setText(f"fila: {n}")

    # ================================================================
    # filmstrip / navegação
    # ================================================================
    def _sync_filmstrip(self) -> None:
        self._film_guard = True
        self.film.clear()
        # mais novo no topo
        for idx in range(len(self.pages) - 1, -1, -1):
            p = self.pages[idx]
            mark = "" if p["done"] else "  ⏳"
            it = QListWidgetItem(f"  #{p['id']} · {p['ts'].strftime('%H:%M:%S')}{mark}")
            it.setData(Qt.UserRole, p["id"])
            if p.get("thumb"):
                it.setIcon(QIcon(p["thumb"]))
            it.setSizeHint(QSize(0, THUMB.height() + 20))
            self.film.addItem(it)
            if idx == self.cur:
                self.film.setCurrentItem(it)
        self._film_guard = False

    def _on_film_select(self, row: int) -> None:
        if self._film_guard or row < 0:
            return
        it = self.film.item(row)
        if it is None:
            return
        pid = it.data(Qt.UserRole)
        for i, p in enumerate(self.pages):
            if p["id"] == pid:
                self.cur = i
                self._render()
                return

    def prev_page(self) -> None:
        if self.cur > 0:
            self.cur -= 1
            self._sync_filmstrip()
            self._render()

    def next_page(self) -> None:
        if self.cur < len(self.pages) - 1:
            self.cur += 1
            self._sync_filmstrip()
            self._render()

    def _toggle_view(self, checked: bool) -> None:
        self._show_translated = checked
        self._render()

    def _toggle_reverse(self, checked: bool) -> None:
        self.reverse_panel.setVisible(checked)
        self.cfg["reverse_panel_visible"] = checked
        config.save(self.cfg)
        if checked:
            w = self._split.width()
            self._split.setSizes([210, max(300, w - 210 - 340), 340])
            self.reverse_panel.input.setFocus()

    def keyPressEvent(self, e) -> None:
        if e.matches(QKeySequence.Paste):
            self.paste_image()
        elif e.key() == Qt.Key_Left:
            self.prev_page()
        elif e.key() == Qt.Key_Right:
            self.next_page()
        else:
            super().keyPressEvent(e)

    # ================================================================
    # render
    # ================================================================
    def _current(self) -> dict | None:
        return self.pages[self.cur] if 0 <= self.cur < len(self.pages) else None

    def _render(self) -> None:
        total = len(self.pages)
        page = self._current()

        newer = max(0, total - 1 - self.cur)     # capturas mais novas ainda não vistas
        self.btn_prev.setEnabled(self.cur > 0)
        self.btn_next.setEnabled(self.cur < total - 1)
        self.btn_next.setText(f"Próxima ({newer})  " if newer else "Próxima  ")
        self.btn_next.setObjectName("Primary" if newer else "")
        self.btn_next.style().unpolish(self.btn_next)
        self.btn_next.style().polish(self.btn_next)
        self.viewer_pane.set_enabled(self.cur > 0, self.cur < total - 1)
        has = page is not None
        self.btn_copy.setEnabled(has and bool(page and page["lines"]))
        self.btn_save.setEnabled(has)
        failed = bool(page and page.get("done") and page["lines"]
                      and not page.get("translated_ok", True))
        self.btn_retry.setEnabled(has and bool(page and page["lines"]))
        self.btn_retry.setObjectName("Primary" if failed else "")
        self.btn_retry.style().unpolish(self.btn_retry)
        self.btn_retry.style().polish(self.btn_retry)

        if page is None:
            reg = self.cfg.get("hotkeys_region", [])
            full = self.cfg.get("hotkeys_fullscreen", [])
            hk = " / ".join(h.upper() for h in reg) or "o atalho de região"
            hkf = " / ".join(h.upper() for h in full)
            self.nav_lbl.setText("nenhuma captura ainda")
            self.viewer_pane.show_message(
                "1. clique em “Definir região” e marque a faixa da legenda\n"
                f"2. volte ao jogo e aperte {hk}"
                + (f"\n   (tela inteira: {hkf})" if hkf else "")
                + "\n\nou tecle Ctrl+V para traduzir uma imagem colada"
            )
            self.text.setPlainText("")
            return

        ts = page["ts"].strftime("%H:%M:%S")
        n = len(page["lines"])
        if not page["done"]:
            state = "processando…"
        elif n == 0:
            state = "sem texto reconhecido"
        else:
            state = f"{n} linha(s)"
        tag = "  (colada)" if page.get("source") == "colada" else ""
        newer_txt = f"    ·    {newer} nova(s)" if newer else ""
        self.nav_lbl.setText(
            f"{self.cur + 1} / {total}    ·    #{page['id']}{tag}    ·    {ts}    ·    {state}{newer_txt}"
        )

        img = page["translated"] if self._show_translated else page["original"]
        img = img or page["original"]
        self.viewer_pane.show_image(pil_to_qpixmap(img))

        if page["lines"]:
            body = "\n".join(f"{p['cn']}\n   →  {p['pt']}\n" for p in page["lines"])
            if failed:
                body = ("A TRADUÇÃO FALHOU (sem internet / limite de uso). "
                        "Clique em Retraduzir.\n\n" + body)
            self.text.setPlainText(body)
        elif page["done"]:
            self.text.setPlainText("(nenhum texto reconhecido nesta captura)")
        else:
            self.text.setPlainText("(processando…)")

    # ================================================================
    # ações
    # ================================================================
    def retranslate_current(self) -> None:
        page = self._current()
        if not page or not page["lines"]:
            return
        lines = [{"text": p["cn"], "rect": p["rect"], "score": p.get("score", 1.0)}
                 for p in page["lines"]]
        page["done"] = False
        self._render()
        self.worker.retranslate(page["id"], page["original"], lines)

    def copy_text(self) -> None:
        page = self._current()
        if not page or not page["lines"]:
            return
        payload = "\n".join(f"{p['cn']}\t{p['pt']}" for p in page["lines"])
        QApplication.clipboard().setText(payload)
        self.statusBar().showMessage("Texto copiado para a área de transferência.")

    def save_image(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        page = self._current()
        if not page:
            return
        img = (page["translated"] if self._show_translated else page["original"]) \
            or page["original"]
        config.SAVE_DIR.mkdir(parents=True, exist_ok=True)
        default = str(config.SAVE_DIR / f"legenda_{page['id']}.png")
        path, _ = QFileDialog.getSaveFileName(self, "Salvar imagem", default, "PNG (*.png)")
        if path:
            img.save(path)
            self.statusBar().showMessage(f"Salvo em {path}")

    # ================================================================
    # janela (sem moldura nativa)
    # ================================================================
    def showEvent(self, e) -> None:
        super().showEvent(e)
        if not getattr(self, "_frameless_ready", False):
            self._init_frameless()
            self._frameless_ready = True
            if self.isMinimized():          # não deixa abrir minimizado
                QTimer.singleShot(0, self.showNormal)

    def _toggle_max(self) -> None:
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def changeEvent(self, e) -> None:
        if e.type() == e.Type.WindowStateChange and hasattr(self, "btn_max"):
            self.btn_max.setIcon(icons.icon(
                "restore" if self.isMaximized() else "maximize", "#c9ccd3", sw=1.7))
        super().changeEvent(e)

    def _apply_always_on_top(self) -> None:
        self.setWindowFlag(Qt.WindowStaysOnTopHint, bool(self.cfg.get("always_on_top", True)))

    def _on_top_toggle(self, checked: bool) -> None:
        self.cfg["always_on_top"] = checked
        config.save(self.cfg)
        self._frameless_ready = False   # setWindowFlag recria a janela nativa
        was_max = self.isMaximized()
        self._apply_always_on_top()
        self.showMaximized() if was_max else self.showNormal()
        self.raise_()

    def closeEvent(self, event) -> None:
        self._unregister_hotkeys()
        if self._win_hotkeys is not None:
            self._win_hotkeys.dispose()
        try:
            if keyboard is not None:
                keyboard.unhook_all()
        except Exception:  # noqa: BLE001
            pass
        self.worker.stop()
        self.worker.wait(3000)
        super().closeEvent(event)


def _set_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    import ctypes

    for fn in (
        lambda: ctypes.windll.user32.SetProcessDpiAwarenessContext(-4),
        lambda: ctypes.windll.shcore.SetProcessDpiAwareness(2),
        lambda: ctypes.windll.user32.SetProcessDPIAware(),
    ):
        try:
            if fn():
                return
        except Exception:  # noqa: BLE001
            continue


def main() -> None:
    _set_dpi_awareness()
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Tradutor de Legendas")
    app.setStyleSheet(style.APP_QSS)
    if config.ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(config.ICON_PATH)))
    cfg = config.load()
    win = Gallery(cfg)
    win.showNormal()
    win.raise_()
    win.activateWindow()
    QTimer.singleShot(0, lambda: win.statusBar().showMessage(
        "Pronto. Defina a região da legenda e use o atalho para capturar."
    ))
    sys.exit(app.exec())
