# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for tidemark's embedded Python analyzer.
# Run from project root: pyinstaller analyze.spec --distpath dist
from PyInstaller.utils.hooks import collect_all

scipy_datas, scipy_binaries, scipy_hiddenimports = collect_all('scipy')
numpy_datas, numpy_binaries, numpy_hiddenimports = collect_all('numpy')

a = Analysis(
    ['python/analyze.py'],
    pathex=['python'],
    binaries=scipy_binaries + numpy_binaries,
    datas=scipy_datas + numpy_datas,
    hiddenimports=['pymannkendall'] + scipy_hiddenimports + numpy_hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['flask', 'gunicorn', 'tkinter', 'matplotlib', 'PIL', 'cv2'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='analyze',
    debug=False,
    strip=False,
    upx=False,
    console=True,
)
