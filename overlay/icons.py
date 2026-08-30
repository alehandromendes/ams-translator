"""
@description Ícones vetoriais (estilo Lucide, stroke) renderizados de SVG p/ QIcon.
             Substituem os emojis da interface.
@connects usado por overlay.gallery, overlay.reverse_panel
"""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_STROKE = "#dfe3e8"

# corpo interno de um <svg viewBox="0 0 24 24"> — stroke currentColor, sem fill
_PATHS: dict[str, str] = {
    "camera": '<path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3.2"/>',
    "region": '<path d="M4 8V6a2 2 0 0 1 2-2h2"/><path d="M16 4h2a2 2 0 0 1 2 2v2"/><path d="M20 16v2a2 2 0 0 1-2 2h-2"/><path d="M8 20H6a2 2 0 0 1-2-2v-2"/><path d="M8.5 12h7"/><path d="M12 8.5v7"/>',
    "monitor": '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8"/><path d="M12 17v4"/>',
    "paste": '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M8 4H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2"/><path d="M9 14l2 2 4-4"/>',
    "keyboard": '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 8h.01M10 8h.01M14 8h.01M18 8h.01M6 12h.01M10 12h.01M14 12h.01M18 12h.01M8 16h8"/>',
    "shield": '<path d="M12 3l7 3v5c0 5-3.2 7.7-7 9-3.8-1.3-7-4-7-9V6l7-3z"/>',
    "refresh": '<path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 4v5h-5"/>',
    "copy": '<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h2"/>',
    "save": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/>',
    "chevron-left": '<path d="M15 18l-6-6 6-6"/>',
    "chevron-right": '<path d="M9 18l6-6-6-6"/>',
    "arrow-right": '<path d="M5 12h14"/><path d="M13 6l6 6-6 6"/>',
    "languages": '<path d="M4 5h10"/><path d="M9 3v2c0 5-2.5 8-6 9"/><path d="M6 10c1.5 3 4 4.5 7 5"/><path d="M13 21l4-9 4 9"/><path d="M14.5 17h5"/>',
    "eye": '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>',
    "pin": '<path d="M12 17v5"/><path d="M9 10.8V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v5.8l1.6 2.4a1 1 0 0 1-.83 1.55H7.23a1 1 0 0 1-.83-1.55L8 10.8z"/>',
    "minimize": '<path d="M5 12h14"/>',
    "maximize": '<rect x="5" y="5" width="14" height="14" rx="1.5"/>',
    "restore": '<rect x="8" y="4" width="12" height="12" rx="1.5"/><path d="M4 8v10a2 2 0 0 0 2 2h10"/>',
    "close": '<path d="M6 6l12 12"/><path d="M18 6L6 18"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9c.3.71.98 1.19 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
}

_CACHE: dict[tuple[str, str, int], QIcon] = {}


def _svg(name: str, color: str, sw: float = 2.0) -> bytes:
    body = _PATHS[name]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="{sw}" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    ).encode("utf-8")


def pixmap(name: str, size: int = 20, color: str = _STROKE, sw: float = 2.0) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(_svg(name, color, sw)))
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    renderer.render(p, QRectF(0, 0, size, size))
    p.end()
    return QPixmap.fromImage(img)


def icon(name: str, color: str = _STROKE, sw: float = 2.0) -> QIcon:
    key = (name, color, int(sw * 10))
    if key not in _CACHE:
        ic = QIcon()
        for s in (16, 20, 24, 32, 48):
            ic.addPixmap(pixmap(name, s, color, sw))
        _CACHE[key] = ic
    return _CACHE[key]
