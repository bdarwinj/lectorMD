# lectorMD

Visor de archivos Markdown para Windows y Linux, con exportación a **PDF** y
**Word (.docx)**.

El documento se maqueta con HTML y CSS dentro de Qt WebEngine, así que se ve
igual en los dos sistemas y el PDF es idéntico a lo que ves en pantalla.

## Qué hace

- **Maquetado completo**: tipografía cuidada, resaltado de sintaxis, tablas,
  citas, listas de tareas e imágenes. Tema claro/oscuro que sigue al sistema.
- **Índice lateral** generado desde los encabezados, que marca la sección
  donde estás.
- **Diagramas Mermaid** (` ```mermaid `) y **fórmulas LaTeX** (`$...$`, `$$...$$`).
- **Avisos tipo GitHub**: `> [!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, `[!WARNING]`, `[!CAUTION]`.
- **Exportar a PDF**: A4, con numeración de páginas; incluye diagramas y fórmulas.
- **Exportar a Word**: numeración real de listas, código con colores, tablas,
  diagramas como imagen y **fórmulas como ecuaciones nativas editables**.
- Búsqueda en el documento, zoom, dos tipografías y recarga automática si el
  archivo cambia en disco.
- Funciona sin conexión: Mermaid y KaTeX van incluidos.

## Descargas

| Sistema | Instalador | Portable |
|---|---|---|
| Windows 10/11 (64 bits) | `lectorMD-<versión>-windows-setup.exe` | `lectorMD-<versión>-windows-portable.zip` |
| Linux (x86-64) | `lectormd_<versión>_amd64.deb` | `lectorMD-<versión>-x86_64.AppImage` |

**Windows.** El instalador no pide permisos de administrador: se instala para
tu usuario, salvo que elijas "para todos los usuarios". Registra lectorMD en
«Abrir con» para los `.md`. Windows no permite que un instalador se imponga
como aplicación predeterminada, así que para eso: clic derecho en un `.md` →
Abrir con → Elegir otra aplicación → lectorMD → «Usar siempre». La versión
portable se descomprime y se ejecuta `lectorMD.exe`, sin instalar nada.

**Linux.** El `.deb` sirve para Debian, Ubuntu, Mint, Zorin y derivadas:

```bash
sudo apt install ./lectormd_2.0.0_amd64.deb
```

El AppImage funciona en cualquier distribución sin instalar:

```bash
chmod +x lectorMD-2.0.0-x86_64.AppImage && ./lectorMD-2.0.0-x86_64.AppImage
```

## Uso

Abre un `.md` con doble clic, arrástralo a la ventana o pulsa `Ctrl`+`O`.
Para exportar, usa el botón **Exportar** de la barra superior.

| Tecla | Acción |
|-------|--------|
| `Ctrl` + `O` | Abrir documento |
| `Ctrl` + `P` | Exportar a PDF |
| `Ctrl` + `Mayús` + `E` | Exportar a Word |
| `Ctrl` + `F`, `F3`, `Mayús` + `F3` | Buscar, siguiente, anterior |
| `Ctrl` + `R` / `F5` | Recargar |
| `F9` | Mostrar u ocultar el índice |
| `Ctrl` + `+` / `-` / `0` | Zoom |
| `Ctrl` + `W` / `Ctrl` + `Q` | Cerrar ventana / salir |

### Exportar desde la terminal

Sin abrir ventana, útil para scripts y conversiones en lote:

```bash
lectormd informe.md --pdf informe.pdf --docx informe.docx
```

Devuelve código 0 si todo fue bien y 1 si alguna exportación falló.

## Desarrollo

Requiere Python 3.12.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m lectormd DEMO.md
```

En Linux, Qt 6.5+ necesita la biblioteca `libxcb-cursor0`
(`sudo apt install libxcb-cursor0`).

## Generar los ejecutables

PyInstaller no hace compilación cruzada: los ejecutables de Windows se
compilan en Windows y los de Linux en Linux. Hay tres caminos.

**1. GitHub Actions (recomendado).** El workflow
`.github/workflows/build.yml` compila en máquinas Windows y Linux reales,
prueba cada ejecutable exportando `DEMO.md` y deja los cuatro archivos como
artefactos. Al subir una etiqueta de versión, además los publica en
GitHub Releases:

```bash
git tag v2.0.0 && git push origin v2.0.0
```

La etiqueta tiene que coincidir con `__version__` en `lectormd/__init__.py`;
si no, el workflow se detiene.

**2. Linux, en local.** Genera el `.deb` y el AppImage en `dist/paquetes/`:

```bash
.venv/bin/pip install -r requirements-build.txt
PYTHON=.venv/bin/python bash packaging/linux/build.sh
```

Para poner tu nombre en el paquete: `MANTENEDOR="Nombre <correo>"`.

**3. Windows, en local.** Con Python 3.12 e
[Inno Setup 6](https://jrsoftware.org/isinfo.php) instalados
(`winget install Python.Python.3.12 JRSoftware.InnoSetup`):

```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1
```

Sin Inno Setup genera solo la versión portable.

## Estructura

```
lectormd/
  app.py          ventana Qt, barra de herramientas, exportación, modo terminal
  renderer.py     Markdown → HTML (markdown-it-py + Pygments)
  exportar.py     Markdown → Word (python-docx, ecuaciones OMML)
  iconos.py       iconos de la barra, recoloreados según el tema
  assets/         shell.html, style.css, app.js y Mermaid/KaTeX
packaging/
  lectormd.spec   receta de PyInstaller (con poda de módulos Qt sin uso)
  linux/          build.sh, .desktop y copyright del .deb
  windows/        build.ps1 e instalador de Inno Setup
  iconos/         icono en SVG, PNG e ICO (generar_iconos.py los regenera)
.github/workflows/build.yml
```

Los colores están al principio de `lectormd/assets/style.css`, en
`body[data-tema="claro"]` y `body[data-tema="oscuro"]`, y se repiten en
`PALETAS` de `app.py` para la barra de herramientas.

## Seguridad

Un `.md` puede llevar HTML incrustado. El visor aplica una política de
seguridad de contenido (CSP) que solo permite los scripts propios del
programa: el HTML de un documento no puede ejecutar JavaScript ni hacer
peticiones de red. Los enlaces web se abren en tu navegador.

## Licencia

MIT. Los ejecutables incluyen componentes de terceros —entre ellos Qt bajo
LGPLv3—, detallados en `packaging/TERCEROS.md`.
