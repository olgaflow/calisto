# -*- mode: python ; coding: utf-8 -*-
"""Spec PyInstaller pour le deploiement Windows de Calisto.

Construction :  python -m PyInstaller --noconfirm calisto.spec
Resultat      :  dist\\Calisto\\Calisto.exe  (aucune fenetre console)
"""

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

datas = (
    collect_data_files("customtkinter")
    + collect_data_files("tkinterweb")
    + collect_data_files("pypdfium2")
    + collect_data_files("pypdfium2_raw")
)

binaries = (
    collect_dynamic_libs("pypdfium2")
    + collect_dynamic_libs("pypdfium2_raw")
)

hiddenimports = [
    "customtkinter",
    "tkinterweb",
    "ollama",
    "ddgs",
    "PyPDF2",
    "fpdf",
    "ai_runtime",
    "image_generation",
    "dev_window",
    "pypdfium2",
    "pypdfium2_raw",
]

a = Analysis(
    ["app_desktop.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Calisto",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Calisto",
)
