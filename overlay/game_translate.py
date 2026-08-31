"""
@description Diálogo "Tradução de jogos" — lista as traduções da biblioteca (GitHub,
             com fallback embutido), baixa os arquivos pra pasta do tradutor
             (`traducoes/<jogo>/`), confere a pasta do jogo e instala com backup do
             original / restaura.
@connects overlay.gamefill.library · aberto por overlay.gallery.open_game_translate
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import icons
from .gamefill import library


class _Job(QThread):
    tick = Signal(str, int, int)     # texto, i, total
    done = Signal(str)               # "" = ok, senão erro
    kind = ""

    def __init__(self, fn) -> None:
        super().__init__()
        self._fn = fn
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        try:
            self._fn(progress_cb=lambda t, i, n: self.tick.emit(t, i, n),
                     should_stop=lambda: self._stop)
            self.done.emit("")
        except TypeError:
            try:
                self._fn(progress_cb=lambda t, i, n: self.tick.emit(t, i, n))
                self.done.emit("")
            except Exception as e:  # noqa: BLE001
                self.done.emit(f"{type(e).__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            self.done.emit(f"{type(e).__name__}: {e}")


class _GameCard(QFrame):
    """Um jogo da biblioteca: info + botão de ação à direita.
    Fluxo: (achar pasta) → Instalar base (dependência) → Baixar → Instalar."""

    def __init__(self, dlg: "GameTranslateDialog", game: library.Game) -> None:
        super().__init__()
        self.setObjectName("GameCard")
        self.dlg = dlg
        self.game = game
        self.root: Path | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(8)

        top = QHBoxLayout()
        left = QVBoxLayout()
        left.setSpacing(2)
        title = QLabel(f"{game.name}")
        title.setObjectName("RowTitle")
        sub = QLabel(game.lang_path
                     + (f"  ·  {game.based_on}" if game.based_on else ""))
        sub.setObjectName("RowSub")
        left.addWidget(title)
        left.addWidget(sub)
        top.addLayout(left, 1)

        self.btn = QPushButton()
        self.btn.setObjectName("Primary")
        self.btn.setMinimumWidth(120)
        self.btn.clicked.connect(self._action)
        top.addWidget(self.btn, 0, Qt.AlignTop)
        outer.addLayout(top)

        if game.note:
            note = QLabel(game.note)
            note.setObjectName("RowSub")
            note.setWordWrap(True)
            outer.addWidget(note)

        # pasta do jogo (raiz — termina em C7)
        row = QHBoxLayout()
        row.setSpacing(6)
        self.path = QLineEdit()
        self.path.setPlaceholderText("pasta do jogo (…\\Game\\C7)")
        self.path.setReadOnly(True)
        b_browse = QPushButton("Procurar")
        b_browse.clicked.connect(self._browse)
        b_default = QPushButton("Padrão")
        b_default.clicked.connect(self._use_default)
        row.addWidget(self.path, 1)
        row.addWidget(b_browse)
        row.addWidget(b_default)
        outer.addLayout(row)

        self.check = QLabel()
        self.check.setObjectName("RowSub")
        self.check.setWordWrap(True)
        outer.addWidget(self.check)

        self._use_default(initial=True)

    # ------------------------------------------------------------------
    def _use_default(self, initial: bool = False) -> None:
        r = self.dlg.lib.find_game_root(self.game)
        if r:
            self.root = r
            self.path.setText(str(r))
        elif not initial:
            QMessageBox.information(
                self, "Pasta padrão",
                "Não achei a pasta do jogo. Use 'Procurar' e aponte a pasta que "
                "termina em \\Game\\C7.")
        self.refresh()

    def _browse(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, "Pasta do jogo — a que termina em \\Game\\C7",
            self.path.text() or "C:/")
        if not d:
            return
        p = Path(d)
        if not self.dlg.lib.is_game_root(self.game, p):
            QMessageBox.warning(self, "Pasta do jogo",
                                "Essa pasta não parece a raiz do jogo (falta o "
                                "executável em Binaries/Win64).")
            return
        self.root = p
        self.path.setText(d)
        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        st = self.dlg.lib.state(self.game, self.root)
        self.root = Path(st["root"]) if st["root"] else self.root
        dep = self.game.dependency

        if not st["root_ok"]:
            self.check.setText("escolha a pasta do jogo (…\\Game\\C7)")
        elif dep and not st["dep_ok"]:
            self.check.setText(f"✗ falta a base: {dep.name} não está instalado")
        elif st["installed"]:
            self.check.setText("✓ tradução PT instalada")
        else:
            self.check.setText("✓ pronto pra instalar")

        icon, text, enabled = "languages", "  Instalar", False
        if not st["root_ok"]:
            text, enabled = "  Instalar", False
        elif dep and not st["dep_ok"]:
            icon, text, enabled = "shield", f"  Instalar base ({dep.name})", True
        elif not st["downloaded"]:
            icon, text, enabled = "save", "  Baixar", True
        elif st["installed"]:
            icon, text, enabled = "refresh", "  Reinstalar", True
        else:
            icon, text, enabled = "languages", "  Instalar", True
        self.btn.setText(text)
        self.btn.setIcon(icons.icon(icon))
        self.btn.setEnabled(enabled and not self.dlg.busy)
        self.btn.setToolTip("" if enabled else "Aponte a pasta do jogo primeiro.")
        self.dlg.btn_restore.setEnabled(st["installed"])
        self.dlg._card_state = st

    # ------------------------------------------------------------------
    def _action(self) -> None:
        if self.dlg.busy:
            return
        lib = self.dlg.lib
        st = lib.state(self.game, self.root)
        dep = self.game.dependency

        if dep and not st["dep_ok"]:
            self._install_dependency(dep)
        elif not st["downloaded"]:
            self.dlg._run_job(
                "Baixando tradução…",
                lambda **kw: lib.download(self.game, **kw),
                self.refresh,
                done_msg="Tradução baixada. Clique em Instalar pra aplicar no jogo.")
        else:
            # instalação 100% via gamepatch: mod tl_translate + PT pré-construído.
            # NÃO modifica arquivos do CPDD (o lib.install fazia isso e saiu).
            def _do_install(**kw):
                from .gamefill import gamepatch
                gamepatch.install(self.root)
                lib._mark_installed(self.game, self.root)
            self.dlg._run_job(
                "Instalando…", _do_install, self.refresh,
                done_msg="Tradução instalada. Reinicie o jogo pra ver.")

    def _install_dependency(self, dep: "library.Dependency") -> None:
        m = QMessageBox(self.dlg)
        m.setWindowTitle(f"Pré-requisito: {dep.name}")
        m.setIcon(QMessageBox.Icon.Warning)
        m.setText(
            f"A tradução PT precisa do <b>{dep.name}</b> instalado no jogo primeiro.\n\n"
            f"{dep.note}\n\n"
            f"Posso baixar o instalador OFICIAL agora (do GitHub da autora, "
            f"{dep.page_url}) e abrir o wizard dele pra você?")
        m.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if m.exec() != QMessageBox.StandardButton.Yes:
            return

        def after(err_ignored=None) -> None:
            path = getattr(self.dlg, "_dep_path", None)
            if path and Path(path).exists():
                library.Library.run_installer(Path(path))
                QMessageBox.information(
                    self.dlg, dep.name,
                    "O instalador do CPDD abriu. No wizard dele:\n"
                    "1. aponte a pasta do jogo (ou Auto-detect)\n"
                    "2. espere o pré-check\n"
                    "3. Install English\n\n"
                    "Quando terminar, volte aqui — o botão vira \"Baixar\".")
            self.refresh()

        def grab(progress_cb=None, **_) -> None:
            self.dlg._dep_path = str(
                self.dlg.lib.fetch_dependency_installer(self.game, progress_cb))

        self.dlg._run_job(f"Baixando o instalador do {dep.name}…", grab, after,
                          done_msg="")


class GameTranslateDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Tradução de jogos")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.lib = library.Library()
        self.busy = False
        self._job: _Job | None = None
        self._card_state: dict = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)

        head = QHBoxLayout()
        self.src_lbl = QLabel("carregando biblioteca…")
        self.src_lbl.setObjectName("RowSub")
        b_reload = QPushButton("↻")
        b_reload.setFixedWidth(34)
        b_reload.clicked.connect(self._load)
        head.addWidget(self.src_lbl, 1)
        head.addWidget(b_reload)
        root.addLayout(head)

        self.cards = QVBoxLayout()
        self.cards.setSpacing(10)
        holder = QWidget()
        holder.setLayout(self.cards)
        root.addWidget(holder, 1)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.bar = QProgressBar()
        self.bar.hide()
        root.addWidget(self.bar)

        foot = QHBoxLayout()
        self.btn_restore = QPushButton(icons.icon("refresh"), "  Restaurar original")
        self.btn_restore.clicked.connect(self._restore)
        self.btn_restore.setEnabled(False)
        foot.addWidget(self.btn_restore)
        foot.addStretch(1)
        close = QPushButton("Fechar")
        close.clicked.connect(self.close)
        foot.addWidget(close)
        root.addLayout(foot)

        self._load()

    # ------------------------------------------------------------------
    def _load(self) -> None:
        while self.cards.count():
            w = self.cards.takeAt(0).widget()
            if w:
                w.deleteLater()
        games, origin = library.load_index()
        self.src_lbl.setText({
            "github": "Fonte: GitHub · alehandromendes/tradutor-legendas-traducoes",
            "local": "Fonte: índice embutido (offline) — GitHub indisponível",
            "vazio": "Nenhuma tradução encontrada",
        }.get(origin, origin))
        self._game_cards = []
        for g in games:
            c = _GameCard(self, g)
            self._game_cards.append(c)
            self.cards.addWidget(c)
        self.cards.addStretch(1)

    # ------------------------------------------------------------------
    def _run_job(self, label: str, fn, on_done, done_msg: str = "Pronto.") -> None:
        self.busy = True
        self.status.setText(label)
        self.bar.show()
        self.bar.setRange(0, 0)
        for c in self._game_cards:
            c.btn.setEnabled(False)
        self._job = _Job(fn)
        self._job.tick.connect(self._on_tick)

        def finish(err: str) -> None:
            self.busy = False
            self._job = None
            self.bar.hide()
            if err:
                self.status.setText("")
                QMessageBox.warning(self, "Erro", err)
            else:
                self.status.setText(done_msg)
            on_done()

        self._job.done.connect(finish)
        self._job.start()

    def _on_tick(self, text: str, i: int, n: int) -> None:
        if n:
            self.bar.setRange(0, n)
            self.bar.setValue(i)
        self.status.setText(text)

    # ------------------------------------------------------------------
    def _restore(self) -> None:
        if self.busy or not self._game_cards:
            return
        card = self._game_cards[0]
        if QMessageBox.question(
            self, "Restaurar original",
            "Devolver o arquivo original (inglês) do jogo?"
        ) != QMessageBox.StandardButton.Yes:
            return
        n = self.lib.restore(card.game, card.root)
        try:
            from .gamefill import gamepatch
            gamepatch.restore(card.root)
        except Exception as e:  # noqa: BLE001
            print("gamepatch.restore:", e)
        QMessageBox.information(self, "Restaurar",
                                f"{n} arquivo(s) restaurado(s). Reinicie o jogo."
                                if n else "Não havia backup pra restaurar.")
        card.refresh()

    def closeEvent(self, e) -> None:
        if self._job:
            self._job.stop()
            self._job.wait(6000)
        super().closeEvent(e)
