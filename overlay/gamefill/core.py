"""
@description Motor do preenchimento: localiza o mod, varre os módulos de diálogo,
             acha as strings com chinês residual, traduz (glossário + fixes + motor
             do tradutor) e grava um fragmento .lua de overlay que o mod carrega por
             cima. `state.json` torna a re-execução barata; `--restore` desfaz.
@connects overlay.translator, glossary/*.csv, overlay/gamefill/fixes.csv
"""
from __future__ import annotations

import csv
import datetime as _dt
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .. import translator
from ..config import DATA_DIR, GLOSSARY_DIR
from . import luatable

# ---------------------------------------------------------------------------
# constantes
# ---------------------------------------------------------------------------
PKG_DIR = Path(__file__).resolve().parent
STATE_DIR = DATA_DIR / "gamefill"       # dev: raiz do projeto · exe: %LOCALAPPDATA%
FIXES_CSV = PKG_DIR / "fixes.csv"

LANG_SUBPATH = Path("lua/translations/Data/Excel/LanguageData")
MODULE_PREFIX = "Data.Excel.LanguageData."
FILE_PREFIX = "StringDB_CN_Data"

# só os módulos de conversa / narrativa (escolha do usuário)
DIALOGUE_MODULES = [
    "StringDB_CN_Data_oldtalk",
    "StringDB_CN_Data_othertalk",
    "StringDB_CN_Data_talk",
    "StringDB_CN_Data_talkother",
    "StringDB_CN_Data_tingentalk",
    "StringDB_CN_Data_asidetalk",
    "StringDB_CN_Data_gossip",
    "StringDB_CN_Data_maintask",
    "StringDB_CN_Data_sidetask",
    "StringDB_CN_Data_newbietask",
    "StringDB_CN_Data_beckland",
    "StringDB_CN_Data_tingen",
    "StringDB_CN_Data_lettertext",
    "StringDB_CN_Data_newspaper",
]

_HEADER = (
    "-- gamefill (tradutor-legendas): overlay regenerável — NÃO editar à mão.\n"
    "-- Preenche linhas que o mod de localização deixou com chinês.\n"
    "-- Regenerar: python -m overlay.gamefill   |   desfazer: --restore\n"
)

_CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
_RUN = re.compile(r"[\u3400-\u9fff\uf900-\ufaff\u30fb]+")

# pontuação de largura inteira / CJK -> ASCII
_PUNCT = {
    "，": ", ", "、": ", ", "。": ". ", "：": ": ", "；": "; ",
    "！": "! ", "？": "? ", "（": " (", "）": ") ", "［": "[", "］": "]",
    "《": '"', "》": '"', "「": '"', "」": '"', "『": '"', "』": '"',
    "…": "…", "—": "—", "～": "~", "　": " ", "·": "\u00b7",
}
_PUNCT_RE = re.compile("|".join(re.escape(k) for k in _PUNCT))


def normalize_punct(s: str) -> str:
    return _PUNCT_RE.sub(lambda m: _PUNCT[m.group(0)], s)


# ajustes finais de vocabulário depois da tradução (casos que o mod deixou meio
# traduzido: "Ting根" = 廷→Ting mas 根 ficou; etc.)
_POST_FIX = [
    (re.compile(r"Ting[\s·]*(?:raiz|根)\b", re.I), "Tingen"),
    (re.compile(r"\bcidade de Ting\b"), "cidade de Tingen"),
]


_BRACE = re.compile(r"\{\{(.*?)\}\}", re.S)


def _fix_braces(s: str) -> str:
    def one(m: re.Match) -> str:
        sides = [p.strip() for p in m.group(1).split("|")]
        return "{{" + "|".join(sides) + "}}"
    return _BRACE.sub(one, s)


def tidy(s: str) -> str:
    s = s.replace("　", " ")
    s = re.sub(r"[ \t]{2,}", " ", s)
    # cola pontuação de fecho ao texto anterior (NÃO inclui aspas ASCII — ambíguas)
    s = re.sub(r"\s+([,.!?;:…»)\]}】」』’])", r"\1", s)
    s = re.sub(r"([«([{【「『‘])\s+", r"\1", s)
    # aspas ASCII: só remove espaço encostado no par "  x  " -> "x"
    s = re.sub(r'"\s+([^"\n]*?)\s+"', r'"\1"', s)
    s = re.sub(r'"\s+([^"\n]{1,40}?)"', r'"\1"', s)
    s = re.sub(r'"([^"\n]{1,40}?)\s+"', r'"\1"', s)
    s = _fix_braces(s)
    s = re.sub(r"\(\s+", "(", s).replace(" )", ")")
    for rx, rep in _POST_FIX:
        s = rx.sub(rep, s)
    return s.strip()


# ---------------------------------------------------------------------------
# localizar o mod
# ---------------------------------------------------------------------------
def _candidate_roots() -> list[Path]:
    roots: list[Path] = []
    for env in ("SystemDrive",):
        d = os.environ.get(env)
        if d:
            roots.append(Path(d + "\\"))
    for extra in ("C:\\", "D:\\", "E:\\", "C:\\Jogos", "C:\\Games",
                  "C:\\Program Files", "C:\\Program Files (x86)",
                  "C:\\Program Files (x86)\\Steam\\steamapps\\common"):
        p = Path(extra)
        if p.exists():
            roots.append(p)
    return roots


def find_mod_dir(explicit: str | os.PathLike | None = None) -> Path | None:
    """Devolve .../C7/Saved/Mods/localization (ou None)."""
    if explicit:
        p = Path(explicit)
        if (p / "bootstrap.lua").exists():
            return p
        if (p / "Saved/Mods/localization/bootstrap.lua").exists():
            return p / "Saved/Mods/localization"
        return None

    saved = STATE_DIR / "state.json"
    if saved.exists():
        try:
            md = json.loads(saved.read_text("utf-8")).get("mod_dir")
            if md and (Path(md) / "bootstrap.lua").exists():
                return Path(md)
        except Exception:  # noqa: BLE001
            pass

    hint = LANG_SUBPATH / f"{FILE_PREFIX}.lua"
    for root in _candidate_roots():
        try:
            for c7 in root.glob("**/C7/Saved/Mods/localization"):
                if (c7 / "bootstrap.lua").exists():
                    return c7
        except Exception:  # noqa: BLE001
            continue
    return None


# ---------------------------------------------------------------------------
# glossário + fixes
# ---------------------------------------------------------------------------
def _load_pairs() -> tuple[list[tuple[str, str]], dict[str, str]]:
    """Devolve (prepass, overrides).
    prepass  = substituições str.replace ANTES de traduzir (nomes multi-caractere).
    overrides = trechos cujo run inteiro é exatamente a chave — resolvidos sem API
                (inclui caracteres únicos ambíguos como 他/她/根 que não podem
                 entrar no prepass, senão bagunçam palavras maiores)."""
    raw: dict[str, str] = {}
    for path in sorted(GLOSSARY_DIR.glob("*.csv")):
        try:
            with path.open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    cn = (row.get("cn") or "").strip()
                    pt = (row.get("pt_br") or "").strip()
                    if cn and pt and _CJK.search(cn):
                        raw.setdefault(cn, pt)
        except Exception:  # noqa: BLE001
            pass
    try:
        with FIXES_CSV.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cn = (row.get("cn") or "").strip()
                pt = (row.get("pt_br") or "").strip()
                if cn and pt:
                    raw[cn] = pt          # fixes têm prioridade
    except Exception:  # noqa: BLE001
        pass

    prepass = {c: p for c, p in raw.items() if len(c) >= 2}
    overrides = dict(raw)                 # todos servem como override de run exato
    return (sorted(prepass.items(), key=lambda kv: len(kv[0]), reverse=True),
            overrides)


def _splice(s: str, start: int, end: int, rep: str) -> str:
    """Troca s[start:end] por rep, pondo espaço só se o vizinho for alfanumérico
    (evita 'Melissahá pouco' e 'do"aspas')."""
    left = s[start - 1] if start > 0 else ""
    right = s[end] if end < len(s) else ""
    pre = " " if left.isalnum() else ""
    post = " " if right.isalnum() else ""
    return s[:start] + pre + rep + post + s[end:]


def _apply_pairs(s: str, pairs: list[tuple[str, str]]) -> str:
    for cn, pt in pairs:
        idx = s.find(cn)
        while idx != -1:
            s = _splice(s, idx, idx + len(cn), pt)
            idx = s.find(cn, idx + len(pt))
    return s


# ---------------------------------------------------------------------------
# resultado
# ---------------------------------------------------------------------------
@dataclass
class ModuleResult:
    module: str
    base_parts: int
    total_cjk: int = 0
    filled: int = 0
    residual: int = 0
    reused: int = 0
    entries: dict[int, dict] = field(default_factory=dict)  # key -> {cn, pt, residual}


@dataclass
class RunReport:
    modules: list[ModuleResult] = field(default_factory=list)
    translated_runs: int = 0
    provider_ok: bool = True

    @property
    def total_cjk(self) -> int:
        return sum(m.total_cjk for m in self.modules)

    @property
    def total_filled(self) -> int:
        return sum(m.filled for m in self.modules)

    @property
    def total_residual(self) -> int:
        return sum(m.residual for m in self.modules)


# ---------------------------------------------------------------------------
# motor
# ---------------------------------------------------------------------------
class GameFill:
    def __init__(self, mod_dir: Path, mark: str = "» ") -> None:
        self.mod_dir = Path(mod_dir)
        self.ld_dir = self.mod_dir / LANG_SUBPATH
        self.mark = mark
        self.mark_residual = (mark.rstrip() + "? ") if mark.strip() else ""
        self.pairs, self.run_overrides = _load_pairs()
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.state_path = STATE_DIR / "state.json"
        self.state = self._load_state()

    # ---- estado -------------------------------------------------------
    def _load_state(self) -> dict:
        try:
            return json.loads(self.state_path.read_text("utf-8"))
        except Exception:  # noqa: BLE001
            return {"mod_dir": str(self.mod_dir), "modules": {}}

    def _save_state(self) -> None:
        self.state["mod_dir"] = str(self.mod_dir)
        self.state["generated"] = _dt.datetime.now().isoformat(timespec="seconds")
        self.state_path.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    # ---- leitura dos módulos ----------------------------------------
    def _index_path(self, module: str) -> Path:
        return self.ld_dir / f"{module}.lua"

    def _part_path(self, module: str, n: int) -> Path:
        return self.ld_dir / f"{module}.parts/{n:04d}.lua"

    def _read_index_count(self, module: str) -> int | None:
        p = self._index_path(module)
        if not p.exists():
            return None
        return luatable.parse_parts_count(p.read_text("utf-8", errors="replace"))

    def _base_parts(self, module: str, cur_count: int) -> int:
        """Nº de fragmentos do MOD (sem contar nosso overlay)."""
        st = self.state["modules"].get(module)
        if st and st.get("applied_index") == cur_count \
                and self._part_path(module, cur_count).exists() \
                and _is_ours(self._part_path(module, cur_count)):
            return int(st["base_parts"])
        return cur_count

    def _merged_module(self, module: str, base_parts: int) -> dict[int, str]:
        merged: dict[int, str] = {}
        for i in range(1, base_parts + 1):
            p = self._part_path(module, i)
            if p.exists():
                merged.update(
                    luatable.parse_entries(p.read_text("utf-8", errors="replace"))
                )
        return merged

    # ---- varredura -------------------------------------------------
    def scan(self, modules: list[str]) -> list[tuple[ModuleResult, dict[int, str]]]:
        found = []
        for module in modules:
            cur = self._read_index_count(module)
            if cur is None:
                continue
            base = self._base_parts(module, cur)
            merged = self._merged_module(module, base)
            cjk = {
                k: normalize_punct(v)
                for k, v in merged.items()
                if _CJK.search(v)
            }
            res = ModuleResult(module=module, base_parts=base, total_cjk=len(cjk))
            found.append((res, cjk))
        return found

    # ---- tradução dos trechos -------------------------------------
    def _translate_runs(self, runs: set[str]) -> tuple[dict[str, str], bool]:
        runmap = {r: self.run_overrides[r] for r in runs if r in self.run_overrides}
        todo = sorted(r for r in runs if _CJK.search(r) and r not in runmap)
        if not todo:
            return runmap, True
        out, ok = translator.translate_lines(
            todo, source="zh-CN", target="pt", force=False
        )
        runmap.update({r: tidy(t) for r, t in zip(todo, out)})
        return runmap, ok

    def _fill_value(self, norm_value: str, runmap: dict[str, str]) -> tuple[str, bool]:
        s = _apply_pairs(norm_value, self.pairs)
        # substitui cada trecho CJK restante, da direita p/ a esquerda (índices estáveis)
        spans = [m.span() for m in _RUN.finditer(s) if _CJK.search(m.group(0))]
        for start, end in reversed(spans):
            run = s[start:end]
            s = _splice(s, start, end, runmap.get(run, run))
        s = tidy(s)
        residual = bool(_CJK.search(s))
        return s, residual

    # ---- aplicar --------------------------------------------------
    def run(self, modules: list[str] | None = None, write: bool = True) -> RunReport:
        modules = modules or DIALOGUE_MODULES
        scanned = self.scan(modules)

        # junta todos os trechos CJK de todos os módulos numa tradução só
        all_runs: set[str] = set()
        for res, cjk in scanned:
            for v in cjk.values():
                s = _apply_pairs(v, self.pairs)
                all_runs.update(r for r in _RUN.findall(s) if _CJK.search(r))
        runmap, prov_ok = self._translate_runs(all_runs)

        report = RunReport(provider_ok=prov_ok, translated_runs=len(runmap))

        for res, cjk in scanned:
            st = self.state["modules"].get(res.module, {})
            prev_entries = st.get("entries", {}) if st.get("base_parts") == res.base_parts else {}
            overlay: dict[int, str] = {}
            for key, norm_value in cjk.items():
                prev = prev_entries.get(str(key))
                if prev and prev.get("src") == norm_value and not prev.get("residual"):
                    pt = prev["pt"]
                    residual = False
                    res.reused += 1
                else:
                    pt, residual = self._fill_value(norm_value, runmap)
                mark = self.mark_residual if residual else self.mark
                overlay[key] = (mark + pt) if mark else pt
                res.filled += 1
                if residual:
                    res.residual += 1
                res.entries[key] = {"src": norm_value, "pt": pt, "residual": residual}

            if write and overlay:
                self._write_overlay(res, overlay)
                self.state["modules"][res.module] = {
                    "base_parts": res.base_parts,
                    "applied_index": res.base_parts + 1,
                    "entries": {str(k): v for k, v in res.entries.items()},
                }
            report.modules.append(res)

        self._write_report(report)          # relatório sempre (mesmo em dry-run)
        if write:
            self._save_state()
        return report

    def _write_overlay(self, res: ModuleResult, overlay: dict[int, str]) -> None:
        part = self._part_path(res.module, res.base_parts + 1)
        part.parent.mkdir(parents=True, exist_ok=True)
        part.write_text(luatable.dump_part(overlay, _HEADER), encoding="utf-8")
        idx = self._index_path(res.module)
        self._backup_index(res.module, idx)
        idx.write_text(f"return {{ __parts = {res.base_parts + 1} }}\n", encoding="utf-8")

    # ---- backup / restore ---------------------------------------
    def _backup_index(self, module: str, idx: Path) -> None:
        bdir = STATE_DIR / "backup"
        bdir.mkdir(parents=True, exist_ok=True)
        b = bdir / f"{module}.lua"
        if not b.exists():
            b.write_text(idx.read_text("utf-8", errors="replace"), encoding="utf-8")

    def restore(self) -> list[str]:
        undone: list[str] = []
        for module, st in list(self.state.get("modules", {}).items()):
            base = int(st["base_parts"])
            applied = int(st.get("applied_index", base + 1))
            part = self._part_path(module, applied)
            if part.exists() and _is_ours(part):
                part.unlink()
            b = STATE_DIR / "backup" / f"{module}.lua"
            idx = self._index_path(module)
            if b.exists():
                idx.write_text(b.read_text("utf-8"), encoding="utf-8")
            elif idx.exists():
                idx.write_text(f"return {{ __parts = {base} }}\n", encoding="utf-8")
            undone.append(module)
        self.state["modules"] = {}
        self._save_state()
        return undone

    # ---- relatório -------------------------------------------------
    def _write_report(self, report: RunReport) -> None:
        path = STATE_DIR / "report.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["module", "key", "origem_cn", "traducao_pt", "residual_cjk"])
            for res in report.modules:
                for key, e in sorted(res.entries.items()):
                    w.writerow([res.module, key, e["src"], e["pt"],
                                "SIM" if e["residual"] else ""])


def _is_ours(path: Path) -> bool:
    try:
        return "gamefill (tradutor-legendas)" in path.read_text("utf-8", errors="replace")[:200]
    except Exception:  # noqa: BLE001
        return False
