# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['E:/Documents/deepseek-harness/default-workspace/md2edrawmind/desktop_launcher.py'],
    pathex=['E:/Documents/deepseek-harness/default-workspace/md2edrawmind'],
    binaries=[],
    datas=[('E:/Documents/deepseek-harness/default-workspace/md2edrawmind/build/desktop-stage', '.')],
    hiddenimports=['md2edrawmind.server', 'md2edrawmind.pipeline'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'PyQt5'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='md2edrawmind',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='md2edrawmind',
)
