"""
@description Traduz EN→PT o `RuntimeTextGemini.lua` do CPDD English patch de Lord of
             Mysteries (mapa 中文→English usado pelo Init.lua em `lookupGeminiText`).
             Troca os valores para português, protegendo markup (`<InvHighlight>`,
             `<Mark id>`, `%s`, quebras de linha) e fixando termos de jogo ambíguos.
             Salva o original antes e permite restaurar.
@connects overlay.translator (provedores + sessão), overlay/gamefill/game_terms.csv
          Só escreve em C7/Saved/Mods/lua/mods/cpdd_runtime_fixes/RuntimeTextGemini.lua
"""
from __future__ import annotations

import csv
import datetime as _dt
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from .. import translator
from ..config import DATA_DIR
from . import luatable

PKG_DIR = Path(__file__).resolve().parent
STATE_DIR = DATA_DIR / "gamefill"
BACKUP_DIR = STATE_DIR / "backup"
CACHE_PATH = STATE_DIR / "patch_pt_cache.json"
STATE_PATH = STATE_DIR / "patch_pt_state.json"
TERMS_CSV = PKG_DIR / "game_terms.csv"

RUNTIME_REL = "lua/mods/cpdd_runtime_fixes/RuntimeTextGemini.lua"
BACKUP_NAME = "RuntimeTextGemini.lua.orig"

_ENTRY = re.compile(r'\[("(?:\\.|[^"\\])*")\]\s*=\s*("(?:\\.|[^"\\])*")', re.S)
_HAN = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
_LATIN = re.compile(r"[A-Za-z]")

# spans de markup preservados na tradução
_TAG = re.compile(r"</?[A-Za-z][^>]*>|</>")
_FMT = re.compile(r"%[0-9.\-]*[sdfg]|\{\d+\}|\$\d+")
_WS = re.compile(r"[\n\r\t\u3000]+(?:[ \t]*[\n\r\t\u3000]+)*")
_SENT = re.compile(r"\[\[\s*(\d+)\s*\]\]")           # marcador que sobrevive ao Google

_BATCH_CHARS = 3600
_BATCH_ITEMS = 48
_SAVE_EVERY = 1500


# ---------------------------------------------------------------------------
def find_mods_dir(explicit: str | os.PathLike | None = None) -> Path | None:
    """.../C7/Saved/Mods (que tem bootstrap.lua + lua/mods/cpdd_runtime_fixes)."""
    def ok(p: Path) -> bool:
        return (p / "bootstrap.lua").exists() and (p / RUNTIME_REL).exists()

    if explicit:
        p = Path(explicit)
        for cand in (p, p / "Saved/Mods", p / "C7/Saved/Mods"):
            if ok(cand):
                return cand
        return None

    st = _read_json(STATE_PATH)
    md = st.get("mods_dir")
    if md and ok(Path(md)):
        return Path(md)

    roots = [Path(os.environ.get("SystemDrive", "C:") + "\\")]
    for extra in ("C:\\", "D:\\", "E:\\", "C:\\Jogos", "C:\\Games",
                  "C:\\Program Files", "C:\\Program Files (x86)",
                  "C:\\Program Files (x86)\\Steam\\steamapps\\common"):
        p = Path(extra)
        if p.exists():
            roots.append(p)
    for root in roots:
        try:
            for c in root.glob("**/C7/Saved/Mods"):
                if ok(c):
                    return c
        except Exception:  # noqa: BLE001
            continue
    return None


def _read_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text("utf-8"))
    except Exception:  # noqa: BLE001
        return {}


# ---------------------------------------------------------------------------
# proteção de markup + termos de jogo
# ---------------------------------------------------------------------------
def _load_terms() -> tuple[re.Pattern | None, dict[str, str]]:
    """UM regex com todos os termos (uma passada só — 50 .sub() por string
    congelavam a UI) + mapa lower->PT."""
    pairs: list[tuple[str, str]] = []
    try:
        with TERMS_CSV.open(encoding="utf-8") as f:
            for row in csv.reader(f):
                if not row or row[0].lstrip().startswith("#") or row[0] == "en":
                    continue
                en = row[0].strip()
                pt = row[1].strip() if len(row) > 1 else ""
                if en and pt:
                    pairs.append((en, pt))
    except Exception:  # noqa: BLE001
        pass
    if not pairs:
        return None, {}
    pairs.sort(key=lambda kv: len(kv[0]), reverse=True)
    rx = re.compile(r"\b(" + "|".join(re.escape(en) for en, _ in pairs) + r")\b", re.I)
    return rx, {en.lower(): pt for en, pt in pairs}


_TERM_RE, _TERM_MAP = _load_terms()


def _case_like(sample: str, pt: str) -> str:
    if sample.isupper() and len(sample) > 1:
        return pt.upper()
    if sample[:1].isupper():
        return pt[:1].upper() + pt[1:]
    return pt


def _protect(text: str) -> tuple[str, list[str]]:
    toks: list[str] = []

    def take(s: str) -> str:
        toks.append(s)
        i = len(toks) - 1
        # tokens de espaço/quebra já trazem sua folga — sem padding, senão o
        # round-trip ganha espaços fantasma no começo/fim de linha
        return f"[[{i}]]" if s.strip() == "" else f" [[{i}]] "

    text = _TAG.sub(lambda m: take(m.group(0)), text)
    text = _FMT.sub(lambda m: take(m.group(0)), text)
    text = _WS.sub(lambda m: take(m.group(0)), text)
    if _TERM_RE is not None:
        text = _TERM_RE.sub(
            lambda m: take(_case_like(m.group(0), _TERM_MAP[m.group(0).lower()])),
            text,
        )
    return text, toks


def _restore(text: str, toks: list[str]) -> str:
    used: set[int] = set()

    def put(m: re.Match) -> str:
        i = int(m.group(1))
        if 0 <= i < len(toks):
            used.add(i)
            return toks[i]           # conteúdo já traz a própria formatação
        return m.group(0)

    text = _SENT.sub(put, text)
    missing = [toks[i] for i in range(len(toks)) if i not in used]
    if missing:                      # markup que o Google engoliu volta no fim
        text = text.rstrip() + "".join(missing)
    text = re.sub(r"(?<!\n) {2,}(?!\n)", " ", text)   # espaços ASCII repetidos, poupa layout
    text = re.sub(r"<(/?[A-Za-z][^>]*)>\s+</>", r"<\1></>", text)  # <tag> </> vazio
    return text


# ---------------------------------------------------------------------------
@dataclass
class Progress:
    total: int = 0
    translated: int = 0
    pending: int = 0
    applied: bool = False
    phase: str = ""


class PatchTranslator:
    def __init__(self, mods_dir: Path) -> None:
        self.mods_dir = Path(mods_dir)
        self.path = self.mods_dir / RUNTIME_REL
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        self.backup = BACKUP_DIR / BACKUP_NAME
        self._cache: dict[str, str] = _read_json(CACHE_PATH)
        self._dirty = 0

    # ---- parsing ---------------------------------------------------
    def _source_path(self) -> Path:
        """Lê SEMPRE o original (backup se já aplicamos)."""
        return self.backup if self.backup.exists() else self.path

    def parse(self) -> list[tuple[str, str]]:
        txt = self._source_path().read_text("utf-8", errors="replace")
        out: list[tuple[str, str]] = []
        for m in _ENTRY.finditer(txt):
            key_raw = m.group(1)
            val = luatable.unescape(m.group(2)[1:-1])
            out.append((key_raw, val))
        return out

    # ---- cache ---------------------------------------------------
    def _save_cache(self, force: bool = False) -> None:
        if not force and self._dirty < _SAVE_EVERY:
            return
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = CACHE_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._cache, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, CACHE_PATH)          # troca atômica
        self._dirty = 0

    # ---- tradução em lote com backoff --------------------------
    @staticmethod
    def _providers():
        return (("clients5", translator._clients5),
                ("gtx", translator._gtx),
                ("mymemory", translator._mymemory))

    def _sleep(self, secs: float, should_stop) -> None:
        """dorme em fatias curtas pra [Parar] responder rápido."""
        end = time.monotonic() + secs
        while time.monotonic() < end:
            if should_stop and should_stop():
                return
            time.sleep(min(0.4, end - time.monotonic()))

    def _translate_batch(self, masked: list[str], should_stop=None) -> list[str] | None:
        for _name, fn in self._providers():
            delay = 3.0
            for _attempt in range(3):
                if should_stop and should_stop():
                    return None
                try:
                    res = fn(masked, "en", "pt")
                except translator._HttpError as e:
                    if "429" in str(e) or "503" in str(e):
                        self._sleep(delay, should_stop)
                        delay = min(delay * 2.5, 30)
                        continue
                    break
                except Exception:  # noqa: BLE001
                    break
                if res and len(res) == len(masked):
                    return res
                break
        return None

    @staticmethod
    def _chunks(items: list[str]):
        buf: list[str] = []
        c = 0
        for it in items:
            if buf and (c + len(it) > _BATCH_CHARS or len(buf) >= _BATCH_ITEMS):
                yield buf
                buf, c = [], 0
            buf.append(it)
            c += len(it)
        if buf:
            yield buf

    def _translatable(self, en: str) -> bool:
        # textos gigantes (livros de lore) estouram o limite de URL do provedor —
        # ficam em inglês, é uma fração ínfima e pouco visível
        return (bool(_LATIN.search(en)) and not _HAN.search(en)
                and len(en) <= 5000)

    # ---- fluxo principal --------------------------------------
    def run(self, progress_cb=None, should_stop=None) -> Progress:
        prog = Progress(phase="lendo")
        if progress_cb:
            progress_cb(prog)
        entries = self.parse()
        prog.total = len(entries)
        # dedupe preservando ordem (a 1ª ocorrência)
        seen: set[str] = set()
        uniq: list[str] = []
        for _k, en in entries:
            if en not in seen and self._translatable(en):
                seen.add(en)
                uniq.append(en)
        todo = [en for en in uniq if en not in self._cache]
        prog.translated = prog.total - len(todo)
        prog.pending = len(todo)
        prog.phase = "traduzindo"
        if progress_cb:
            progress_cb(prog)

        fails = 0
        for chunk in self._chunks(todo):
            if should_stop and should_stop():
                prog.phase = "parado"
                break
            masks = [_protect(en) for en in chunk]          # lazy: só o lote atual
            res = self._translate_batch([m for m, _ in masks], should_stop)
            if res is None:
                fails += 1
                if fails >= 6:          # provedores travados → para e retoma depois
                    prog.phase = "limite de uso — tente de novo mais tarde"
                    break
                self._sleep(3 * fails, should_stop)
                continue                                    # pendente, retoma depois
            fails = 0
            for en, (_m, toks), pt_masked in zip(chunk, masks, res):
                pt = _restore(translator._clean(pt_masked) or en, toks)
                self._cache[en] = pt or en
                self._dirty += 1
            prog.translated += len(chunk)
            prog.pending = max(0, prog.pending - len(chunk))
            self._save_cache()
            if progress_cb:
                progress_cb(prog)

        self._save_cache(force=True)
        stopped = (should_stop and should_stop()) or prog.phase.startswith("limite")
        end_phase = prog.phase if stopped and prog.phase != "traduzindo" else None
        prog.phase = "gravando"
        if progress_cb:
            progress_cb(prog)
        self.write(entries)                 # grava o que já tem (resto fica EN)
        prog.applied = True
        prog.phase = end_phase or ("parado" if stopped else "pronto")
        self._save_state(prog)
        if progress_cb:
            progress_cb(prog)
        return prog

    # ---- gravação -----------------------------------------------
    def write(self, entries: list[tuple[str, str]] | None = None) -> int:
        entries = entries or self.parse()
        if not self.backup.exists():
            self.backup.write_bytes(self.path.read_bytes())     # 1x, o original puro

        n_pt = 0
        lines = [
            "-- RuntimeTextGemini.lua traduzido EN->PT por tradutor-legendas.",
            f"-- Original intacto em: {self.backup}",
            "-- Restaurar: python -m overlay.gamefill.patch_pt --restore",
            f"-- Entradas: {len(entries)}.",
            "return {",
        ]
        for key_raw, en in entries:
            pt = self._cache.get(en, en)
            if pt != en:
                n_pt += 1
            lines.append(f'\t[{key_raw}] = "{luatable.escape(pt)}",')
        lines.append("}")
        tmp = self.path.with_suffix(".lua.tmp")
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)
        return n_pt

    def restore(self) -> bool:
        if not self.backup.exists():
            return False
        self.path.write_bytes(self.backup.read_bytes())
        st = _read_json(STATE_PATH)
        st["applied"] = False
        st["restored_at"] = _dt.datetime.now().isoformat(timespec="seconds")
        STATE_PATH.write_text(json.dumps(st, ensure_ascii=False, indent=1), "utf-8")
        return True

    # ---- estado / status -------------------------------------
    def _save_state(self, prog: Progress) -> None:
        STATE_PATH.write_text(json.dumps({
            "mods_dir": str(self.mods_dir),
            "applied": prog.applied,
            "total": prog.total,
            "translated": prog.translated,
            "pending": prog.pending,
            "updated": _dt.datetime.now().isoformat(timespec="seconds"),
        }, ensure_ascii=False, indent=1), encoding="utf-8")

    def status(self) -> Progress:
        try:
            entries = self.parse()
            total = len(entries)
            uniq = {en for _k, en in entries if self._translatable(en)}
            translated = sum(1 for en in uniq if en in self._cache)
            pending = len(uniq) - translated
        except Exception:  # noqa: BLE001
            total = translated = pending = 0
        st = _read_json(STATE_PATH)
        return Progress(total=total, translated=translated, pending=pending,
                        applied=bool(st.get("applied")), phase="")


# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        prog="python -m overlay.gamefill.patch_pt",
        description="Traduz EN->PT o RuntimeTextGemini.lua do CPDD English patch de LoM.",
    )
    ap.add_argument("--mods-dir", help=".../C7/Saved/Mods (autodetecta se omitido)")
    ap.add_argument("--restore", action="store_true", help="volta o RuntimeTextGemini original")
    ap.add_argument("--status", action="store_true", help="só mostra o progresso")
    args = ap.parse_args(argv)

    md = find_mods_dir(args.mods_dir)
    if not md:
        print("!! não achei C7/Saved/Mods/lua/mods/cpdd_runtime_fixes/RuntimeTextGemini.lua\n"
              "   passe --mods-dir <caminho>")
        return 2
    pt = PatchTranslator(md)
    print(f"mods: {md}")

    if args.restore:
        print("restaurado" if pt.restore() else "sem backup pra restaurar")
        return 0
    if args.status:
        s = pt.status()
        print(f"entradas {s.total} | traduzidas {s.translated} | faltam {s.pending} | "
              f"aplicado={s.applied}")
        return 0

    last = [0.0]

    def cb(p: Progress) -> None:
        now = time.time()
        if now - last[0] > 2 or p.phase in ("pronto", "parado", "gravando"):
            last[0] = now
            print(f"  [{p.phase}] {p.translated}/{p.total}  (faltam {p.pending})")

    p = pt.run(progress_cb=cb)
    print(f"\n{p.phase}: {p.translated}/{p.total} traduzidas.  "
          f"Restaurar: python -m overlay.gamefill.patch_pt --restore")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
