"""
@description Ciclo completo da tradução do jogo (Lord of Mysteries + CPDD English patch):
             instala o dumper -> (rodar o jogo) -> lê o dump dos 45 módulos -> traduz
             EN->PT (cache do patch_pt) -> grava a camada PT em lua/mods/tl_translate/pt/
             -> troca pro modo aplicar. Só mexe em pastas do usuário (nada do CPDD).
@connects overlay.gamefill.patch_pt (motor + cache), overlay/gamefill/luamod/*
          CLI:  python -m overlay.gamefill.gamepatch  <prepare|build|restore|status>
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

from . import luatable, patch_pt

PKG_DIR = Path(__file__).resolve().parent
# quando congelado (PyInstaller), os datas ficam em sys._MEIPASS
_MEI = Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "frozen", False) else None
_BASE = (_MEI / "overlay/gamefill") if _MEI else PKG_DIR
LUAMOD = _BASE / "luamod"
PREBUILT = _BASE / "prebuilt"

REL_USER_SETTINGS = "Saved/Mods/lua/cpdd_user_settings.lua"
REL_MOD_INIT = "Saved/Mods/lua/mods/tl_translate/Init.lua"
REL_PT_DIR = "Saved/Mods/lua/mods/tl_translate/pt"
REL_HOTPATCH = "Saved/Mods/lua/mods/tl_translate/pt/hotpatch.lua"
REL_DUMP_DIR = "Saved/Mods/lua/_tl_dump"


def _deploy_mod(root: Path) -> None:
    """Copia Init.lua + cpdd_user_settings.lua + hotpatch.lua pro jogo."""
    (root / REL_MOD_INIT).parent.mkdir(parents=True, exist_ok=True)
    (root / REL_PT_DIR).mkdir(parents=True, exist_ok=True)
    (root / REL_USER_SETTINGS).write_bytes((LUAMOD / "cpdd_user_settings.lua").read_bytes())
    (root / REL_MOD_INIT).write_bytes((LUAMOD / "Init.lua").read_bytes())
    hp = LUAMOD / "hotpatch.lua"
    if hp.exists():
        (root / REL_HOTPATCH).write_bytes(hp.read_bytes())

_ENTRY = re.compile(r'\[("(?:\\.|[^"\\])*"|\d+)\]\s*=\s*("(?:\\.|[^"\\])*")', re.S)


# ---------------------------------------------------------------------------
def find_game_root(explicit: str | None = None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if (p / "Binaries/Win64/C7-Win64-Shipping.exe").exists() else None
    for base in ("C:/Jogos/Game/C7",
                 "C:/Program Files (x86)/Steam/steamapps/common/Lord of Mysteries/C7",
                 "D:/Steam/steamapps/common/Lord of Mysteries/C7"):
        p = Path(base)
        if (p / "Binaries/Win64/C7-Win64-Shipping.exe").exists():
            return p
    return None


def _cpdd_ok(root: Path) -> bool:
    return (root / "Saved/Mods/bootstrap.lua").exists()


# ---------------------------------------------------------------------------
def prepare(root: Path) -> None:
    """Instala o dumper e liga o modo dump."""
    (root / REL_USER_SETTINGS).parent.mkdir(parents=True, exist_ok=True)
    (root / REL_MOD_INIT).parent.mkdir(parents=True, exist_ok=True)
    (root / REL_PT_DIR).mkdir(parents=True, exist_ok=True)
    (root / REL_DUMP_DIR).mkdir(parents=True, exist_ok=True)
    _deploy_mod(root)
    (root / REL_DUMP_DIR / "run").write_text("dump", encoding="utf-8")
    for f in (root / REL_DUMP_DIR).glob("*.lua"):
        f.unlink()
    (root / REL_DUMP_DIR / "status").unlink(missing_ok=True)


def install(root: Path, progress_cb=None, pt_src=None) -> dict:
    """Instalação direta: mod tl_translate + traduções PT.
    NÃO modifica nenhum arquivo do CPDD — restaura qualquer modificação prévia
    (RuntimeTextGemini.lua / Init.lua) e só cria pastas seguras do usuário.

    pt_src: pasta com os .lua PT já baixados (library.game_dir). Se None, cai no
    PREBUILT embutido — que só existe em build de dev; no instalador a tradução
    é baixada."""
    import shutil
    # 1) devolve os arquivos do CPDD ao original (se tiverem sido modificados antes)
    try:
        patch_pt.PatchTranslator(root / "Saved/Mods").restore()
    except Exception:  # noqa: BLE001
        pass
    # 2) mod em pasta segura do usuário
    _deploy_mod(root)
    ptdir = root / REL_PT_DIR
    ptdir.mkdir(parents=True, exist_ok=True)
    src = Path(pt_src) if pt_src else PREBUILT
    n = 0
    if src.is_dir():
        for f in src.iterdir():
            if (f.is_file() and f.suffix == ".lua"
                    and f.name not in ("hotpatch.lua", "apply_status.txt")):
                shutil.copy2(f, ptdir / f.name)
                n += 1
    if n == 0:
        raise RuntimeError(
            "nenhum arquivo de tradução encontrado — clique em Baixar primeiro "
            f"({src})")
    # modo aplicar: NUNCA deixa _tl_dump/ no jogo do usuário (é ferramenta de
    # dev; a presença de _tl_dump/run ligaria o dump e daria hitch no jogo).
    shutil.rmtree(root / REL_DUMP_DIR, ignore_errors=True)
    if progress_cb:
        progress_cb({"phase": "pronto", "files": n})
    return {"files": n}


def dump_status(root: Path) -> str:
    p = root / REL_DUMP_DIR / "status"
    return p.read_text("utf-8").strip() if p.exists() else ""


def _read_text(f: Path) -> str:
    """o File.SaveStringContentToFile do jogo grava UTF-16 LE (com BOM)."""
    raw = f.read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-16", errors="replace")


# nomes reais conhecidos (quando não há _modules.lua do dump antigo)
_KNOWN_NAMES = {
    "Data_Excel_LanguageData_StringDB_CN_Data": "Data.Excel.LanguageData.StringDB_CN_Data",
    "Data_Config_StringConst_Language_zhs": "Data.Config.StringConst.Language_zhs",
    "Shared_language_zhs": "Shared.language_zhs",
    "Launch_I18n_zh": "Launch.I18n.zh",
    "Data_Excel_RoleCreateQandAData": "Data.Excel.RoleCreateQandAData",
    "Gameplay_Debug_DebugConst": "Gameplay.Debug.DebugConst",
    "Gameplay_LogicSystem_CreateRole_CreateRoleAnswer_Panel":
        "Gameplay.LogicSystem.CreateRole.CreateRoleAnswer_Panel",
}


def _real_name(stem: str, modmap: dict[str, str]) -> str:
    return modmap.get(stem) or _KNOWN_NAMES.get(stem) or stem.replace("_", ".")


def _read_modmap(root: Path) -> dict[str, str]:
    """_tl_dump/_modules.lua  ->  { sanitizado : nome.real.pontilhado }"""
    f = root / REL_DUMP_DIR / "_modules.lua"
    if not f.exists():
        return {}
    txt = _read_text(f)
    out: dict[str, str] = {}
    for m in re.finditer(r'\["([^"]+)"\]\s*=\s*"((?:\\.|[^"\\])*)"', txt):
        out[m.group(1)] = luatable.unescape(m.group(2))
    return out


def _read_dumps(root: Path) -> dict[str, dict]:
    """{ nome_arquivo_do_módulo : {key: en} }  a partir de _tl_dump/*.lua"""
    out: dict[str, dict] = {}
    for f in sorted((root / REL_DUMP_DIR).glob("*.lua")):
        if f.name.startswith("_"):          # _modules.lua, _index.lua
            continue
        txt = _read_text(f)
        rows: dict = {}
        for m in _ENTRY.finditer(txt):
            k = m.group(1)
            key = int(k) if k.isdigit() else k          # numérico ou "string"
            rows[key] = luatable.unescape(m.group(2)[1:-1])
        if rows:
            out[f.stem] = rows
    return out


# overrides exatos EN->PT (nomes de skill encurtados, tags de UI, etc.)
_OVR_PATH = PKG_DIR / "skill_overrides.csv"


def _load_overrides() -> dict[str, str]:
    if not _OVR_PATH.exists():
        return {}
    out: dict[str, str] = {}
    for ln in _OVR_PATH.read_text("utf-8").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "\t" not in ln:
            continue
        en, pt = ln.split("\t", 1)
        if en:
            out[en] = pt
    return out


_LATIN = re.compile(r"[A-Za-z]")
_HAN = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")


def build(root: Path, progress_cb=None, should_stop=None) -> dict:
    dumps = _read_dumps(root)
    if not dumps:
        raise RuntimeError("nenhum dump em _tl_dump/*.lua — rode o jogo uma vez "
                           "depois de 'prepare'")

    pt = patch_pt.PatchTranslator(root / "Saved/Mods")          # reusa cache/engine/backoff
    modmap = _read_modmap(root)
    overrides = _load_overrides()

    # junta todos os valores EN únicos que faltam no cache
    uniq: list[str] = []
    seen: set[str] = set()
    for rows in dumps.values():
        for v in rows.values():
            if (v and v not in seen and _LATIN.search(v) and not _HAN.search(v)
                    and len(v) <= 5000):
                seen.add(v)
                uniq.append(v)
    todo = [v for v in uniq if v not in pt._cache and v not in overrides]

    prog = patch_pt.Progress(total=len(uniq), translated=len(uniq) - len(todo),
                             pending=len(todo), phase="traduzindo")
    if progress_cb:
        progress_cb(prog)
    pt._fill_cache(todo, prog, progress_cb, should_stop)
    pt._save_cache(force=True)

    # grava a camada PT: lua/mods/tl_translate/pt/<modulo>.lua
    #
    # o jogo carrega UM único "Data.Excel.LanguageData.StringDB_CN_Data" (não os
    # sufixados _maintask/_skill1/...). Então todo o PT dos módulos StringDB* é
    # fundido num só arquivo com esse nome.
    AGG_STEM = "Data_Excel_LanguageData_StringDB_CN_Data"
    AGG_NAME = "Data.Excel.LanguageData.StringDB_CN_Data"
    ptdir = root / REL_PT_DIR
    ptdir.mkdir(parents=True, exist_ok=True)
    for old in ptdir.glob("*.lua"):
        old.unlink()

    def _rows_to_pt(rows: dict) -> dict:
        out = {}
        for key, en in rows.items():
            tl = overrides.get(en) or pt._cache.get(en)
            if tl and tl != en:
                out[key] = tl
        return out

    def _write(stem: str, mapping: dict) -> int:
        lines = ["return {"]
        for key, tl in mapping.items():
            kk = str(key) if isinstance(key, int) else '"' + luatable.escape(str(key)) + '"'
            lines.append(f'  [{kk}] = "{luatable.escape(tl)}",')
        lines.append("}")
        (ptdir / f"{stem}.lua").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return len(mapping)

    written, entries = 0, 0
    real_names: list[str] = []
    # NÃO fundir: o jogo carrega CADA StringDB_CN_Data_<tag> como módulo separado
    # em package.loaded (confirmado pelo _catalog.txt). Um arquivo pt/ por módulo,
    # e TODOS entram no _index.lua -> Loader.AfterLoad hooka cada um.
    for old in ptdir.glob("cpdd_*.lua"):
        old.unlink()
    cpdd_tags: list[str] = []
    for mod, rows in dumps.items():
        ptmap = _rows_to_pt(rows)
        if not ptmap:
            continue
        n = _write(mod, ptmap)
        written += 1
        entries += n
        real_names.append(_real_name(mod, modmap))
        # também exporta como tabela por tag p/ injetar em cpdd_translation.*
        if mod == AGG_STEM:
            tag = ""
        elif mod.startswith(AGG_STEM):
            tag = mod[len(AGG_STEM):].lstrip("_")
        else:
            tag = None
        if tag is not None:
            _write("cpdd_" + (tag or "AGG"), ptmap)
            cpdd_tags.append(tag)
    (ptdir / "cpdd_tags.lua").write_text(
        "return {\n" + "\n".join(f'  "{t}",' for t in cpdd_tags) + "\n}\n",
        encoding="utf-8")
    # índice com os nomes reais dos módulos (o Init.lua em modo aplicar lê isto)
    idx = ["return {"]
    idx += [f'  "{luatable.escape(nm)}",' for nm in sorted(real_names)]
    idx.append("}")
    (ptdir / "_index.lua").write_text("\n".join(idx) + "\n", encoding="utf-8")

    # mapa EN->PT keyed pelo INGLÊS que o CPDD produz. O Init.lua funde isto no
    # geminiTextOverrides -> translateVisibleText passa a re-traduzir EN->PT tudo
    # que o CPDD já resolveu pra inglês (diálogo, item, interação, quest...).
    # Fatiado em partes de <=15000 entradas: um `return {...}` gigante estoura
    # o limite de constantes por função do LuaJIT.
    for old in ptdir.glob("_en2pt*.lua"):
        old.unlink()
    en2pt: list[tuple[str, str]] = []
    seen_en: set[str] = set()
    for en, tl in list(pt._cache.items()) + list(overrides.items()):
        if not en or not tl or tl == en or en in seen_en:
            continue
        if len(en) > 2000 or ("\n" in en and len(en) > 600):
            continue
        if not _LATIN.search(en) or _HAN.search(en):
            continue
        seen_en.add(en)
        en2pt.append((en, tl))
    CHUNK = 15000
    parts = 0
    for i in range(0, len(en2pt), CHUNK):
        parts += 1
        lines = ["return {"]
        for en, tl in en2pt[i:i + CHUNK]:
            lines.append(f'  ["{luatable.escape(en)}"] = "{luatable.escape(tl)}",')
        lines.append("}")
        (ptdir / f"_en2pt_{parts}.lua").write_text("\n".join(lines) + "\n",
                                                   encoding="utf-8")
    (ptdir / "_en2pt_count.lua").write_text(f"return {parts}\n", encoding="utf-8")
    entries += len(en2pt)
    # garante Init.lua + hotpatch.lua atualizados, troca pro modo aplicar
    _deploy_mod(root)
    (root / REL_DUMP_DIR / "run").unlink(missing_ok=True)
    prog.phase = "pronto"
    if progress_cb:
        progress_cb(prog)
    return {"modules": written, "entries": entries, "cache": len(pt._cache)}


def restore(root: Path) -> list[str]:
    done = []
    for rel in (REL_USER_SETTINGS, REL_MOD_INIT):
        p = root / rel
        if p.exists():
            p.unlink()
            done.append(rel)
    import shutil
    for d in ("Saved/Mods/lua/mods/tl_translate", "Saved/Mods/lua/_tl_dump"):
        p = root / d
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
            done.append(d)
    # RuntimeTextGemini / Init do CPDD ficam com patch_pt --restore
    try:
        patch_pt.PatchTranslator(root / "Saved/Mods").restore()
        done.append("RuntimeTextGemini.lua + Init.lua (originais do CPDD)")
    except Exception:  # noqa: BLE001
        pass
    return done


# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    cmd = argv[0] if argv else "status"
    root = find_game_root(argv[1] if len(argv) > 1 else None)
    if not root:
        print("!! não achei a pasta do jogo (…/Game/C7). passe o caminho como 2º arg.")
        return 2
    print(f"jogo: {root}")
    if not _cpdd_ok(root):
        print("!! o CPDD English patch não está instalado (falta Saved/Mods/bootstrap.lua)")
        return 2

    if cmd == "install":
        r = install(root)
        print(f"instalado: mod + {r['files']} arquivos PT. Reinicie o jogo.")
    elif cmd == "prepare":
        prepare(root)
        print("dumper instalado (modo DUMP). Abra o jogo até o menu e feche.")
    elif cmd == "status":
        st = dump_status(root)
        n = len(list((root / REL_DUMP_DIR).glob("*.lua")))
        print(f"dump: {st or '(ainda não rodou)'}  | arquivos: {n}")
        ptn = len(list((root / REL_PT_DIR).glob("*.lua")))
        mode = "APLICAR" if not (root / REL_DUMP_DIR / "run").exists() else "DUMP"
        print(f"modo: {mode}  | camada PT: {ptn} módulos")
    elif cmd == "build":
        t0 = time.time()
        def cb(p):
            if time.time() - t0 > 2 or p.phase == "pronto":
                print(f"  [{p.phase}] {p.translated}/{p.total}")
        r = build(root, cb)
        print(f"\npronto: {r['modules']} módulos PT, {r['entries']} entradas. "
              f"Reinicie o jogo.")
    elif cmd == "restore":
        for d in restore(root):
            print("  removido/restaurado:", d)
        print("jogo de volta ao CPDD puro.")
    else:
        print("uso: install | prepare | build | restore | status  [pasta_do_jogo]")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
