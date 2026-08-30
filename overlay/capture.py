"""
@description Captura de tela (região configurada) via mss. Sem dependência de Qt.
@connects usado por overlay.gallery (grab) e overlay.gallery (list_monitors no diálogo)
"""
from __future__ import annotations

import mss
from PIL import Image


def list_monitors() -> list[dict]:
    with mss.mss() as sct:
        return [dict(m) for m in sct.monitors]


def grab(region: dict | None = None, monitor: int = 1) -> Image.Image:
    """region: {left, top, width, height} absoluto. Se None, captura o monitor inteiro."""
    with mss.mss() as sct:
        if region:
            area = {
                "left": int(region["left"]),
                "top": int(region["top"]),
                "width": int(region["width"]),
                "height": int(region["height"]),
            }
        else:
            mons = sct.monitors
            area = mons[monitor] if monitor < len(mons) else mons[1]
        raw = sct.grab(area)
        return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
