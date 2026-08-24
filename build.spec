# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：单文件、无控制台、内嵌 assets 与图标。"""
import sys
from pathlib import Path

block_cipher = None

here = Path(SPECPATH).resolve()
assets = here / 'assets'

datas = []
if assets.exists():
    datas.append((str(assets), 'assets'))

a = Analysis(
    ['main.py'],
    pathex=[str(here)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtCore',
        'PySide6.QtSvg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuick3D',
              'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
              'PySide6.QtDesigner', 'PySide6.QtHelp', 'PySide6.QtMultimedia',
              'PySide6.QtTest', 'PySide6.QtSql', 'PySide6.QtNetwork',
              'PySide6.QtXml', 'PySide6.QtPrintSupport'],
    win_no_prefer_redirect=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='双猫桌面宠物',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,            # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(here / 'assets' / 'icons' / 'app.ico'),
)
