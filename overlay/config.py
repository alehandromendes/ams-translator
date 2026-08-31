"""
@description Configuração e persistência das settings do AMS Translator (tradução ao vivo).
@connects lido por overlay.gallery, overlay.compositor, overlay.worker
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Console do Windows (cp1252) não imprime CJK — força UTF-8.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

FROZEN = getattr(sys, "frozen", False)

if FROZEN:
    # .exe do PyInstaller: recursos empacotados em sys._MEIPASS; dados graváveis
    # em %LOCALAPPDATA%\AMS Translator (NÃO ao lado do exe — senão o app
    # trava a pasta e impede recompilar/atualizar).
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    _base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    DATA_DIR = Path(_base) / "AMS Translator"
    _legacy = Path(_base) / "TradutorDeLegendas"
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        # migração do nome antigo (Tradutor de Legendas) — copia 1x o que existir
        if _legacy.is_dir() and not (DATA_DIR / ".migrated").exists():
            import shutil
            for item in _legacy.iterdir():
                dst = DATA_DIR / item.name
                if dst.exists():
                    continue
                try:
                    if item.is_dir():
                        shutil.copytree(item, dst)
                    else:
                        shutil.copy2(item, dst)
                except Exception:  # noqa: BLE001
                    pass
            (DATA_DIR / ".migrated").write_text("from TradutorDeLegendas\n", "utf-8")
    except Exception:  # noqa: BLE001
        DATA_DIR = Path(sys.executable).resolve().parent
else:
    DATA_DIR = Path(__file__).resolve().parent.parent
    BUNDLE_DIR = DATA_DIR

ROOT = DATA_DIR  # compat

CONFIG_PATH = DATA_DIR / "overlay_config.json"
CACHE_PATH = DATA_DIR / "data" / "cache" / "overlay_tm.json"
SAVE_DIR = DATA_DIR / "data" / "overlay_shots"

# glossário editável ao lado do exe tem prioridade; senão usa o empacotado
_editable_glossary = DATA_DIR / "glossary"
GLOSSARY_DIR = _editable_glossary if (_editable_glossary / "names.csv").exists() \
    else BUNDLE_DIR / "glossary"

ICON_PATH = BUNDLE_DIR / "assets" / "icon.ico"

DEFAULTS: dict = {
    "_v": 3,                         # versão do schema (migrações em load())
    "hotkeys_region": ["pgup"],      # atalho: captura a região pré-configurada
    "hotkeys_fullscreen": ["pgdown"],  # atalho: captura a tela inteira
    "nav_prev_hotkeys": ["left"],    # atalhos globais: página anterior da galeria
    "nav_next_hotkeys": ["right"],   # atalhos globais: próxima página da galeria
    "region": None,          # {"left", "top", "width", "height"} em coords absolutas
    "monitor": 1,            # índice mss (1 = monitor primário) — usado se region for None
    "source_lang": "zh-CN",
    "target_lang": "pt",
    "always_on_top": True,
    "min_ocr_score": 0.5,
    "font_path": "C:/Windows/Fonts/seguisb.ttf",  # Segoe UI Semibold
    "hide_window_on_capture": True,
    "max_pages": 10,         # quantas capturas a galeria mantém (buffer circular)
    # se o intervalo desde a captura anterior for MENOR que isto, a galeria NÃO
    # pula pra nova (você navega com as setas); se for maior/igual, pula.
    "auto_advance_gap_seconds": 60,
    # painel "digitar e traduzir" (lado direito) — direção inversa
    "reverse_panel_visible": True,
    "reverse_source": "pt",
    "reverse_target": "zh-CN",
}


def load() -> dict:
    cfg = dict(DEFAULTS)
    raw: dict = {}
    if CONFIG_PATH.exists():
        try:
            raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            cfg.update(raw)
        except Exception:  # noqa: BLE001
            pass

    def _norm(v) -> list[str]:
        return [str(h).strip().lower() for h in v if str(h).strip()] \
            if isinstance(v, list) else []

    # migração: formato antigo (hotkey / hotkeys[]) → hotkeys_region, só se o
    # arquivo ainda não tiver a chave nova
    if "hotkeys_region" not in raw:
        old = _norm(raw.get("hotkeys")) or ([raw["hotkey"]] if raw.get("hotkey") else [])
        if old:
            cfg["hotkeys_region"] = old
    cfg.pop("hotkey", None)
    cfg.pop("hotkeys", None)

    for key in ("hotkeys_region", "hotkeys_fullscreen",
                "nav_prev_hotkeys", "nav_next_hotkeys"):
        cfg[key] = _norm(cfg.get(key))

    if not cfg["hotkeys_region"]:
        cfg["hotkeys_region"] = list(DEFAULTS["hotkeys_region"])

    # v2: nav com as setas por padrão (arquivos v1 tinham [] gravado pelo save)
    if int(raw.get("_v", 1)) < 2:
        for key in ("nav_prev_hotkeys", "nav_next_hotkeys"):
            if not cfg[key]:
                cfg[key] = list(DEFAULTS[key])

    # v3: captura passa a ser PgUp (região) / PgDn (tela inteira). Migra só quem
    # ainda está nos padrões antigos (F9/F8) — teclas personalizadas ficam.
    if int(raw.get("_v", 1)) < 3:
        if cfg["hotkeys_region"] in ([], ["f9"]):
            cfg["hotkeys_region"] = list(DEFAULTS["hotkeys_region"])
        if cfg["hotkeys_fullscreen"] in ([], ["f8"]):
            cfg["hotkeys_fullscreen"] = list(DEFAULTS["hotkeys_fullscreen"])

    cfg["_v"] = 3
    return cfg


def save(cfg: dict) -> None:
    keep = {k: cfg.get(k, v) for k, v in DEFAULTS.items()}
    CONFIG_PATH.write_text(
        json.dumps(keep, ensure_ascii=False, indent=2), encoding="utf-8"
    )
