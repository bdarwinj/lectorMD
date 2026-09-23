"""Localiza los recursos tanto en desarrollo como dentro del ejecutable."""

from __future__ import annotations

import sys
from pathlib import Path


def base() -> Path:
    """Carpeta del paquete lectormd.

    PyInstaller descomprime todo en sys._MEIPASS; en desarrollo es la carpeta
    de este archivo.
    """
    congelado = getattr(sys, "_MEIPASS", None)
    if congelado:
        return Path(congelado) / "lectormd"
    return Path(__file__).resolve().parent


def assets() -> Path:
    return base() / "assets"
