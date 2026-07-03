# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hidden = []
hidden += collect_submodules('oracledb')
hidden += collect_submodules('cryptography')
hidden += collect_submodules('pandas')
hidden += collect_submodules('openpyxl')
hidden += [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
]

a = Analysis(
    ['plan_pracy.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.ini', '.'),
        ('db/schema.sql', 'db'),
        ('db/seed.sql', 'db'),
    ],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PlanPracy',
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
    name='PlanPracy',
)
