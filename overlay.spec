# -*- mode: python ; coding: utf-8 -*-
"""
@description Build do tradutor de legendas ao vivo num executável Windows.
@connects  pyinstaller overlay.spec   (gera dist/Tradutor de Legendas/)
"""
import certifi
from PyInstaller.utils.hooks import collect_all

datas = [
    ("glossary/names.csv", "glossary"),
    ("glossary/terms.csv", "glossary"),
    ("assets/icon.ico", "assets"),
    ("overlay/gamefill/game_terms.csv", "overlay/gamefill"),
    ("overlay/gamefill/fixes.csv", "overlay/gamefill"),
    ("overlay/gamefill/translations_index.json", "overlay/gamefill"),
    (certifi.where(), "."),          # -> _internal/cacert.pem  (SSL do requests)
]
binaries = []
hiddenimports = [
    "PySide6.QtSvg", "certifi",
    # importados sob demanda pelo botão "Traduzir jogo"
    "overlay.game_translate",
    "overlay.gamefill", "overlay.gamefill.patch_pt", "overlay.gamefill.library",
    "overlay.gamefill.core", "overlay.gamefill.luatable",
]

# rapidocr + onnxruntime trazem modelos .onnx e DLLs — precisa coletar tudo.
# (certifi NÃO entra aqui: só o cacert.pem acima é necessário; collect_all traria
#  dezenas de arquivinhos de teste que o Defender trava no rebuild.)
for pkg in ("rapidocr_onnxruntime", "onnxruntime"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["run_overlay.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=["tkinter", "PySide6.QtQuick", "PySide6.QtQml", "PySide6.Qt3DCore"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Tradutor de Legendas",
    console=False,
    disable_windowed_traceback=False,
    icon="assets/icon.ico",
    # SEMPRE elevado (manifest requireAdministrator). Sem admin, o hook de
    # teclado e — em alguns casos — o RegisterHotKey não pegam por cima de um
    # jogo que roda elevado (UIPI). O UAC aparece a cada abertura, de propósito.
    uac_admin=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="Tradutor de Legendas",
)
