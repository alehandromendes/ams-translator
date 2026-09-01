"""
@description Overrides pontuais no RuntimeTextGemini.lua (pós-patch_pt): encurta o
             aviso de "jogo saudável" que cobre a tela de login e ajusta textos
             que a MT deixou esquisitos. Aplica no arquivo do jogo, na fonte
             traducoes/ e no cache (pra não perder no próximo build).
@connects overlay.gamefill.patch_pt (CACHE_PATH), RuntimeTextGemini.lua
          uso:  python -m overlay.gamefill.gemini_overrides
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import patch_pt as P

# chave-chinesa (prefixo)  ->  valor PT curto forçado
KEY_PREFIX_OVERRIDES: dict[str, str] = {
    "健康游戏忠告": (
        "Jogo saudável: recuse pirataria, cuidado com golpes, jogue com "
        "moderação e organize seu tempo. Indicado para maiores de 16 anos "
        "(menores acompanhados dos pais). A empresa cumpre as regras "
        "antivício e de cadastro por nome real. Direitos: Hangzhou Danzhi "
        "Universe. Aprovação: Guo Xin Chu Shen [2024] No. 2024115807."
    ),
}

# valor-EN exato  ->  valor PT forçado
EN_VALUE_OVERRIDES: dict[str, str] = {
    "Connect to Server": "Conectando ao servidor",
    "Enter the Extraordinary World": "Entrar no mundo dos Beyounders",
    "Enter Extraordinary World": "Entrar no mundo dos Beyounders",
    "Enter World": "Entrar no mundo dos Beyounders",
}

# chave-chinesa exata  ->  valor PT forçado
CN_KEY_OVERRIDES: dict[str, str] = {
    "进入非凡世界": "Entrar no mundo dos Beyounders",
}

_PAIR = re.compile(r'(\["(?:\\.|[^"\\])*"\]\s*=\s*)"((?:\\.|[^"\\])*)"')


def _apply_to_file(path: Path) -> int:
    txt = path.read_text(encoding="utf-8")
    n = 0

    def repl(m: re.Match) -> str:
        nonlocal n
        head, val = m.group(1), m.group(2)
        for pref, pt in KEY_PREFIX_OVERRIDES.items():
            if head.startswith('["' + pref) or pref in head[:48]:
                n += 1
                return head + '"' + pt + '"'
        for en, pt in EN_VALUE_OVERRIDES.items():
            if val == en:
                n += 1
                return head + '"' + pt + '"'
        for cn, pt in CN_KEY_OVERRIDES.items():
            if head.startswith('["' + cn + '"]'):
                n += 1
                return head + '"' + pt + '"'
        return m.group(0)

    new = _PAIR.sub(repl, txt)
    if n:
        path.write_text(new, encoding="utf-8")
    return n


def _patch_cache() -> int:
    if not P.CACHE_PATH.exists():
        return 0
    cache: dict[str, str] = json.loads(P.CACHE_PATH.read_text("utf-8"))
    n = 0
    # health: a chave do cache é o VALOR EN longo; acha por prefixo
    for en_src in list(cache):
        if en_src.startswith("Healthy Gaming Advice"):
            cache[en_src] = KEY_PREFIX_OVERRIDES["健康游戏忠告"]
            n += 1
    for en, pt in EN_VALUE_OVERRIDES.items():
        if en in cache:
            cache[en] = pt
            n += 1
    if n:
        P.CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), "utf-8")
    return n


def main() -> int:
    md = P.find_mods_dir(None)
    if not md:
        print("!! nao achei o CPDD")
        return 2
    game = md / P.RUNTIME_REL
    src = Path.home() / "AppData/Local/AMS Translator/traducoes/Lord of Mysteries/RuntimeTextGemini.lua"
    total = 0
    for f in (game, src):
        if f.exists():
            k = _apply_to_file(f)
            total += k
            print(f"{k:3}  {f}")
    print(f"cache: {_patch_cache()} entradas ajustadas")
    print(f"total {total} substituicoes no RuntimeTextGemini")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
