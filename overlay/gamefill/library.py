"""
@description Biblioteca de traduções de jogos. Lê um índice (GitHub, com fallback
             embutido), resolve a dependência da tradução (ex.: o CPDD English patch,
             baixado do repositório OFICIAL dele — nunca redistribuído aqui), baixa os
             arquivos da tradução PT pra pasta do tradutor, verifica a pasta do jogo e
             instala/restaura com backup do original.
@connects overlay.game_translate (diálogo) · overlay.translator (sessão HTTP)
          Escreve só em <dados>/traducoes/ e nos arquivos que o manifesto indicar
          (backup em <dados>/gamefill/backup/).
"""
from __future__ import annotations

import datetime as _dt
import fnmatch
import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from ..config import DATA_DIR
from ..translator import _SESSION

PKG_DIR = Path(__file__).resolve().parent
BUNDLED_INDEX = PKG_DIR / "translations_index.json"
TRANSLATIONS_DIR = DATA_DIR / "traducoes"
DEPS_DIR = TRANSLATIONS_DIR / "_deps"
BACKUP_DIR = DATA_DIR / "gamefill" / "backup"

INDEX_URL = ("https://raw.githubusercontent.com/alehandromendes/"
             "tradutor-legendas-traducoes/main/index.json")
RAW_BASE = ("https://raw.githubusercontent.com/alehandromendes/"
            "tradutor-legendas-traducoes/main/")


@dataclass
class TFile:
    src: str                       # caminho no repo da biblioteca
    dest: str                      # caminho relativo à RAIZ do jogo

    @property
    def name(self) -> str:
        return Path(self.src).name


@dataclass
class Dependency:
    id: str
    name: str
    detect: list[str]              # arquivos (rel. à raiz do jogo) que provam que está instalada
    page_url: str = ""             # página pública do instalador oficial
    api_url: str = ""              # GitHub API da última release
    asset_glob: str = "*.exe"      # padrão do asset do instalador
    direct_url: str = ""           # link fixo do instalador (release oficial da autora)
    note: str = ""


_LANG_LABEL = {"zh": "中文", "zh-cn": "中文", "zh-hans": "中文",
               "en": "EN", "pt-br": "PT-BR", "pt": "PT"}


def _lbl(code: str) -> str:
    return _LANG_LABEL.get((code or "").lower(), (code or "").upper())


@dataclass
class Game:
    id: str
    name: str
    source_lang: str = "zh-CN"
    via_lang: str = ""
    target_lang: str = "pt-BR"
    based_on: str = ""
    note: str = ""
    default_dirs: list[str] = field(default_factory=list)     # candidatos à RAIZ do jogo
    game_markers: list[str] = field(default_factory=list)     # confirmam a raiz certa
    dependency: Dependency | None = None
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
        dep = None
        d = g.get("dependency")
        if d:
            dep = Dependency(
                id=d["id"], name=d["name"], detect=list(d.get("detect", [])),
                page_url=d.get("page_url", ""), api_url=d.get("api_url", ""),
                asset_glob=d.get("asset_glob", "*.exe"),
                direct_url=d.get("direct_url", ""), note=d.get("note", ""),
            )
        games.append(Game(
            id=g["id"], name=g["name"],
            source_lang=g.get("source_lang", "zh-CN"),
            via_lang=g.get("via_lang", g.get("via", "")),
            target_lang=g.get("target_lang", "pt-BR"),
            based_on=g.get("based_on", ""), note=g.get("note", ""),
            default_dirs=list(g.get("default_dirs", [])),
            game_markers=list(g.get("game_markers", [])),
            dependency=dep,
            files=[TFile(f["src"], f["dest"]) for f in g.get("files", [])],
        ))
    return games


def load_index() -> tuple[list[Game], str]:
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

    # ---- pasta local da tradução -----------------------------------
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
            r = _SESSION.get(RAW_BASE + f.src, timeout=(6, 120))
            r.raise_for_status()
            (d / f.name).write_bytes(r.content)
        (d / ".manifest.json").write_text(json.dumps({
            "id": g.id, "name": g.name,
            "downloaded": _dt.datetime.now().isoformat(timespec="seconds"),
            "files": [f.name for f in g.files],
        }, ensure_ascii=False, indent=1), "utf-8")
        if progress_cb:
            progress_cb("baixado", len(g.files), len(g.files))

    # ---- raiz do jogo --------------------------------------------
    def find_game_root(self, g: Game) -> Path | None:
        for cand in g.default_dirs:
            p = Path(cand)
            if p.exists() and all((p / m).exists() for m in g.game_markers):
                return p
        if not g.game_markers:
            for cand in g.default_dirs:
                if Path(cand).exists():
                    return Path(cand)
        return None

    def is_game_root(self, g: Game, root: Path) -> bool:
        root = Path(root)
        return root.exists() and all((root / m).exists() for m in g.game_markers) \
            if g.game_markers else root.exists()

    # ---- dependência (ex.: CPDD) --------------------------------
    def dependency_ok(self, g: Game, root: Path | None) -> bool:
        if not g.dependency:
            return True
        if not root:
            return False
        return all((Path(root) / d).exists() for d in g.dependency.detect)

    def fetch_dependency_installer(self, g: Game, progress_cb=None) -> Path:
        """Baixa o instalador OFICIAL da dependência (fonte dela, não daqui)."""
        dep = g.dependency
        if not dep or not dep.api_url:
            raise RuntimeError("sem API da dependência no índice")
        r = _SESSION.get(dep.api_url, timeout=15)
        r.raise_for_status()
        rel = r.json()
        assets = rel.get("assets", [])
        match = next((a for a in assets
                      if fnmatch.fnmatch(a["name"].lower(), dep.asset_glob.lower())), None)
        if not match:
            match = next((a for a in assets if a["name"].lower().endswith(".exe")), None)
        if not match:
            raise RuntimeError("não achei o instalador na última release da dependência")
        DEPS_DIR.mkdir(parents=True, exist_ok=True)
        dest = DEPS_DIR / match["name"]
        if dest.exists() and dest.stat().st_size == match.get("size", -1):
            if progress_cb:
                progress_cb("já baixado", 1, 1)
            return dest
        total = int(match.get("size") or 0)
        got = 0
        with _SESSION.get(match["browser_download_url"], stream=True,
                          timeout=(15, 300)) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length") or total or 0)
            tmp = dest.with_suffix(".part")
            with open(tmp, "wb") as fh:
                for chunk in resp.iter_content(65536):
                    fh.write(chunk)
                    got += len(chunk)
                    if progress_cb and total:
                        progress_cb(f"baixando {match['name']}", got, total)
            os.replace(tmp, dest)
        if progress_cb:
            progress_cb("baixado", 1, 1)
        return dest

    def fetch_dependency_direct(self, g: Game, progress_cb=None) -> Path:
        """Baixa o instalador da dependência por link FIXO (release oficial da
        autora). Mesmo arquivo que o botão da página do GitHub — não hospedamos
        nada, só automatizamos o download."""
        dep = g.dependency
        if not dep or not dep.direct_url:
            raise RuntimeError("sem direct_url da dependência no índice")
        DEPS_DIR.mkdir(parents=True, exist_ok=True)
        name = dep.direct_url.rsplit("/", 1)[-1] or "cpdd-english-patch.exe"
        dest = DEPS_DIR / name
        with _SESSION.get(dep.direct_url, stream=True, timeout=(15, 300)) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length") or 0)
            if dest.exists() and total and dest.stat().st_size == total:
                if progress_cb:
                    progress_cb("já baixado", 1, 1)
                return dest
            got = 0
            tmp = dest.with_suffix(".part")
            with open(tmp, "wb") as fh:
                for chunk in resp.iter_content(65536):
                    fh.write(chunk)
                    got += len(chunk)
                    if progress_cb and total:
                        progress_cb(f"baixando {name}", got, total)
            os.replace(tmp, dest)
        if progress_cb:
            progress_cb("baixado", 1, 1)
        return dest

    @staticmethod
    def run_installer(path: Path) -> None:
        os.startfile(str(path))                       # abre o wizard oficial

    # ---- instalar / restaurar ----------------------------------
    def _backup_path(self, g: Game, dest_rel: str) -> Path:
        return BACKUP_DIR / g.id / dest_rel

    def installed(self, g: Game) -> bool:
        return (BACKUP_DIR / g.id / ".installed.json").exists()

    def _mark_installed(self, g: Game, root: Path) -> None:
        (BACKUP_DIR / g.id).mkdir(parents=True, exist_ok=True)
        (BACKUP_DIR / g.id / ".installed.json").write_text(json.dumps({
            "id": g.id, "root": str(root),
            "at": _dt.datetime.now().isoformat(timespec="seconds"),
            "files": [f.dest for f in g.files],
            "via": "gamepatch",
        }, ensure_ascii=False, indent=1), "utf-8")

    def install(self, g: Game, root: Path, progress_cb=None, should_stop=None) -> None:
        root = Path(root)
        src_dir = self.game_dir(g)
        for i, f in enumerate(g.files):
            if progress_cb:
                progress_cb(f"instalando {f.name}", i, len(g.files))
            dst = root / f.dest
            dst.parent.mkdir(parents=True, exist_ok=True)
            bkp = self._backup_path(g, f.dest)
            if dst.exists() and not bkp.exists():
                bkp.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, bkp)
            shutil.copy2(src_dir / f.name, dst)
        (BACKUP_DIR / g.id / ".installed.json").write_text(json.dumps({
            "id": g.id, "root": str(root),
            "at": _dt.datetime.now().isoformat(timespec="seconds"),
            "files": [f.dest for f in g.files],
        }, ensure_ascii=False, indent=1), "utf-8")
        if progress_cb:
            progress_cb("instalado", len(g.files), len(g.files))

    def restore(self, g: Game, root: Path | None = None) -> int:
        marker = BACKUP_DIR / g.id / ".installed.json"
        info = {}
        try:
            info = json.loads(marker.read_text("utf-8"))
        except Exception:  # noqa: BLE001
            pass
        r = Path(root or info.get("root", ""))
        n = 0
        for f in g.files:
            bkp = self._backup_path(g, f.dest)
            dst = r / f.dest
            if bkp.exists() and dst.parent.exists():
                shutil.copy2(bkp, dst)
                n += 1
        marker.unlink(missing_ok=True)
        return n

    # ---- estado combinado (pra UI) ---------------------------
    def state(self, g: Game, root: Path | None = None) -> dict:
        r = Path(root) if root else self.find_game_root(g)
        dep_ok = self.dependency_ok(g, r)
        return {
            "root": str(r) if r else "",
            "root_ok": r is not None,
            "dep": g.dependency.name if g.dependency else "",
            "dep_ok": dep_ok,
            "downloaded": self.downloaded(g),
            "installed": self.installed(g),
            "can_install": bool(r and dep_ok and self.downloaded(g)),
        }
