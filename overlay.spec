# -*- mode: python ; coding: utf-8 -*-
"""
@description Build do AMS Translator (tradução ao vivo) num executável Windows.
@connects  pyinstaller overlay.spec   (gera dist/AMS Translator/)
"""
import certifi
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

datas = [
    ("glossary/names.csv", "glossary"),
    ("glossary/terms.csv", "glossary"),
    ("assets/icon.ico", "assets"),
    ("overlay/gamefill/game_terms.csv", "overlay/gamefill"),
    ("overlay/gamefill/fixes.csv", "overlay/gamefill"),
    ("overlay/gamefill/translations_index.json", "overlay/gamefill"),
    ("overlay/gamefill/skill_overrides.csv", "overlay/gamefill"),
    # NADA específico de jogo vai no .exe. O AMS Translator é multi-jogo: TODO o
    # mod tl_translate (Init.lua + cpdd_user_settings.lua + hotpatch.lua + a
    # camada PT, 107 arquivos) é BAIXADO do repo ams-translator-traducoes na
    # hora de instalar. luamod/ e prebuilt/ só servem de fallback rodando do
    # código-fonte (dev).
    (certifi.where(), "."),          # -> _internal/cacert.pem  (SSL do requests)
]
binaries = []
hiddenimports = [
    "PySide6.QtSvg", "certifi",
    # importados sob demanda pelo botão "Traduzir jogo"
    "overlay.game_translate",
    "overlay.gamefill", "overlay.gamefill.patch_pt", "overlay.gamefill.library",
    "overlay.gamefill.core", "overlay.gamefill.luatable", "overlay.gamefill.gamepatch",
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
    name="AMS Translator",
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
    name="AMS Translator",
)
