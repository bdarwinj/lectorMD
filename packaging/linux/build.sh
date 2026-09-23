#!/usr/bin/env bash
# Genera los paquetes de Linux de lectorMD:
#   dist/paquetes/lectormd_<versión>_amd64.deb          instalador (Debian, Ubuntu, Mint, Zorin…)
#   dist/paquetes/lectorMD-<versión>-x86_64.AppImage     portable (cualquier distribución)
#
# Uso, desde la carpeta del proyecto y con las dependencias instaladas
# (pip install -r requirements-build.txt):
#   bash packaging/linux/build.sh
#
# Variables opcionales:
#   PYTHON=...       intérprete a usar (por defecto: python3)
#   SIN_COMPILAR=1   reutiliza dist/lectormd sin volver a pasar por PyInstaller
#   MANTENEDOR=...   campo Maintainer del .deb, p. ej. "Nombre <correo@dominio>"
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$RAIZ"

PY="${PYTHON:-python3}"
VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' lectormd/__init__.py)"
ARCH_DEB="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
ARCH_AI="$(uname -m)"
MANTENEDOR="${MANTENEDOR:-lectorMD <lectormd@users.noreply.invalid>}"
BUNDLE="dist/lectormd"
SALIDA="dist/paquetes"
TRABAJO="build/paquetes"
HERRAMIENTAS="build/herramientas"

echo "==> lectorMD $VERSION ($ARCH_DEB)"

# 1. Ejecutable ---------------------------------------------------------------
if [ -z "${SIN_COMPILAR:-}" ]; then
  "$PY" -m PyInstaller packaging/lectormd.spec --noconfirm --clean \
    --distpath dist --workpath build/pyinstaller
fi
[ -x "$BUNDLE/lectormd" ] || { echo "No existe $BUNDLE/lectormd" >&2; exit 1; }
cp packaging/TERCEROS.md "$BUNDLE/TERCEROS.txt"

# El plugin xcb de Qt ≥ 6.5 necesita libxcb-cursor, que muchas distribuciones
# no traen instalada. Si PyInstaller no la encontró al compilar, se avisa.
if ! find "$BUNDLE/_internal" -name 'libxcb-cursor.so.0' | grep -q .; then
  echo "AVISO: libxcb-cursor.so.0 no quedó incluida; instala libxcb-cursor0 y recompila." >&2
fi

rm -rf "$TRABAJO"
mkdir -p "$TRABAJO" "$SALIDA" "$HERRAMIENTAS"

instalar_recursos() {  # $1 = carpeta usr/ de destino
  local usr="$1"
  install -Dm644 packaging/linux/lectormd.desktop "$usr/share/applications/lectormd.desktop"
  install -Dm644 packaging/iconos/lectormd.svg "$usr/share/icons/hicolor/scalable/apps/lectormd.svg"
  for t in 16 24 32 48 64 128 256 512; do
    install -Dm644 "packaging/iconos/png/lectormd-$t.png" \
      "$usr/share/icons/hicolor/${t}x${t}/apps/lectormd.png"
  done
}

# 2. Paquete .deb -------------------------------------------------------------
DEB="$TRABAJO/deb"
mkdir -p "$DEB/DEBIAN" "$DEB/opt" "$DEB/usr/bin"
cp -a "$BUNDLE" "$DEB/opt/lectormd"
ln -s /opt/lectormd/lectormd "$DEB/usr/bin/lectormd"
instalar_recursos "$DEB/usr"
install -Dm644 packaging/linux/copyright "$DEB/usr/share/doc/lectormd/copyright"
install -Dm644 packaging/TERCEROS.md "$DEB/usr/share/doc/lectormd/TERCEROS.md"

# Bibliotecas del sistema que el ejecutable usa pero no incluye (calculadas
# con ldd sobre la compilación). Las básicas de cualquier escritorio (glibc,
# X11, GL, GLib, GTK) no se listan.
cat > "$DEB/DEBIAN/control" <<EOF
Package: lectormd
Version: $VERSION
Section: text
Priority: optional
Architecture: $ARCH_DEB
Maintainer: $MANTENEDOR
Installed-Size: $(du -sk "$DEB" | cut -f1)
Depends: libnss3, libxkbcommon-x11-0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0, libxcb-render-util0, libxcb-shape0, libxcb-xkb1, libxkbfile1, libgbm1, libegl1, libfontconfig1, libdbus-1-3, libxcomposite1, libxdamage1, libxrandr2, libxtst6, libasound2t64 | libasound2
Description: Visor de Markdown con exportación a PDF y Word
 Muestra archivos Markdown maquetados, con índice navegable, resaltado de
 código, diagramas Mermaid y fórmulas LaTeX, y los exporta a PDF o a
 documentos de Word (.docx) con ecuaciones editables.
EOF

cat > "$DEB/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null && update-desktop-database -q /usr/share/applications || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
exit 0
EOF
cp "$DEB/DEBIAN/postinst" "$DEB/DEBIAN/postrm"
chmod 755 "$DEB/DEBIAN/postinst" "$DEB/DEBIAN/postrm"

# La umask de quien compila (a menudo 002) no debe acabar en el sistema:
# directorios 755 y archivos 644, salvo los ejecutables.
chmod -R u+rwX,go+rX,go-w "$DEB"

ARCHIVO_DEB="$SALIDA/lectormd_${VERSION}_${ARCH_DEB}.deb"
dpkg-deb --root-owner-group -Zxz --build "$DEB" "$ARCHIVO_DEB" >/dev/null
echo "  instalador -> $ARCHIVO_DEB ($(du -h "$ARCHIVO_DEB" | cut -f1))"

# 3. AppImage -----------------------------------------------------------------
APPDIR="$TRABAJO/lectorMD.AppDir"
mkdir -p "$APPDIR/usr/lib"
cp -a "$BUNDLE" "$APPDIR/usr/lib/lectormd"
instalar_recursos "$APPDIR/usr"
cp packaging/linux/lectormd.desktop "$APPDIR/lectormd.desktop"
cp packaging/iconos/png/lectormd-256.png "$APPDIR/lectormd.png"
ln -s lectormd.png "$APPDIR/.DirIcon"
cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
AQUI="$(dirname "$(readlink -f "$0")")"
exec "$AQUI/usr/lib/lectormd/lectormd" "$@"
EOF
chmod 755 "$APPDIR/AppRun"

chmod -R u+rwX,go+rX,go-w "$APPDIR"

APPIMAGETOOL="$HERRAMIENTAS/appimagetool-$ARCH_AI.AppImage"
if [ ! -x "$APPIMAGETOOL" ]; then
  echo "  descargando appimagetool (herramienta oficial del proyecto AppImage)…"
  curl -fsSL -o "$APPIMAGETOOL" \
    "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH_AI.AppImage"
  chmod +x "$APPIMAGETOOL"
fi

ARCHIVO_AI="$SALIDA/lectorMD-${VERSION}-${ARCH_AI}.AppImage"
# APPIMAGE_EXTRACT_AND_RUN: la herramienta funciona aunque no haya FUSE.
ARCH="$ARCH_AI" APPIMAGE_EXTRACT_AND_RUN=1 "$APPIMAGETOOL" --no-appstream \
  "$APPDIR" "$ARCHIVO_AI" >/dev/null 2>"$TRABAJO/appimagetool.log" || {
  cat "$TRABAJO/appimagetool.log" >&2
  exit 1
}
echo "  portable   -> $ARCHIVO_AI ($(du -h "$ARCHIVO_AI" | cut -f1))"
