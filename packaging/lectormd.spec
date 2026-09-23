# -*- mode: python ; coding: utf-8 -*-
"""Receta de PyInstaller para Windows y Linux.

Genera una carpeta autocontenida (onedir) en dist/:
  - Windows: dist/lectorMD/lectorMD.exe
  - Linux:   dist/lectormd/lectormd

Se usa onedir y no onefile a propósito: con Qt WebEngine (~200 MB), un
onefile se descomprime entero en cada arranque y tarda varios segundos.

Uso:  pyinstaller packaging/lectormd.spec --noconfirm
"""

import re
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

RAIZ = Path(SPECPATH).resolve().parent  # noqa: F821 — SPECPATH lo define PyInstaller
ES_WINDOWS = sys.platform == "win32"
NOMBRE = "lectorMD" if ES_WINDOWS else "lectormd"
VERSION = re.search(r'__version__ = "([^"]+)"', (RAIZ / "lectormd" / "__init__.py").read_text()).group(1)

# Módulos de Qt que PySide6 trae pero la app no usa: fuera, para adelgazar.
SOBRANTES = [
    "PySide6.Qt3DAnimation", "PySide6.Qt3DCore", "PySide6.Qt3DExtras", "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic", "PySide6.Qt3DRender", "PySide6.QtBluetooth", "PySide6.QtCharts",
    "PySide6.QtDataVisualization", "PySide6.QtGraphs", "PySide6.QtHttpServer",
    "PySide6.QtLocation", "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.QtNfc", "PySide6.QtQuick3D", "PySide6.QtRemoteObjects", "PySide6.QtScxml",
    "PySide6.QtSensors", "PySide6.QtSerialBus", "PySide6.QtSerialPort", "PySide6.QtSpatialAudio",
    "PySide6.QtSql", "PySide6.QtStateMachine", "PySide6.QtTest", "PySide6.QtTextToSpeech",
    "PySide6.QtWebSockets", "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtUiTools",
    "tkinter", "unittest", "pydoc", "doctest",
]

a = Analysis(
    [str(RAIZ / "packaging" / "lanzador.py")],
    pathex=[str(RAIZ)],
    datas=[
        (str(RAIZ / "lectormd" / "assets"), "lectormd/assets"),
        # latex2mathml lee su tabla de símbolos al importarse y no tiene hook.
        *collect_data_files("latex2mathml"),
    ],
    hiddenimports=["lectormd.app", "lectormd.exportar", "lectormd.renderer", "lectormd.iconos"],
    excludes=SOBRANTES,
    noarchive=False,
)

# --------------------------------------------------------------------------
# Poda. Qt WebEngine depende de Qt Quick, y los hooks de PySide6 arrastran por
# eso todo el árbol QML con sus bibliotecas (Qt3D, Charts, Multimedia…) más
# las traducciones de Chromium a 53 idiomas: ~150 MB que la app no usa.
#
# Es una lista de EXCLUSIÓN, calculada con ldd sobre lo que la app carga de
# verdad. En Windows las dependencias pueden variar y aquí no se pueden
# probar: excluyendo solo lo que seguro sobra, lo peor que puede pasar es que
# quede algo de más, nunca que falte algo necesario.
# --------------------------------------------------------------------------
MODULOS_QT_SOBRANTES = {
    "3DAnimation", "3DCore", "3DExtras", "3DInput", "3DLogic", "3DQuick",
    "3DQuickAnimation", "3DQuickExtras", "3DQuickInput", "3DQuickLogic",
    "3DQuickRender", "3DQuickScene2D", "3DQuickScene3D", "3DRender",
    "Charts", "ChartsQml", "Concurrent", "DataVisualization", "DataVisualizationQml",
    "Graphs", "GraphsWidgets", "Location", "Multimedia", "MultimediaQuick",
    "MultimediaWidgets", "PdfQuick", "PdfWidgets", "PositioningQuick", "QmlCore",
    "QmlLocalStorage", "QmlNetwork", "QmlXmlListModel", "Quick3D", "Quick3DAssetImport",
    "Quick3DAssetUtils", "Quick3DEffects", "Quick3DGlslParser", "Quick3DHelpers",
    "Quick3DHelpersImpl", "Quick3DIblBaker", "Quick3DParticleEffects",
    "Quick3DParticles", "Quick3DRuntimeRender", "Quick3DSpatialAudio", "Quick3DUtils",
    "Quick3DXr", "QuickControls2", "QuickControls2Basic", "QuickControls2BasicStyleImpl",
    "QuickControls2FluentWinUI3StyleImpl", "QuickControls2Fusion",
    "QuickControls2FusionStyleImpl", "QuickControls2Imagine",
    "QuickControls2ImagineStyleImpl", "QuickControls2Impl", "QuickControls2Material",
    "QuickControls2MaterialStyleImpl", "QuickControls2Universal",
    "QuickControls2UniversalStyleImpl", "QuickControls2WindowsStyleImpl",
    "QuickDialogs2", "QuickDialogs2QuickImpl", "QuickDialogs2Utils", "QuickEffects",
    "QuickLayouts", "QuickParticles", "QuickShapes", "QuickShapesDesignHelpers",
    "QuickTemplates2", "QuickTest", "QuickTimeline", "QuickTimelineBlendTrees",
    "QuickVectorImage", "QuickVectorImageGenerator", "QuickVectorImageHelpers",
    "RemoteObjects", "RemoteObjectsQml", "Scxml", "ScxmlQml", "Sensors", "SensorsQuick",
    "SerialBus", "SerialPort", "ShaderTools", "SpatialAudio", "Sql", "StateMachine",
    "StateMachineQml", "Test", "TextToSpeech", "VirtualKeyboardSettings",
    "WaylandCompositor", "WebChannelQuick", "WebEngineQuick",
    "WebEngineQuickDelegatesQml", "WebSockets", "WebView", "WebViewQuick",
    "Bluetooth", "Nfc", "Help", "Designer", "DesignerComponents", "UiTools",
}
MODULOS_QT_SOBRANTES |= {m for m in MODULOS_QT_SOBRANTES if m.startswith("Labs")}
IDIOMAS = ("en", "en-US", "es", "es-419")
_LIB_QT = re.compile(r"^(?:lib)?Qt6([A-Za-z0-9]+?)(?:\.so(?:\.\d+)*|\.dll)$")


def _sobra(destino: str) -> bool:
    ruta = destino.replace("\\", "/")
    nombre = ruta.rsplit("/", 1)[-1]
    if "/qml/" in f"/{ruta}":
        return True
    m = _LIB_QT.match(nombre)
    if m and (m.group(1) in MODULOS_QT_SOBRANTES or m.group(1).startswith("Labs")):
        return True
    if "/translations/" in f"/{ruta}":
        if "/qtwebengine_locales/" in ruta:
            return nombre.split(".")[0] not in IDIOMAS
        # El idioma va al final: qtbase_es.qm, qt_help_es.qm, qtbase_pt_BR.qm
        m = re.search(r"_([a-z]{2,3})(?:_[A-Za-z]{2,4})?\.qm$", nombre)
        return bool(m) and m.group(1) not in ("es", "en")
    return False


antes = len(a.binaries) + len(a.datas)
a.binaries = [e for e in a.binaries if not _sobra(e[0])]
a.datas = [e for e in a.datas if not _sobra(e[0])]
print(f"lectorMD: poda de Qt — {antes - len(a.binaries) - len(a.datas)} archivos fuera")

pyz = PYZ(a.pure)

extra_exe = {}
if ES_WINDOWS:
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo, VarStruct,
        VSVersionInfo,
    )

    numeros = tuple(int(n) for n in (VERSION.split(".") + ["0"] * 4)[:4])
    extra_exe["version"] = VSVersionInfo(
        ffi=FixedFileInfo(filevers=numeros, prodvers=numeros),
        kids=[
            StringFileInfo([StringTable("040A04B0", [
                StringStruct("FileDescription", "lectorMD — visor de Markdown"),
                StringStruct("ProductName", "lectorMD"),
                StringStruct("FileVersion", VERSION),
                StringStruct("ProductVersion", VERSION),
                StringStruct("OriginalFilename", "lectorMD.exe"),
                StringStruct("InternalName", "lectorMD"),
            ])]),
            VarFileInfo([VarStruct("Translation", [0x040A, 1200])]),
        ],
    )
    extra_exe["icon"] = str(RAIZ / "packaging" / "iconos" / "lectormd.ico")

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NOMBRE,
    console=False,
    upx=False,  # UPX rompe las bibliotecas de Qt
    **extra_exe,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name=NOMBRE)
