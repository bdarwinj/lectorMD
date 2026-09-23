"""Punto de entrada del ejecutable (PyInstaller necesita un script)."""

import sys

from lectormd.app import main

sys.exit(main())
