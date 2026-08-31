"""
@description Gera assets/icon.ico e assets/logo.png do AMS Translator.
@connects icon.ico é usado por overlay.spec (build do .exe) e overlay.gallery (setWindowIcon)
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent

BLUE_TOP = (37, 99, 235)      # #2563eb
BLUE_BOT = (29, 78, 216)      # #1d4ed8
WHITE = (255, 255, 255)
INK = (23, 37, 84)            # #172554

CJK_FONT = "C:/Windows/Fonts/msyh.ttc"
LAT_FONT = "C:/Windows/Fonts/arialbd.ttf"


def _rounded_mask(size: int, radius_ratio: float = 0.225) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    r = int(size * radius_ratio)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=255)
    return m


def _font(path: str, px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, px)


def _centered(draw, xy, text, font, fill, stroke=0, stroke_fill=None):
    l, t, r, b = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    draw.text((xy[0] - (r - l) / 2 - l, xy[1] - (b - t) / 2 - t), text, font=font,
              fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)


def render(size: int) -> Image.Image:
    S = size * 4  # supersample
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # fundo: gradiente vertical azul
    grad = Image.new("RGB", (1, S))
    for y in range(S):
        k = y / (S - 1)
        grad.putpixel((0, y), tuple(int(a + (b - a) * k) for a, b in zip(BLUE_TOP, BLUE_BOT)))
    grad = grad.resize((S, S))
    img.paste(grad, (0, 0), _rounded_mask(S))

    # barra de legenda (caption) no terço inferior
    bar_h = int(S * 0.20)
    bar_y0 = int(S * 0.60)
    pad = int(S * 0.14)
    d.rounded_rectangle(
        [pad, bar_y0, S - pad, bar_y0 + bar_h],
        radius=int(bar_h * 0.28), fill=(255, 255, 255, 235),
    )
    # duas "linhas de texto" na barra
    line_h = int(bar_h * 0.16)
    lx0 = pad + int(S * 0.05)
    d.rounded_rectangle([lx0, bar_y0 + int(bar_h * 0.28),
                         S - pad - int(S * 0.18), bar_y0 + int(bar_h * 0.28) + line_h],
                        radius=line_h // 2, fill=(148, 163, 184, 255))
    d.rounded_rectangle([lx0, bar_y0 + int(bar_h * 0.60),
                         S - pad - int(S * 0.34), bar_y0 + int(bar_h * 0.60) + line_h],
                        radius=line_h // 2, fill=(148, 163, 184, 255))

    # 文  →  A   na metade de cima
    cy = int(S * 0.34)
    f_cjk = _font(CJK_FONT, int(S * 0.34))
    f_lat = _font(LAT_FONT, int(S * 0.34))
    _centered(d, (int(S * 0.30), cy), "文", f_cjk, WHITE)
    _centered(d, (int(S * 0.70), cy), "A", f_lat, WHITE)
    # seta
    f_arrow = _font(LAT_FONT, int(S * 0.16))
    _centered(d, (int(S * 0.50), cy + int(S * 0.01)), "→", f_arrow, (191, 219, 254, 255))

    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    HERE.mkdir(exist_ok=True)
    sizes = [16, 24, 32, 48, 64, 128, 256]
    imgs = [render(s) for s in sizes]
    imgs[-1].save(HERE / "icon.ico", format="ICO",
                  sizes=[(s, s) for s in sizes])
    render(512).save(HERE / "logo.png")
    print("gerado:", HERE / "icon.ico", "e", HERE / "logo.png")


if __name__ == "__main__":
    main()
