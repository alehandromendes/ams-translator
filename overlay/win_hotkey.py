"""
@description Atalhos globais via Win32 RegisterHotKey — funcionam com o app em segundo
             plano (sem foco), inclusive por cima de jogos em janela/borderless, e sem
             thread de hook nem consumo de CPU. Fallback: lib `keyboard`.
@connects usado por overlay.gallery
"""
from __future__ import annotations

import ctypes
import queue
import sys
import threading
from ctypes import wintypes

_IS_WIN = sys.platform == "win32"

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_APP = 0x8000          # acorda o loop pra drenar comandos (bind/unbind/quit)

# nome (formato da lib `keyboard`) -> virtual-key code
_VK: dict[str, int] = {}
for _i in range(1, 25):                      # F1..F24
    _VK[f"f{_i}"] = 0x70 + (_i - 1)
for _c in range(ord("a"), ord("z") + 1):     # a..z
    _VK[chr(_c)] = _c - 32
for _d in range(10):                         # 0..9
    _VK[str(_d)] = 0x30 + _d
for _n in range(10):                         # numpad 0..9
    _VK[f"num {_n}"] = 0x60 + _n
_VK.update({
    "space": 0x20, "tab": 0x09, "enter": 0x0D, "esc": 0x1B, "backspace": 0x08,
    "home": 0x24, "end": 0x23, "insert": 0x2D, "delete": 0x2E, "del": 0x2E,
    "page up": 0x21, "page down": 0x22, "pageup": 0x21, "pagedown": 0x22,
    "pgup": 0x21, "pgdn": 0x22, "pgdown": 0x22,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "print screen": 0x2C, "scroll lock": 0x91, "pause": 0x13,
    "-": 0xBD, "=": 0xBB, "[": 0xDB, "]": 0xDD, ";": 0xBA, "'": 0xDE,
    ",": 0xBC, ".": 0xBE, "/": 0xBF, "`": 0xC0, "\\": 0xDC,
})


def parse_combo(combo: str) -> tuple[int, int] | None:
    """'ctrl+shift+f9' -> (mods, vk). None se a tecla não for reconhecida."""
    mods = MOD_NOREPEAT
    key: str | None = None
    for part in combo.lower().replace(" +", "+").replace("+ ", "+").split("+"):
        part = part.strip()
        if part in ("ctrl", "control"):
            mods |= MOD_CONTROL
        elif part == "alt":
            mods |= MOD_ALT
        elif part == "shift":
            mods |= MOD_SHIFT
        elif part in ("win", "windows", "super", "meta", "cmd"):
            mods |= MOD_WIN
        elif part:
            key = part
    vk = _VK.get(key or "")
    return (mods, vk) if vk else None


if _IS_WIN:
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    _HWND_MESSAGE = wintypes.HWND(-3)
    _GWLP_WNDPROC = -4
    _WNDPROC = ctypes.WINFUNCTYPE(
        ctypes.c_ssize_t, wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM
    )

    for _fn, _res, _args in (
        ("CreateWindowExW", wintypes.HWND,
         [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
          ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
          wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]),
        ("DestroyWindow", wintypes.BOOL, [wintypes.HWND]),
        ("DefWindowProcW", ctypes.c_ssize_t,
         [wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]),
        ("CallWindowProcW", ctypes.c_ssize_t,
         [ctypes.c_void_p, wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]),
        ("SetWindowLongPtrW", ctypes.c_void_p,
         [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]),
        ("GetWindowLongPtrW", ctypes.c_void_p, [wintypes.HWND, ctypes.c_int]),
        ("RegisterHotKey", wintypes.BOOL,
         [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]),
        ("UnregisterHotKey", wintypes.BOOL, [wintypes.HWND, ctypes.c_int]),
        ("GetMessageW", wintypes.BOOL,
         [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.UINT]),
        ("TranslateMessage", wintypes.BOOL, [ctypes.c_void_p]),
        ("DispatchMessageW", ctypes.c_ssize_t, [ctypes.c_void_p]),
        ("PostThreadMessageW", wintypes.BOOL,
         [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]),
        ("PostQuitMessage", None, [ctypes.c_int]),
    ):
        getattr(_user32, _fn).restype = _res
        getattr(_user32, _fn).argtypes = _args

    _kernel32.GetCurrentThreadId.restype = wintypes.DWORD

    class WinHotkeys:
        """Atalhos globais via Win32 RegisterHotKey. Roda uma thread DEDICADA com
        janela 'message-only' e loop GetMessage próprio — não depende de como o
        event loop do Qt despacha (o WM_HOTKEY do RegisterHotKey vai pra fila da
        thread que registrou; se essa for a thread do Qt, na prática o 1º atalho
        às vezes se perde e a entrega fica imprevisível sob jogo em foco).
        Os callbacks disparam NA thread — quem usa deve marshalar pro Qt
        (HotkeyBridge.triggered com QueuedConnection)."""

        def __init__(self) -> None:
            self._map: dict[int, callable] = {}   # hid -> callback
            self._next = 1
            self.taken: list[str] = []            # combos já em uso por outro app (1409)
            self._hwnd = None
            self._tid = 0
            self._cmds: "queue.Queue[tuple]" = queue.Queue()
            self._ready = threading.Event()
            self._proc = _WNDPROC(self._wnd_proc)   # manter a referência viva!
            self._old_proc = 0
            self._thread = threading.Thread(target=self._run, name="win-hotkeys",
                                            daemon=True)
            self._thread.start()
            self._ready.wait(2.0)

        # ---- thread dedicada -------------------------------------------
        def _run(self) -> None:
            self._tid = _kernel32.GetCurrentThreadId()
            self._hwnd = _user32.CreateWindowExW(
                0, "Static", "overlay-hotkeys", 0, 0, 0, 0, 0,
                _HWND_MESSAGE, None, None, None,
            )
            if self._hwnd:
                self._old_proc = _user32.GetWindowLongPtrW(self._hwnd, _GWLP_WNDPROC) or 0
                _user32.SetWindowLongPtrW(
                    self._hwnd, _GWLP_WNDPROC,
                    ctypes.cast(self._proc, ctypes.c_void_p),
                )
            self._ready.set()
            if not self._hwnd:
                return

            msg = wintypes.MSG()
            pmsg = ctypes.byref(msg)
            while _user32.GetMessageW(pmsg, None, 0, 0) > 0:
                if msg.message == WM_APP:
                    if self._drain_cmds():      # True = pediram pra sair
                        break
                    continue
                _user32.TranslateMessage(pmsg)
                _user32.DispatchMessageW(pmsg)

            for hid in list(self._map):
                _user32.UnregisterHotKey(self._hwnd, hid)
            _user32.DestroyWindow(self._hwnd)
            self._hwnd = None

        def _drain_cmds(self) -> bool:
            while True:
                try:
                    cmd = self._cmds.get_nowait()
                except queue.Empty:
                    return False
                if cmd[0] == "quit":
                    return True
                if cmd[0] == "clear":
                    for hid in list(self._map):
                        _user32.UnregisterHotKey(self._hwnd, hid)
                    self._map.clear()
                    self.taken = []
                elif cmd[0] == "bind":
                    _, combo, callback, result = cmd
                    result.append(self._do_bind(combo, callback))
                    self._ready_pulse()

        _bind_done: threading.Event | None = None

        def _ready_pulse(self) -> None:
            if self._bind_done is not None:
                self._bind_done.set()

        def _do_bind(self, combo: str, callback) -> str | None:
            """registra 1 combo NA thread. retorna None se ok, ou o combo se falhou."""
            parsed = parse_combo(combo)
            if parsed is None:
                return combo
            mods, vk = parsed
            hid = self._next
            self._next += 1
            ctypes.set_last_error(0)
            if _user32.RegisterHotKey(self._hwnd, hid, mods, vk):
                self._map[hid] = callback
                return None
            if ctypes.get_last_error() == 1409:
                self.taken.append(combo)
            return combo

        def _wnd_proc(self, hwnd, msg, wparam, lparam):
            if msg == WM_HOTKEY:
                cb = self._map.get(wparam)
                if cb is not None:
                    try:
                        cb()
                    except Exception:  # noqa: BLE001
                        pass
                    return 0
            if self._old_proc:
                return _user32.CallWindowProcW(self._old_proc, hwnd, msg, wparam, lparam)
            return _user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        def _wake(self) -> None:
            if self._tid:
                _user32.PostThreadMessageW(self._tid, WM_APP, 0, 0)

        # ---- API pública (thread principal) --------------------------
        def bind(self, combos: list[str], callback) -> list[str]:
            """Registra cada combo → callback. Retorna os que falharam; acumula
            os 'já em uso' em self.taken."""
            if not self._hwnd:
                return list(combos)
            failed: list[str] = []
            for combo in combos:
                result: list = []
                self._bind_done = threading.Event()
                self._cmds.put(("bind", combo, callback, result))
                self._wake()
                self._bind_done.wait(1.0)
                if result and result[0] is not None:
                    failed.append(result[0])
            self._bind_done = None
            return failed

        def clear(self) -> None:
            if not self._hwnd:
                return
            self._cmds.put(("clear",))
            self._wake()

        def dispose(self) -> None:
            if self._tid:
                self._cmds.put(("quit",))
                self._wake()
                self._thread.join(1.5)
            self._tid = 0

    def is_elevated() -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:  # noqa: BLE001
            return False

    def relaunch_as_admin() -> bool:
        """Reabre o próprio processo com UAC. True se o relançamento foi disparado."""
        if is_elevated():
            return False
        import subprocess  # noqa: F401  (só p/ list2cmdline)

        if getattr(sys, "frozen", False):
            exe, params = sys.executable, ""
        else:
            exe = sys.executable
            params = subprocess.list2cmdline(sys.argv)
        try:
            rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
            return int(rc) > 32
        except Exception:  # noqa: BLE001
            return False

else:  # não-Windows (dev em outro SO)
    WinHotkeys = None  # type: ignore

    def is_elevated() -> bool:
        return False

    def relaunch_as_admin() -> bool:
        return False
