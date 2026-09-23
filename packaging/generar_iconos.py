"""Genera los iconos de la app a partir de packaging/iconos/lectormd.svg.

Salida:
  packaging/iconos/png/lectormd-<N>.png   (Linux: hicolor y AppImage)
  packaging/iconos/lectormd.ico           (Windows: ejecutable e instalador)

Uso:  python packaging/generar_iconos.py
"""

import io
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QIODevice, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication, QImage, QPainter  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

RAIZ = Path(__file__).resolve().parent / "iconos"
TAMANOS_PNG = (16, 24, 32, 48, 64, 128, 256, 512)
TAMANOS_ICO = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def rasterizar(render: QSvgRenderer, tam: int) -> QImage:
    img = QImage(tam, tam, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    render.render(p, QRectF(0, 0, tam, tam))
    p.end()
    return img


def a_png(img: QImage) -> bytes:
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


def ico(imagenes: dict[int, bytes]) -> bytes:
    """Escribe un .ico con PNG embebidos (válido desde Windows Vista)."""
    cabecera = (0).to_bytes(2, "little") + (1).to_bytes(2, "little") + len(imagenes).to_bytes(2, "little")
    directorio, datos = b"", b""
    desplazamiento = 6 + 16 * len(imagenes)
    for tam, png in sorted(imagenes.items()):
        lado = 0 if tam >= 256 else tam  # 0 significa 256 en el formato ICO
        directorio += bytes([lado, lado, 0, 0]) + (1).to_bytes(2, "little") + (32).to_bytes(2, "little")
        directorio += len(png).to_bytes(4, "little") + desplazamiento.to_bytes(4, "little")
        datos += png
        desplazamiento += len(png)
    return cabecera + directorio + datos


def main() -> int:
    QGuiApplication(sys.argv[:1])
    render = QSvgRenderer(str(RAIZ / "lectormd.svg"))
    if not render.isValid():
        print("SVG no válido", file=sys.stderr)
        return 1
    carpeta_png = RAIZ / "png"
    carpeta_png.mkdir(exist_ok=True)
    for tam in TAMANOS_PNG:
        (carpeta_png / f"lectormd-{tam}.png").write_bytes(a_png(rasterizar(render, tam)))
    (RAIZ / "lectormd.ico").write_bytes(ico({t: a_png(rasterizar(render, t)) for t in TAMANOS_ICO}))
    print(f"{len(TAMANOS_PNG)} PNG y lectormd.ico generados en {RAIZ}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
