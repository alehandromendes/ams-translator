"""
@description Atalho para rodar o tradutor de legendas ao vivo sem `-m`.
             Também é o entry point do build PyInstaller (overlay.spec).
@connects overlay.gallery.main
"""
import multiprocessing
import sys


def _set_dpi_awareness() -> None:
    """Per-Monitor DPI Aware v2 ANTES de qualquer coisa Qt — senão o Windows
    faz bitmap-scaling (janela 'com zoom errado' / desalinhada em telas escaladas)."""
    if sys.platform != "win32":
        return
    import ctypes

    for fn in (
        lambda: ctypes.windll.user32.SetProcessDpiAwarenessContext(-4),  # PMv2
        lambda: ctypes.windll.shcore.SetProcessDpiAwareness(2),          # PMv1
        lambda: ctypes.windll.user32.SetProcessDPIAware(),               # system
    ):
        try:
            if fn():
                return
        except Exception:  # noqa: BLE001
            continue


if __name__ == "__main__":
    multiprocessing.freeze_support()   # evita fork-bomb no .exe congelado
    _set_dpi_awareness()

    from overlay.gallery import main
    main()
