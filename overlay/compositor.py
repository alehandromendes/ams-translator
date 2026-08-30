"""
@description Compõe a imagem "traduzida" — cobre a legenda original e escreve o texto PT
             encaixado na mesma área, estilo Google Tradutor.
@connects usado por overlay.worker
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

_FONT_FALLBACKS = [
    "C:/Windows/Fonts/seguisb.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _resolve_font(preferred: str | None) -> str | None:
    for cand in [preferred, *_FONT_FALLBACKS]:
        if cand and Path(cand).exists():
            return cand
    return None


def _load_font(path: str | None, size: int) -> ImageFont.ImageFont:
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:  # noqa: BLE001
            pass
    return ImageFont.load_default()


def _bg_color(arr: np.ndarray, rect: tuple[int, int, int, int], pad: int = 8) -> tuple[int, int, int]:
    h, w = arr.shape[:2]
    x0, y0, x1, y1 = rect
    x0c, y0c, x1c, y1c = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
    strips = [
        arr[max(0, y0 - pad):y0c, x0c:x1c],
        arr[y1c:min(h, y1 + pad), x0c:x1c],
        arr[y0c:y1c, max(0, x0 - pad):x0c],
        arr[y0c:y1c, x1c:min(w, x1 + pad)],
    ]
    px = [s.reshape(-1, 3) for s in strips if s.size]
    if not px:
        return (16, 16, 16)
    med = np.median(np.concatenate(px, axis=0), axis=0)
    return tuple(int(c) for c in med)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines, cur = [], words[0]
    for word in words[1:]:
        trial = f"{cur} {word}"
        if draw.textbbox((0, 0), trial, font=font)[2] <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines


def _fit(draw, text, font_path, box_w, box_h):
    lo, hi = 9, max(11, box_h + 6)
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        font = _load_font(font_path, mid)
        lines = _wrap(draw, text, font, box_w)
        widths = [draw.textbbox((0, 0), ln, font=font)[2] for ln in lines]
        line_h = draw.textbbox((0, 0), "Ag", font=font)[3]
        gap = int(mid * 0.22)
        total_h = len(lines) * line_h + (len(lines) - 1) * gap
        if (max(widths, default=0) <= box_w) and (total_h <= box_h):
            best = (font, lines, line_h, gap)
            lo = mid + 1
        else:
            hi = mid - 1
    if best is None:
        font = _load_font(font_path, 10)
        lines = _wrap(draw, text, font, box_w)
        line_h = draw.textbbox((0, 0), "Ag", font=font)[3]
        best = (font, lines, line_h, int(10 * 0.22))
    return best


def compose(original: Image.Image, pairs: list[dict], font_path: str | None = None) -> Image.Image:
    """pairs: [{"rect": (x0, y0, x1, y1), "pt": "texto traduzido"}]."""
    font_path = _resolve_font(font_path)
    img = original.convert("RGB").copy()
    arr = np.asarray(img)
    draw = ImageDraw.Draw(img)

    for pr in pairs:
        pt = (pr.get("pt") or "").strip()
        if not pt:
            continue
        x0, y0, x1, y1 = pr["rect"]
        bg = _bg_color(arr, pr["rect"])
        m = 3
        draw.rectangle([x0 - m, y0 - m, x1 + m, y1 + m], fill=bg)

        lum = 0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]
        fg = (255, 255, 255) if lum < 140 else (17, 17, 17)
        stroke = (0, 0, 0) if fg[0] == 255 else (255, 255, 255)

        box_w, box_h = max(1, x1 - x0), max(1, y1 - y0)
        font, lines, line_h, gap = _fit(draw, pt, font_path, box_w, box_h)

        total_h = len(lines) * line_h + (len(lines) - 1) * gap
        cy = y0 + (box_h - total_h) // 2
        sw = max(1, getattr(font, "size", 12) // 12)
        for ln in lines:
            lw = draw.textbbox((0, 0), ln, font=font)[2]
            cx = x0 + (box_w - lw) // 2
            draw.text((cx, cy), ln, font=font, fill=fg,
                      stroke_width=sw, stroke_fill=stroke)
            cy += line_h + gap

    return img
