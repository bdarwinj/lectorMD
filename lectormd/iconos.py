"""Iconos de la barra de herramientas.

Se dibujan como SVG de trazo y se colorean en tiempo de ejecución, así se ven
igual en Windows y Linux y cambian de color con el tema.
"""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# Trazos en una caja de 24x24.
TRAZOS = {
    "abrir": '<path d="M3 7.5A1.5 1.5 0 0 1 4.5 6H9l2 2h8.5A1.5 1.5 0 0 1 21 9.5v8A1.5 1.5 0 0 1 19.5 19h-15A1.5 1.5 0 0 1 3 17.5z"/>',
    "indice": '<rect x="3" y="4.5" width="18" height="15" rx="2"/><path d="M9 4.5v15M5.5 8.5h1.5M5.5 11.5h1.5"/>',
    "buscar": '<circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 5.5 5.5"/>',
    "exportar": '<path d="M14 3.5H7A1.5 1.5 0 0 0 5.5 5v14A1.5 1.5 0 0 0 7 20.5h10a1.5 1.5 0 0 0 1.5-1.5V8z"/><path d="M14 3.5V8h4.5M12 11v6M9.5 14.5 12 17l2.5-2.5"/>',
    "pdf": '<path d="M14 3.5H7A1.5 1.5 0 0 0 5.5 5v14A1.5 1.5 0 0 0 7 20.5h10a1.5 1.5 0 0 0 1.5-1.5V8z"/><path d="M14 3.5V8h4.5"/><path d="M9 12.5h1.2a1.3 1.3 0 0 1 0 2.6H9v-2.6zm0 2.6V17"/>',
    "word": '<path d="M14 3.5H7A1.5 1.5 0 0 0 5.5 5v14A1.5 1.5 0 0 0 7 20.5h10a1.5 1.5 0 0 0 1.5-1.5V8z"/><path d="M14 3.5V8h4.5"/><path d="m8.5 12 1.2 5 1.8-4 1.8 4 1.2-5"/>',
    "menu": '<path d="M4.5 7h15M4.5 12h15M4.5 17h15"/>',
    "tema": '<path d="M20 14.2A8 8 0 1 1 9.8 4a6.3 6.3 0 0 0 10.2 10.2z"/>',
    "anterior": '<path d="m6 15 6-6 6 6"/>',
    "siguiente": '<path d="m6 9 6 6 6-6"/>',
    "cerrar": '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
    "recargar": '<path d="M20 11.5A8 8 0 1 0 17.7 17"/><path d="M20 5.5v6h-6"/>',
}


def _pixmaps(nombre: str, color: str, tam: int):
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        f"{TRAZOS[nombre]}</svg>"
    )
    render = QSvgRenderer(QByteArray(svg.encode()))
    for escala in (1, 2):
        px = QPixmap(tam * escala, tam * escala)
        px.fill(Qt.GlobalColor.transparent)
        px.setDevicePixelRatio(escala)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        render.render(p, QRectF(0, 0, tam, tam))
        p.end()
        yield px


def icono(nombre: str, color: str, activo: str | None = None, tam: int = 20) -> QIcon:
    """Genera un QIcon nítido (a 1x y 2x) del color indicado.

    `activo` es el color para el estado marcado de los botones conmutables.
    """
    ico = QIcon()
    for px in _pixmaps(nombre, color, tam):
        ico.addPixmap(px, QIcon.Mode.Normal, QIcon.State.Off)
    for px in _pixmaps(nombre, activo or color, tam):
        ico.addPixmap(px, QIcon.Mode.Normal, QIcon.State.On)
    return ico
