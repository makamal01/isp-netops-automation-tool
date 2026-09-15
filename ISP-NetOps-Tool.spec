# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for the packaged Windows app.

Build with:
    pyinstaller --noconfirm ISP-NetOps-Tool.spec

A plain CLI invocation (`pyinstaller --onefile ... app/main.py`) can't
express one thing this app's build genuinely needs: PySide6's own
PyInstaller hook bundles Qt Quick/QML/PDF/VirtualKeyboard/3D/Svg
unconditionally, regardless of `--exclude-module` - this app only ever
imports QtCore/QtGui/QtWidgets (verified via
`grep -rhoE "from PySide6\.[A-Za-z]+" app/`), so ~8MB of that is dead
weight in the shipped exe. The only way to actually drop it is to filter
Analysis.binaries after the fact, which requires a .spec file.
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

SPEC_DIR = Path(SPECPATH)

netmiko_datas, netmiko_binaries, netmiko_hidden = collect_all('netmiko')
ntc_datas, ntc_binaries, ntc_hidden = collect_all('ntc_templates')

a = Analysis(
    [str(SPEC_DIR / 'app' / 'main.py')],
    pathex=[str(SPECPATH)],
    binaries=netmiko_binaries + ntc_binaries,
    datas=[(str(SPEC_DIR / 'app' / 'assets'), 'app/assets')] + netmiko_datas + ntc_datas,
    hiddenimports=netmiko_hidden + ntc_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# Qt submodules this QtWidgets-only app never imports. PySide6's hook
# bundles them regardless of --exclude-module; stripping them here after
# analysis is the only way to actually drop them from the build.
_UNUSED_QT_BINARIES = (
    'Qt6Quick', 'Qt6Qml', 'Qt6Pdf', 'Qt6VirtualKeyboard',
    'Qt6Multimedia', 'Qt63D', 'Qt6Svg', 'Qt6Sensors', 'Qt6Positioning',
    'Qt6WebEngine', 'Qt6Designer', 'Qt6Help', 'Qt6Test', 'Qt6Bluetooth',
    'Qt6Nfc', 'Qt6RemoteObjects', 'Qt6SerialPort', 'Qt6SerialBus',
    'Qt6Charts', 'Qt6DataVisualization', 'Qt6Location', 'Qt6WebSockets',
)
a.binaries = [
    entry for entry in a.binaries
    if not any(pattern in entry[0] for pattern in _UNUSED_QT_BINARIES)
]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ISP-NetOps-Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(SPEC_DIR / 'app' / 'assets' / 'icon.ico'),
)
