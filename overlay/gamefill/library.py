"""
@description Biblioteca de traduções de jogos: lê um índice (GitHub, com fallback
             embutido), baixa os arquivos de tradução pra pasta do tradutor
             (`traducoes/<Nome do jogo>/`), verifica a pasta do jogo e instala
             (com backup do original) / restaura.
@connects overlay.game_translate (diálogo) · overlay.translator (sessão HTTP)
          Escreve só em: <dados do tradutor>/traducoes/  e nos arquivos que o
          manifesto do jogo indicar (com backup em <dados>/gamefill/backup/).
"""
from __future__ import annotations

import datetime as _dt
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from ..config import DATA_DIR
from ..translator import _SESSION

PKG_DIR = Path(__file__).resolve().parent
BUNDLED_INDEX = PKG_DIR / "translations_index.json"
TRANSLATIONS_DIR = DATA_DIR / "traducoes"
BACKUP_DIR = DATA_DIR / "gamefill" / "backup"

INDEX_URL = ("https://raw.githubusercontent.com/alehandromendes/"
             "tradutor-legendas-traducoes/main/index.json")
RAW_BASE = ("https://raw.githubusercontent.com/alehandromendes/"
            "tradutor-legendas-traducoes/main/")


@dataclass
class TFile:
    src: str                       # caminho no repo da biblioteca
    dest: str                      # caminho relativo dentro da pasta do jogo

    @property
    def name(self) -> str:
        return Path(self.src).name


_LANG_LABEL = {"zh": "中文", "zh-cn": "中文", "zh-hans": "中文",
               "en": "EN", "pt-br": "PT-BR", "pt": "PT"}


def _lbl(code: str) -> str:
    return _LANG_LABEL.get((code or "").lower(), (code or "").upper())


@dataclass
class Game:
    id: str
    name: str
    source_lang: str = "zh-CN"     # idioma original do jogo
    via_lang: str = ""             # idioma-ponte (ex.: EN, do patch em inglês)
    target_lang: str = "pt-BR"
    based_on: str = ""
    note: str = ""
    default_dirs: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    files: list[TFile] = field(default_factory=list)

    @property
    def lang_path(self) -> str:
        parts = [_lbl(self.source_lang)]
        if self.via_lang:
            parts.append(_lbl(self.via_lang))
        parts.append(_lbl(self.target_lang))
        return " → ".join(parts)


def _parse(data: dict) -> list[Game]:
    games: list[Game] = []
    for g in data.get("games", []):
        games.append(Game(
            id=g["id"], name=g["name"],
            source_lang=g.get("source_lang", "zh-CN"),
            via_lang=g.get("via_lang", g.get("via", "")),
            target_lang=g.get("target_lang", "pt-BR"),
            based_on=g.get("based_on", ""), note=g.get("note", ""),
            default_dirs=list(g.get("default_dirs", [])),
            requires=list(g.get("requires", [])),
            files=[TFile(f["src"], f["dest"]) for f in g.get("files", [])],
        ))
    return games


def load_index() -> tuple[list[Game], str]:
    """(jogos, origem) — tenta o GitHub, cai pro índice embutido."""
    try:
        r = _SESSION.get(INDEX_URL, timeout=6)
        if r.ok and r.text.strip().startswith("{"):
            return _parse(r.json()), "github"
    except Exception:  # noqa: BLE001
        pass
    try:
        return _parse(json.loads(BUNDLED_INDEX.read_text("utf-8"))), "local"
    except Exception:  # noqa: BLE001
        return [], "vazio"


# ---------------------------------------------------------------------------
class Library:
    def __init__(self) -> None:
        TRANSLATIONS_DIR.mkdir(parents=True, exist_ok=True)

    # ---- pasta local da tradução -------------------------------------
    def game_dir(self, g: Game) -> Path:
        return TRANSLATIONS_DIR / g.name

    def downloaded(self, g: Game) -> bool:
        d = self.game_dir(g)
        return bool(g.files) and all((d / f.name).exists() for f in g.files)

    def download(self, g: Game, progress_cb=None, should_stop=None) -> None:
        d = self.game_dir(g)
        d.mkdir(parents=True, exist_ok=True)
        for i, f in enumerate(g.files):
            if should_stop and should_stop():
                return
            if progress_cb:
                progress_cb(f"baixando {f.name} ({i + 1}/{len(g.files)})", i, len(g.files))
            r = _SESSION.get(RAW_BASE + f.src, timeout=(6, 60))
            r.raise_for_status()
            (d / f.name).write_bytes(r.content)
        (d / ".manifest.json").write_text(json.dumps({
            "id": g.id, "name": g.name, "downloaded": _dt.datetime.now().isoformat(timespec="seconds"),
            "files": [f.name for f in g.files],
        }, ensure_ascii=False, indent=1), "utf-8")
        if progress_cb:
            progress_cb("baixado", len(g.files), len(g.files))

    # ---- pasta do jogo ---------------------------------------------
    def detect_game_dir(self, g: Game) -> Path | None:
        for cand in g.default_dirs:
            p = Path(cand)
            if p.exists() and not self.verify(g, p):
                return p
        return None

    def verify(self, g: Game, target: Path) -> list[str]:
        """devolve a lista de itens de `requires` que faltam (vazio = ok)."""
        target = Path(target)
        return [r for r in g.requires if not (target / r).exists()]

    # ---- instalar / restaurar ------------------------------------
    def _backup_path(self, g: Game, dest_rel: str) -> Path:
        return BACKUP_DIR / g.id / dest_rel

    def installed(self, g: Game, target: Path) -> bool:
        marker = BACKUP_DIR / g.id / ".installed.json"
        return marker.exists()

    def install(self, g: Game, target: Path, progress_cb=None,
                should_stop=None) -> None:
        target = Path(target)
        src_dir = self.game_dir(g)
        for i, f in enumerate(g.files):
            if progress_cb:
                progress_cb(f"instalando {f.name}", i, len(g.files))
            dst = target / f.dest
            dst.parent.mkdir(parents=True, exist_ok=True)
            bkp = self._backup_path(g, f.dest)
            if dst.exists() and not bkp.exists():
                bkp.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, bkp)               # 1ª vez: guarda o original
            shutil.copy2(src_dir / f.name, dst)
        marker = BACKUP_DIR / g.id / ".installed.json"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({
            "id": g.id, "target": str(target),
            "at": _dt.datetime.now().isoformat(timespec="seconds"),
            "files": [f.dest for f in g.files],
        }, ensure_ascii=False, indent=1), "utf-8")
        if progress_cb:
            progress_cb("instalado", len(g.files), len(g.files))

    def restore(self, g: Game, target: Path | None = None) -> int:
        marker = BACKUP_DIR / g.id / ".installed.json"
        info = {}
        try:
            info = json.loads(marker.read_text("utf-8"))
        except Exception:  # noqa: BLE001
            pass
        tgt = Path(target or info.get("target", ""))
        n = 0
        for f in g.files:
            bkp = self._backup_path(g, f.dest)
            dst = tgt / f.dest
            if bkp.exists() and dst.parent.exists():
                shutil.copy2(bkp, dst)
                n += 1
        marker.unlink(missing_ok=True)
        return n

    # ---- estado combinado (pra UI) ------------------------------
    def state(self, g: Game, target: Path | None = None) -> dict:
        tgt = Path(target) if target else self.detect_game_dir(g)
        missing = self.verify(g, tgt) if tgt else g.requires
        return {
            "downloaded": self.downloaded(g),
            "installed": self.installed(g, tgt) if tgt else False,
            "target": str(tgt) if tgt else "",
            "missing": missing,
            "dir_ok": tgt is not None and not missing,
        }
