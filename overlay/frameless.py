"""
@description Janela sem moldura nativa mas COM redimensionar/arrastar/snap/sombra do
             Windows (via WM_NCCALCSIZE + WM_NCHITTEST). A barra do topo (arrastável)
             é a `_build_topbar()` do app.
@connects mixado por overlay.gallery.Gallery
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

from PySide6.QtCore import QPoint, Qt

_IS_WIN = sys.platform == "win32"

WM_NCCALCSIZE = 0x0083
WM_NCHITTEST = 0x0084
WM_GETMINMAXINFO = 0x0024

HTCLIENT = 1
HTCAPTION = 2
HTLEFT, HTRIGHT, HTTOP, HTTOPLEFT, HTTOPRIGHT = 10, 11, 12, 13, 14
HTBOTTOM, HTBOTTOMLEFT, HTBOTTOMRIGHT = 15, 16, 17

_GWL_STYLE = -16
_WS_CAPTION = 0x00C00000
_WS_THICKFRAME = 0x00040000
_WS_MINIMIZEBOX = 0x00020000
_WS_MAXIMIZEBOX = 0x00010000
_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_NOZORDER = 0x0004
_SWP_FRAMECHANGED = 0x0020

_BORDER = 6  # zona de resize (px lógicos)

if _IS_WIN:
    _dwm = ctypes.windll.dwmapi
    _user32 = ctypes.windll.user32
    _HMONITOR = ctypes.c_void_p

    # em 64-bit, HWND/HMONITOR são ponteiros — sem argtypes o ctypes trunca p/ 32-bit
    _user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    _user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    _user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
    _user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    _user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    _user32.GetWindowRect.restype = wintypes.BOOL
    _user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    _user32.MonitorFromWindow.restype = _HMONITOR
    _user32.GetMonitorInfoW.argtypes = [_HMONITOR, ctypes.c_void_p]
    _user32.GetMonitorInfoW.restype = wintypes.BOOL
    _user32.SetWindowPos.argtypes = [
        wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, wintypes.UINT,
    ]
    _user32.SetWindowPos.restype = wintypes.BOOL
    _user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    _user32.GetSystemMetrics.restype = ctypes.c_int
    _user32.GetSystemMetricsForDpi.argtypes = [ctypes.c_int, wintypes.UINT]
    _user32.GetSystemMetricsForDpi.restype = ctypes.c_int
    _user32.GetDpiForWindow.argtypes = [wintypes.HWND]
    _user32.GetDpiForWindow.restype = wintypes.UINT
    _user32.GetWindowPlacement.argtypes = [wintypes.HWND, ctypes.c_void_p]
    _user32.GetWindowPlacement.restype = wintypes.BOOL

    _SW_MAXIMIZE = 3

    class _WINDOWPLACEMENT(ctypes.Structure):
        _fields_ = [
            ("length", wintypes.UINT), ("flags", wintypes.UINT),
            ("showCmd", wintypes.UINT),
            ("ptMinPosition", wintypes.POINT), ("ptMaxPosition", wintypes.POINT),
            ("rcNormalPosition", wintypes.RECT),
        ]

    _SM_CXSIZEFRAME = 32
    _SM_CYSIZEFRAME = 33
    _SM_CXPADDEDBORDER = 92

    class _MARGINS(ctypes.Structure):
        _fields_ = [("l", ctypes.c_int), ("r", ctypes.c_int),
                    ("t", ctypes.c_int), ("b", ctypes.c_int)]

    class _NCCALCSIZE_PARAMS(ctypes.Structure):
        _fields_ = [("rgrc", wintypes.RECT * 3), ("lppos", ctypes.c_void_p)]

    def _win_maximized(hwnd) -> bool:
        try:
            wp = _WINDOWPLACEMENT()
            wp.length = ctypes.sizeof(_WINDOWPLACEMENT)
            if _user32.GetWindowPlacement(hwnd, ctypes.byref(wp)):
                return wp.showCmd == _SW_MAXIMIZE
        except Exception:  # noqa: BLE001
            pass
        return False

    def _frame_size(hwnd):
        try:
            dpi = _user32.GetDpiForWindow(hwnd) or 96
            fx = (_user32.GetSystemMetricsForDpi(_SM_CXSIZEFRAME, dpi)
                  + _user32.GetSystemMetricsForDpi(_SM_CXPADDEDBORDER, dpi))
            fy = (_user32.GetSystemMetricsForDpi(_SM_CYSIZEFRAME, dpi)
                  + _user32.GetSystemMetricsForDpi(_SM_CXPADDEDBORDER, dpi))
            if fx and fy:
                return fx, fy
        except Exception:  # noqa: BLE001
            pass
        return 8, 8

else:
    def _win_maximized(hwnd) -> bool:  # noqa: ARG001
        return False

    def _frame_size(hwnd):  # noqa: ARG001
        return 8, 8


class FramelessMixin:
    """Requer: self é QWidget/QMainWindow com Qt.FramelessWindowHint.
    Deve definir self._titlebar (widget) para a área arrastável."""

    _titlebar = None

    def _init_frameless(self) -> None:
        if not _IS_WIN:
            return
        hwnd = int(self.winId())
        # devolve os estilos WS_ que o FramelessWindowHint tira — sem eles o Windows
        # não faz: minimizar direito, arrastar janela maximizada p/ outra tela,
        # snap, sombra. O WM_NCCALCSIZE esconde os pixels da moldura.
        try:
            style = _user32.GetWindowLongPtrW(hwnd, _GWL_STYLE)
            style |= (_WS_CAPTION | _WS_THICKFRAME | _WS_MINIMIZEBOX | _WS_MAXIMIZEBOX)
            _user32.SetWindowLongPtrW(hwnd, _GWL_STYLE, style)
            _user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                 _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOZORDER | _SWP_FRAMECHANGED)
        except Exception:  # noqa: BLE001
            pass
        # sombra + animações + snap do Windows
        try:
            _dwm.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(_MARGINS(0, 0, 1, 0)))
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    def nativeEvent(self, event_type, message):  # noqa: N802
        if not _IS_WIN or bytes(event_type) != b"windows_generic_MSG":
            return super().nativeEvent(event_type, message)

        msg = wintypes.MSG.from_address(int(message))

        if msg.message == WM_NCCALCSIZE and msg.wParam:
            # remove a moldura não-cliente. MAS quando maximizada (inclusive por
            # Aero Snap arrastando pro topo), o Windows posiciona a janela ~8px
            # pra fora de cada borda — sem subtrair isso do rect cliente, o
            # conteúdo vaza pra fora da tela e por baixo da barra de tarefas.
            if _win_maximized(msg.hWnd) and not self.isFullScreen():
                fx, fy = _frame_size(msg.hWnd)
                p = _NCCALCSIZE_PARAMS.from_address(int(msg.lParam) & ((1 << 64) - 1))
                p.rgrc[0].left += fx
                p.rgrc[0].top += fy
                p.rgrc[0].right -= fx
                p.rgrc[0].bottom -= fy
            return True, 0

        if msg.message == WM_NCHITTEST:
            return True, self._hit_test(msg)

        if msg.message == WM_GETMINMAXINFO and self.windowHandle():
            self._fix_maximize(msg.lParam)
            return True, 0     # True = não deixa o DefWindowProc sobrescrever

        return super().nativeEvent(event_type, message)

    # ------------------------------------------------------------------
    def _hit_test(self, msg) -> int:
        rect = wintypes.RECT()
        _user32.GetWindowRect(msg.hWnd, ctypes.byref(rect))
        gx = ctypes.c_short(msg.lParam & 0xFFFF).value
        gy = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value

        dpr = self.devicePixelRatioF() or 1.0
        bw = int(_BORDER * dpr)

        left = gx - rect.left < bw
        right = rect.right - gx < bw
        top = gy - rect.top < bw
        bottom = rect.bottom - gy < bw

        if not _win_maximized(msg.hWnd):
            if top and left:
                return HTTOPLEFT
            if top and right:
                return HTTOPRIGHT
            if bottom and left:
                return HTBOTTOMLEFT
            if bottom and right:
                return HTBOTTOMRIGHT
            if left:
                return HTLEFT
            if right:
                return HTRIGHT
            if top:
                return HTTOP
            if bottom:
                return HTBOTTOM

        # área da barra de título → arrastar (menos sobre botões/checkboxes)
        from PySide6.QtWidgets import QAbstractButton  # import tardio

        tb = self._titlebar
        if tb is not None:
            local = self.mapFromGlobal(QPoint(int(gx / dpr), int(gy / dpr)))
            top_left = tb.mapTo(self, tb.rect().topLeft())
            if QPoint(top_left).y() <= local.y() < QPoint(top_left).y() + tb.height():
                w = self.childAt(local)
                while w is not None and w is not self:
                    if isinstance(w, QAbstractButton) or w.property("titlebar_button"):
                        return HTCLIENT
                    w = w.parentWidget()
                return HTCAPTION
        return HTCLIENT

    def _fix_maximize(self, lparam: int) -> None:
        """Impede a janela maximizada de cobrir a barra de tarefas."""
        class MINMAXINFO(ctypes.Structure):
            _fields_ = [
                ("ptReserved", wintypes.POINT),
                ("ptMaxSize", wintypes.POINT),
                ("ptMaxPosition", wintypes.POINT),
                ("ptMinTrackSize", wintypes.POINT),
                ("ptMaxTrackSize", wintypes.POINT),
            ]

        MONITOR_DEFAULTTONEAREST = 2

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        hwnd = int(self.winId())
        hmon = _user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        if not hmon:
            return
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if not _user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            return
        work = mi.rcWork
        mon = mi.rcMonitor
        w = work.right - work.left
        h = work.bottom - work.top
        info = MINMAXINFO.from_address(lparam)
        # maximizada = exatamente a área de trabalho (não cobre a barra de tarefas
        # nem vaza pra fora do monitor)
        info.ptMaxPosition.x = work.left - mon.left
        info.ptMaxPosition.y = work.top - mon.top
        info.ptMaxSize.x = w
        info.ptMaxSize.y = h
        # limites de arrasto — em pixels FÍSICOS (a msg é physical)
        dpr = self.devicePixelRatioF() or 1.0
        info.ptMinTrackSize.x = int(self.minimumWidth() * dpr)
        info.ptMinTrackSize.y = int(self.minimumHeight() * dpr)
        info.ptMaxTrackSize.x = w
        info.ptMaxTrackSize.y = h
