"""
@description Parser/serializador mínimo para os arquivos de tradução do mod:
             `return { data = { [<int>] = "<str>", ... } }` (ou fragmentos `.parts/NNNN.lua`).
@connects overlay.gamefill.core
"""
from __future__ import annotations

import re

_ENTRY = re.compile(r'\[(\d+)\]\s*=\s*"((?:\\.|[^"\\])*)"', re.S)
_PARTS = re.compile(r"__parts\s*=\s*(\d+)")

_UNESCAPE = {
    "n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "'": "'",
    "a": "\a", "b": "\b", "f": "\f", "v": "\v",
}


def unescape(s: str) -> str:
    out: list[str] = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\\" and i + 1 < n:
            nx = s[i + 1]
            if nx in _UNESCAPE:
                out.append(_UNESCAPE[nx])
                i += 2
                continue
            if nx.isdigit():
                j = i + 1
                num = ""
                while j < n and s[j].isdigit() and len(num) < 3:
                    num += s[j]
                    j += 1
                out.append(chr(int(num)))
                i = j
                continue
            out.append(nx)
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def escape(s: str) -> str:
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    s = s.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    return s


def parse_entries(text: str) -> dict[int, str]:
    """Todas as entradas `[id] = "..."` de um .lua (índice ou fragmento)."""
    return {int(m.group(1)): unescape(m.group(2)) for m in _ENTRY.finditer(text)}


def parse_parts_count(text: str) -> int | None:
    m = _PARTS.search(text)
    return int(m.group(1)) if m else None


def dump_part(data: dict[int, str], header: str = "") -> str:
    lines = []
    if header:
        lines.append(header.rstrip("\n"))
    lines.append("return {")
    lines.append("    data = {")
    for k in sorted(data):
        lines.append(f'        [{k}] = "{escape(data[k])}",')
    lines.append("    },")
    lines.append("}")
    return "\n".join(lines) + "\n"
