"""Ventana principal de lectorMD (Qt / PySide6).

La interfaz es Qt (barra de herramientas, diálogos) y el documento se maqueta
con HTML y CSS dentro de un QWebEngineView, igual en Windows y Linux.

Uso:  lectormd [archivo.md ...]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from pathlib import Path
from urllib.parse import unquote

from lectormd import NOMBRE, __version__


def _preparar_entorno() -> None:
    """Ajustes que deben hacerse antes de arrancar Qt WebEngine."""
    # Ubuntu 24.04+ restringe los "user namespaces" sin privilegios mediante
    # AppArmor, y el sandbox de Chromium depende de ellos: sin este ajuste el
    # motor web no arranca. El contenido es local y una CSP estricta impide
    # ejecutar scripts del documento, así que el riesgo es acotado.
    try:
        restr = Path("/proc/sys/kernel/apparmor_restrict_unprivileged_userns")
        if restr.read_text().strip() == "1":
            os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
    except OSError:
        pass


_preparar_entorno()

# QtWebEngineWidgets debe importarse antes de crear la QApplication.
from PySide6.QtCore import QEvent, QMarginsF, QObject, QSize, Qt, QTimer, QUrl, Signal  # noqa: E402
from PySide6.QtCore import QFileSystemWatcher  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QAction,
    QActionGroup,
    QColor,
    QDesktopServices,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QIcon,
    QKeySequence,
    QPageLayout,
    QPageSize,
)
from PySide6.QtWebEngineCore import (  # noqa: E402
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
)
from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSizePolicy,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from lectormd import exportar, renderer, rutas  # noqa: E402
from lectormd.iconos import icono  # noqa: E402

EXTENSIONES = (".md", ".markdown", ".mdown", ".mkd", ".mkdn")
FILTRO_MD = "Markdown (*.md *.markdown *.mdown *.mkd *.mkdn);;Todos los archivos (*)"
DEPURAR = bool(os.environ.get("LECTORMD_DEBUG"))

# Los mismos colores que las variables de style.css, para que la barra de
# herramientas y el documento se vean como una sola pieza.
PALETAS = {
    "claro": {
        "fondo": "#fbfaf8", "alt": "#ffffff", "sutil": "#f2f1ee", "texto": "#1d2126",
        "suave": "#5c6570", "tenue": "#8a929c", "borde": "#e2e0db",
        "acento": "#4a56c8", "acento_suave": "#eceefb",
    },
    "oscuro": {
        "fondo": "#15171c", "alt": "#1b1e25", "sutil": "#212530", "texto": "#e6e8ec",
        "suave": "#a4adba", "tenue": "#737d8b", "borde": "#2a2f39",
        "acento": "#8e9bf5", "acento_suave": "#232842",
    },
}

QSS = """
QMainWindow, QWidget#raiz {{ background: {fondo}; }}
QToolBar {{
    background: {alt}; border: 0; border-bottom: 1px solid {borde};
    padding: 5px 8px; spacing: 3px;
}}
QToolBar QToolButton {{
    background: transparent; color: {texto};
    border: 1px solid transparent; border-radius: 7px; padding: 5px;
}}
QToolBar QToolButton:hover {{ background: {sutil}; }}
QToolBar QToolButton:checked, QToolBar QToolButton:pressed {{
    background: {acento_suave}; color: {acento};
}}
QToolBar QToolButton:disabled {{ color: {tenue}; }}
QToolBar QToolButton::menu-indicator {{ image: none; width: 0; }}
QToolButton#exportar {{ padding: 5px 11px 5px 7px; font-weight: 600; }}
QLabel#titulo {{ color: {texto}; font-weight: 600; }}
QLabel#subtitulo {{ color: {tenue}; }}
QWidget#busqueda {{ background: {alt}; border-bottom: 1px solid {borde}; }}
QWidget#busqueda QToolButton {{
    background: transparent; border: 0; border-radius: 6px; padding: 4px;
}}
QWidget#busqueda QToolButton:hover {{ background: {sutil}; }}
QLabel#coincidencias {{ color: {tenue}; }}
QLineEdit {{
    background: {fondo}; color: {texto}; border: 1px solid {borde};
    border-radius: 7px; padding: 5px 9px;
    selection-background-color: {acento}; selection-color: {alt};
}}
QLineEdit:focus {{ border-color: {acento}; }}
QMenu {{
    background: {alt}; color: {texto}; border: 1px solid {borde};
    border-radius: 8px; padding: 5px;
}}
QMenu::item {{ padding: 6px 26px 6px 12px; border-radius: 5px; }}
QMenu::item:selected {{ background: {acento_suave}; color: {acento}; }}
QMenu::item:disabled {{ color: {tenue}; }}
QMenu::separator {{ height: 1px; background: {borde}; margin: 4px 8px; }}
QToolTip {{
    background: {texto}; color: {fondo}; border: 0;
    padding: 4px 8px; border-radius: 5px;
}}
"""

# src/href relativos: se reescriben a file:// para que carguen las imágenes.
_ABSOLUTAS = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//|#)", re.IGNORECASE)


def _absolutizar(htm: str, carpeta: Path) -> str:
    def arreglar(m: re.Match) -> str:
        attr, comilla, valor = m.group(1), m.group(2), m.group(3)
        if not valor or _ABSOLUTAS.match(valor):
            return m.group(0)
        destino = (carpeta / unquote(valor)).resolve()
        return f"{attr}={comilla}{QUrl.fromLocalFile(str(destino)).toString()}{comilla}"

    return re.sub(r'\b(src|href)=(["\'])([^"\']*)\2', arreglar, htm)


def _permisos_normales(ruta: Path) -> None:
    """Chromium crea el PDF con permisos 0600; se aplican los habituales."""
    if os.name != "posix":
        return
    mascara = os.umask(0)
    os.umask(mascara)
    try:
        os.chmod(ruta, 0o666 & ~mascara)
    except OSError:
        pass


# --------------------------------------------------------------------------
# Motor web
# --------------------------------------------------------------------------

class Pagina(QWebEnginePage):
    """Decide qué pasa con cada enlace del documento."""

    abrir_md = Signal(str)

    def __init__(self, perfil: QWebEngineProfile, shell: Path, padre=None):
        super().__init__(perfil, padre)
        self.shell = shell

    def acceptNavigationRequest(self, url: QUrl, tipo, principal: bool) -> bool:  # noqa: N802
        if url.scheme() in ("http", "https", "mailto"):
            QDesktopServices.openUrl(url)
            return False
        if url.isLocalFile():
            ruta = Path(url.toLocalFile())
            if ruta == self.shell:
                return True
            if ruta.suffix.lower() in EXTENSIONES:
                self.abrir_md.emit(str(ruta))
                return False
            # Otro archivo local (un PDF, una imagen…): lo abre el sistema.
            if tipo == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
                QDesktopServices.openUrl(url)
            return False
        return False

    def javaScriptConsoleMessage(self, nivel, mensaje, linea, fuente):  # noqa: N802
        if DEPURAR:
            print(f"[js:{linea}] {mensaje}", file=sys.stderr)


class Visor(QWebEngineView):
    """El WebView con menú contextual recortado y arrastrar y soltar propio."""

    soltado = Signal(str)

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setAcceptDrops(True)

    def contextMenuEvent(self, evento):  # noqa: N802
        menu = self.createStandardContextMenu()
        # Atrás, recargar, guardar página… romperían el visor.
        fuera = {
            QWebEnginePage.WebAction.Back, QWebEnginePage.WebAction.Forward,
            QWebEnginePage.WebAction.Reload, QWebEnginePage.WebAction.SavePage,
            QWebEnginePage.WebAction.ViewSource, QWebEnginePage.WebAction.OpenLinkInNewTab,
            QWebEnginePage.WebAction.OpenLinkInNewWindow,
            QWebEnginePage.WebAction.OpenLinkInThisWindow,
            QWebEnginePage.WebAction.DownloadLinkToDisk,
            QWebEnginePage.WebAction.DownloadImageToDisk,
        }
        if not DEPURAR:
            fuera.add(QWebEnginePage.WebAction.InspectElement)
        acciones_fuera = {self.page().action(a) for a in fuera}
        for accion in list(menu.actions()):
            if accion in acciones_fuera:
                menu.removeAction(accion)
        # Quita separadores duplicados que quedan al borrar entradas.
        previo_sep = True
        for accion in list(menu.actions()):
            if accion.isSeparator() and previo_sep:
                menu.removeAction(accion)
            previo_sep = accion.isSeparator()
        if menu.actions():
            menu.exec(evento.globalPos())

    def _ruta_md(self, evento) -> str | None:
        if evento.mimeData().hasUrls():
            for url in evento.mimeData().urls():
                if url.isLocalFile():
                    return url.toLocalFile()
        return None

    def dragEnterEvent(self, evento):  # noqa: N802
        if self._ruta_md(evento):
            evento.acceptProposedAction()
        else:
            super().dragEnterEvent(evento)

    def dragMoveEvent(self, evento):  # noqa: N802
        if self._ruta_md(evento):
            evento.acceptProposedAction()
        else:
            super().dragMoveEvent(evento)

    def dropEvent(self, evento):  # noqa: N802
        ruta = self._ruta_md(evento)
        if ruta:
            evento.acceptProposedAction()
            self.soltado.emit(ruta)
        else:
            super().dropEvent(evento)


class _Senales(QObject):
    """Puente para avisar al hilo de la interfaz desde un hilo de trabajo."""

    docx_listo = Signal(str, str)  # ruta, error ("" si fue bien)


# --------------------------------------------------------------------------
# Ventana
# --------------------------------------------------------------------------

class Ventana(QMainWindow):
    def __init__(self, ruta: Path | None = None):
        super().__init__()
        self.ruta: Path | None = None
        self.texto = ""
        self.listo = False
        self.pendiente = ruta
        self.modo_tema = "auto"
        self.fuente = "sans"
        self.ocupado = False
        self.tras_exportar = None  # modo terminal: callable(ok, detalle)
        self.senales = _Senales()
        self.senales.docx_listo.connect(self._docx_listo)

        self.shell = rutas.assets() / "shell.html"
        self.setWindowTitle(NOMBRE)
        self.setWindowIcon(QIcon(str(rutas.assets() / "lectormd.svg")))
        self.resize(1140, 840)
        self.setMinimumSize(460, 360)

        self.vigilante = QFileSystemWatcher(self)
        self.vigilante.fileChanged.connect(self._archivo_cambio)
        self.recarga = QTimer(self, singleShot=True, interval=180)
        self.recarga.timeout.connect(lambda: self.recargar(conservar_scroll=True))

        self._construir()
        self._acciones()
        QGuiApplication.styleHints().colorSchemeChanged.connect(lambda *_: self._aplicar_tema())
        self._aplicar_tema()
        self.visor.load(QUrl.fromLocalFile(str(self.shell)))

    # ------------------------------------------------------------ interfaz
    def _construir(self) -> None:
        # --- motor web: perfil sin disco (ni caché ni cookies persistentes)
        self.perfil = QWebEngineProfile(self)
        self.pagina = Pagina(self.perfil, self.shell, self)
        ajustes = self.pagina.settings()
        ajustes.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        ajustes.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        ajustes.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        ajustes.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
        ajustes.setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, False)
        self.pagina.abrir_md.connect(lambda r: self.abrir(Path(r)))
        self.pagina.loadFinished.connect(self._shell_cargado)
        self.pagina.pdfPrintingFinished.connect(self._pdf_listo)
        self.pagina.findTextFinished.connect(self._resultado_busqueda)

        self.visor = Visor(self)
        self.visor.setPage(self.pagina)
        self.visor.soltado.connect(lambda r: self.abrir(Path(r)))

        # --- barra de herramientas
        barra = QToolBar(self)
        barra.setMovable(False)
        barra.setFloatable(False)
        barra.setIconSize(QSize(20, 20))
        barra.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.addToolBar(barra)
        self.barra = barra

        self.a_abrir = QAction("Abrir…", self, shortcut=QKeySequence.StandardKey.Open,
                               toolTip="Abrir documento  (Ctrl+O)")
        self.a_abrir.triggered.connect(self.elegir_archivo)
        barra.addAction(self.a_abrir)

        self.a_indice = QAction("Índice", self, checkable=True, checked=True,
                                shortcut=QKeySequence("F9"), toolTip="Mostrar u ocultar el índice  (F9)")
        self.a_indice.toggled.connect(lambda v: self._js(f"lector.indice({json.dumps(v)})"))
        barra.addAction(self.a_indice)

        # Título centrado: dos espaciadores elásticos a los lados.
        barra.addWidget(self._espaciador())
        caja_titulo = QWidget(barra)
        lt = QVBoxLayout(caja_titulo)
        lt.setContentsMargins(0, 0, 0, 0)
        lt.setSpacing(0)
        self.l_titulo = QLabel(NOMBRE, objectName="titulo", alignment=Qt.AlignmentFlag.AlignCenter)
        self.l_subtitulo = QLabel("ningún documento", objectName="subtitulo",
                                  alignment=Qt.AlignmentFlag.AlignCenter)
        fuente_sub = self.l_subtitulo.font()
        fuente_sub.setPointSizeF(max(7.5, fuente_sub.pointSizeF() - 1.5))
        self.l_subtitulo.setFont(fuente_sub)
        for etiqueta in (self.l_titulo, self.l_subtitulo):
            etiqueta.setMaximumWidth(620)
            etiqueta.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        lt.addWidget(self.l_titulo)
        lt.addWidget(self.l_subtitulo)
        barra.addWidget(caja_titulo)
        barra.addWidget(self._espaciador())

        self.a_buscar = QAction("Buscar", self, checkable=True, shortcut=QKeySequence.StandardKey.Find,
                                toolTip="Buscar en el documento  (Ctrl+F)")
        self.a_buscar.toggled.connect(self._mostrar_busqueda)
        barra.addAction(self.a_buscar)

        # Exportar: botón con texto y menú desplegable.
        self.a_pdf = QAction("Exportar a PDF…", self, shortcut=QKeySequence("Ctrl+P"))
        self.a_pdf.triggered.connect(lambda: self.exportar_pdf())
        self.a_docx = QAction("Exportar a Word (.docx)…", self, shortcut=QKeySequence("Ctrl+Shift+E"))
        self.a_docx.triggered.connect(lambda: self.exportar_docx())
        menu_exp = QMenu(self)
        menu_exp.addAction(self.a_pdf)
        menu_exp.addAction(self.a_docx)
        self.b_exportar = QToolButton(self, objectName="exportar", text="Exportar",
                                      toolTip="Exportar a PDF o Word",
                                      popupMode=QToolButton.ToolButtonPopupMode.InstantPopup,
                                      toolButtonStyle=Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.b_exportar.setMenu(menu_exp)
        barra.addWidget(self.b_exportar)

        self.b_menu = QToolButton(self, toolTip="Menú",
                                  popupMode=QToolButton.ToolButtonPopupMode.InstantPopup)
        self.b_menu.setMenu(self._menu_principal())
        barra.addWidget(self.b_menu)

        # --- barra de búsqueda (oculta hasta Ctrl+F)
        self.busqueda = QWidget(self, objectName="busqueda")
        lb = QHBoxLayout(self.busqueda)
        lb.setContentsMargins(12, 6, 10, 6)
        lb.setSpacing(4)
        self.e_buscar = QLineEdit(placeholderText="Buscar en el documento", clearButtonEnabled=True)
        self.e_buscar.setMaximumWidth(360)
        self.e_buscar.textChanged.connect(lambda _: self._buscar())
        self.e_buscar.returnPressed.connect(lambda: self._buscar())
        self.l_coincidencias = QLabel("", objectName="coincidencias")
        self.b_anterior = QToolButton(self, toolTip="Anterior  (Mayús+F3)")
        self.b_anterior.clicked.connect(lambda: self._buscar(atras=True))
        self.b_siguiente = QToolButton(self, toolTip="Siguiente  (F3)")
        self.b_siguiente.clicked.connect(lambda: self._buscar())
        self.b_cerrar_busqueda = QToolButton(self, toolTip="Cerrar  (Esc)")
        self.b_cerrar_busqueda.clicked.connect(lambda: self.a_buscar.setChecked(False))
        lb.addWidget(self.e_buscar)
        lb.addWidget(self.l_coincidencias)
        lb.addWidget(self.b_anterior)
        lb.addWidget(self.b_siguiente)
        lb.addStretch(1)
        lb.addWidget(self.b_cerrar_busqueda)
        self.busqueda.hide()

        raiz = QWidget(self, objectName="raiz")
        lr = QVBoxLayout(raiz)
        lr.setContentsMargins(0, 0, 0, 0)
        lr.setSpacing(0)
        lr.addWidget(self.busqueda)
        lr.addWidget(self.visor, 1)
        self.setCentralWidget(raiz)
        self._habilitar_documento(False)

    @staticmethod
    def _espaciador() -> QWidget:
        w = QWidget()
        w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        return w

    def _menu_principal(self) -> QMenu:
        menu = QMenu(self)

        grupo_tema = QActionGroup(self)
        self.acciones_tema = {}
        for clave, texto in (("auto", "Tema del sistema"), ("claro", "Tema claro"), ("oscuro", "Tema oscuro")):
            a = QAction(texto, self, checkable=True, checked=(clave == "auto"))
            a.triggered.connect(lambda _=False, c=clave: self._set_tema(c))
            grupo_tema.addAction(a)
            menu.addAction(a)
            self.acciones_tema[clave] = a
        menu.addSeparator()

        grupo_fuente = QActionGroup(self)
        for clave, texto in (("sans", "Tipografía sans"), ("serif", "Tipografía serif")):
            a = QAction(texto, self, checkable=True, checked=(clave == "sans"))
            a.triggered.connect(lambda _=False, c=clave: self._set_fuente(c))
            grupo_fuente.addAction(a)
            menu.addAction(a)
        menu.addSeparator()

        for texto, atajos, factor in (
            ("Acercar", [QKeySequence.StandardKey.ZoomIn, QKeySequence("Ctrl+=")], 0.1),
            ("Alejar", [QKeySequence.StandardKey.ZoomOut], -0.1),
            ("Tamaño normal", [QKeySequence("Ctrl+0")], 0),
        ):
            a = QAction(texto, self)
            a.setShortcuts(atajos)
            a.triggered.connect(lambda _=False, f=factor: self._zoom(f))
            menu.addAction(a)
            self.addAction(a)
        menu.addSeparator()

        self.a_recargar = QAction("Recargar", self, shortcuts=[QKeySequence("Ctrl+R"), QKeySequence("F5")])
        self.a_recargar.triggered.connect(lambda: self.recargar())
        menu.addAction(self.a_recargar)
        a_acerca = QAction(f"Acerca de {NOMBRE}", self)
        a_acerca.triggered.connect(self._acerca)
        menu.addAction(a_acerca)
        menu.addSeparator()
        a_salir = QAction("Salir", self, shortcut=QKeySequence.StandardKey.Quit)
        a_salir.triggered.connect(QApplication.instance().quit)
        menu.addAction(a_salir)
        return menu

    def _acciones(self) -> None:
        """Atajos que no tienen botón visible."""
        for atajo, funcion in (
            ("Ctrl+W", self.close),
            ("F3", lambda: self._buscar_desde_atajo(False)),
            ("Shift+F3", lambda: self._buscar_desde_atajo(True)),
            ("Escape", lambda: self.a_buscar.setChecked(False)),
        ):
            a = QAction(self, shortcut=QKeySequence(atajo))
            a.triggered.connect(funcion)
            self.addAction(a)
        for a in (self.a_pdf, self.a_docx, self.a_recargar):
            self.addAction(a)

    def _habilitar_documento(self, si: bool) -> None:
        for w in (self.a_pdf, self.a_docx, self.a_buscar, self.a_recargar, self.b_exportar):
            w.setEnabled(si and not self.ocupado)

    # --------------------------------------------------------------- tema
    def _tema_efectivo(self) -> str:
        if self.modo_tema != "auto":
            return self.modo_tema
        esquema = QGuiApplication.styleHints().colorScheme()
        return "oscuro" if esquema == Qt.ColorScheme.Dark else "claro"

    def _aplicar_tema(self) -> None:
        tema = self._tema_efectivo()
        c = PALETAS[tema]
        self.setStyleSheet(QSS.format(**c))
        # El fondo del WebView antes de pintar evita un destello blanco.
        self.pagina.setBackgroundColor(c["fondo"])
        pintar = lambda n: icono(n, c["suave"], c["acento"])  # noqa: E731
        self.a_abrir.setIcon(pintar("abrir"))
        self.a_indice.setIcon(pintar("indice"))
        self.a_buscar.setIcon(pintar("buscar"))
        self.b_exportar.setIcon(pintar("exportar"))
        self.b_menu.setIcon(pintar("menu"))
        self.a_pdf.setIcon(pintar("pdf"))
        self.a_docx.setIcon(pintar("word"))
        self.b_anterior.setIcon(pintar("anterior"))
        self.b_siguiente.setIcon(pintar("siguiente"))
        self.b_cerrar_busqueda.setIcon(pintar("cerrar"))
        self._js(f"lector.tema({json.dumps(tema)})")

    def _set_tema(self, modo: str) -> None:
        self.modo_tema = modo
        self._aplicar_tema()

    def _set_fuente(self, cual: str) -> None:
        self.fuente = cual
        self._js(f"lector.fuente({json.dumps(cual)})")

    def _zoom(self, delta: float) -> None:
        z = 1.0 if delta == 0 else min(3.0, max(0.4, self.visor.zoomFactor() + delta))
        self.visor.setZoomFactor(z)

    # ------------------------------------------------------------ carga web
    def _js(self, codigo: str, cb=None) -> None:
        if not self.listo:
            return
        if cb is None:
            self.pagina.runJavaScript(codigo, 0)
        else:
            self.pagina.runJavaScript(codigo, 0, cb)

    def _shell_cargado(self, ok: bool) -> None:
        if not ok or self.listo:
            return
        self.listo = True
        self._js(f"lector.estilos({json.dumps(renderer.css_resaltado())})")
        self._js(f"lector.fuente({json.dumps(self.fuente)})")
        self._aplicar_tema()
        if self.pendiente:
            ruta, self.pendiente = self.pendiente, None
            self.abrir(ruta)

    # ---------------------------------------------------------- documento
    def abrir(self, ruta: Path, conservar_scroll: bool = False) -> None:
        ruta = Path(ruta).expanduser()
        if not self.listo:
            self.pendiente = ruta
            return
        try:
            texto = ruta.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            QMessageBox.warning(self, "No se pudo abrir", f"{ruta}\n\n{e.strerror or e}")
            return

        doc = renderer.renderizar(texto)
        titulo = doc.titulo or ruta.stem
        cambio_archivo = ruta != self.ruta
        self.ruta, self.texto = ruta.resolve(), texto

        datos = {
            "cuerpo": _absolutizar(doc.cuerpo, self.ruta.parent),
            "indice": doc.indice,
            "meta": {k: str(v) for k, v in doc.meta.items()},
            "titulo": titulo,
            "palabras": doc.palabras,
            "minutos": doc.minutos,
            "conservarScroll": conservar_scroll and not cambio_archivo,
        }
        self._js(f"lector.cargar({json.dumps(datos)})")

        self.l_titulo.setText(self._recortar(titulo, 70))
        carpeta = str(self.ruta.parent)
        casa = str(Path.home())
        if carpeta.startswith(casa):
            carpeta = "~" + carpeta[len(casa):]
        self.l_subtitulo.setText(self._recortar(carpeta, 90, izquierda=True))
        self.l_subtitulo.setToolTip(str(self.ruta))
        self.setWindowTitle(f"{titulo} — {NOMBRE}")
        self.a_indice.setEnabled(len(doc.indice) > 1)
        self._habilitar_documento(True)
        self._vigilar(self.ruta)

    @staticmethod
    def _recortar(texto: str, maximo: int, izquierda: bool = False) -> str:
        if len(texto) <= maximo:
            return texto
        return "…" + texto[-(maximo - 1):] if izquierda else texto[: maximo - 1] + "…"

    def recargar(self, conservar_scroll: bool = False) -> None:
        if self.ruta:
            self.abrir(self.ruta, conservar_scroll=conservar_scroll)

    def _vigilar(self, ruta: Path) -> None:
        """Recarga sola si el archivo cambia en disco mientras lo lees."""
        viejos = self.vigilante.files()
        if viejos:
            self.vigilante.removePaths(viejos)
        self.vigilante.addPath(str(ruta))

    def _archivo_cambio(self, ruta: str) -> None:
        # Muchos editores guardan borrando y recreando el archivo, lo que
        # hace que el vigilante lo suelte: se vuelve a añadir.
        if Path(ruta).exists() and ruta not in self.vigilante.files():
            self.vigilante.addPath(ruta)
        self.recarga.start()

    def elegir_archivo(self) -> None:
        inicio = str(self.ruta.parent) if self.ruta else str(Path.home())
        ruta, _ = QFileDialog.getOpenFileName(self, "Abrir documento", inicio, FILTRO_MD)
        if ruta:
            self.abrir(Path(ruta))

    # ------------------------------------------------------------ búsqueda
    def _mostrar_busqueda(self, visible: bool) -> None:
        self.busqueda.setVisible(visible)
        if visible:
            self.e_buscar.setFocus()
            self.e_buscar.selectAll()
        else:
            self.pagina.findText("")
            self.l_coincidencias.setText("")
            self.visor.setFocus()

    def _buscar_desde_atajo(self, atras: bool) -> None:
        if not self.a_buscar.isChecked():
            self.a_buscar.setChecked(True)
            return
        self._buscar(atras)

    def _buscar(self, atras: bool = False) -> None:
        texto = self.e_buscar.text()
        banderas = QWebEnginePage.FindFlag.FindBackward if atras else QWebEnginePage.FindFlag(0)
        self.pagina.findText(texto, banderas)
        if not texto:
            self.l_coincidencias.setText("")

    def _resultado_busqueda(self, resultado) -> None:
        total = resultado.numberOfMatches()
        if not self.e_buscar.text():
            self.l_coincidencias.setText("")
        elif total:
            self.l_coincidencias.setText(f"{resultado.activeMatch()} de {total}")
        else:
            self.l_coincidencias.setText("sin resultados")

    # ---------------------------------------------------------- exportación
    def _avisar(self, texto: str, tipo: str = "ok") -> None:
        self._js(f"lector.avisar({json.dumps(texto)}, {json.dumps(tipo)})")

    def _set_ocupado(self, si: bool) -> None:
        self.ocupado = si
        if si:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()
        self._habilitar_documento(self.ruta is not None)

    def _pedir_destino(self, titulo: str, extension: str, filtro: str) -> Path | None:
        sugerido = str(self.ruta.with_suffix(extension))
        destino, _ = QFileDialog.getSaveFileName(self, titulo, sugerido, filtro)
        if not destino:
            return None
        if not destino.lower().endswith(extension):
            destino += extension
        return Path(destino)

    def _esperar(self, expresion: str, luego, limite: float, fallo) -> None:
        """Sondea una expresión JS hasta que sea verdadera o venza el plazo."""
        inicio = time.monotonic()

        def sondear():
            def respuesta(valor):
                if valor:
                    luego()
                elif time.monotonic() - inicio > limite:
                    fallo()
                else:
                    QTimer.singleShot(60, sondear)

            self.pagina.runJavaScript(expresion, 0, respuesta)

        sondear()

    def _fallo_exportacion(self, detalle: str) -> None:
        self._js("lector.restaurar()")
        self._set_ocupado(False)
        self._avisar(f"No se pudo exportar: {detalle}", "error")
        if self.tras_exportar:
            self.tras_exportar(False, detalle)

    def exportar_pdf(self, destino: Path | None = None) -> None:
        if not self.ruta or self.ocupado:
            return
        if destino is None:
            destino = self._pedir_destino("Exportar a PDF", ".pdf", "PDF (*.pdf)")
        if not destino:
            return
        self._set_ocupado(True)
        self._js("lector.prepararExportacion({svg: false})")
        self._esperar("window.__exportListo === true", lambda: self._imprimir(destino), 20,
                      lambda: self._fallo_exportacion("el documento tardó demasiado en prepararse"))

    def _imprimir(self, destino: Path) -> None:
        # El color de fondo del motor web se cuela en los márgenes del PDF.
        self.pagina.setBackgroundColor(QColor("white"))
        pagina = QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait,
                             QMarginsF(16, 16, 16, 18), QPageLayout.Unit.Millimeter)
        self.pagina.printToPdf(str(destino), pagina)

    def _pdf_listo(self, ruta: str, ok: bool) -> None:
        self._js("lector.restaurar()")
        self.pagina.setBackgroundColor(QColor(PALETAS[self._tema_efectivo()]["fondo"]))
        self._set_ocupado(False)
        if ok:
            _permisos_normales(Path(ruta))
            self._avisar(f"PDF guardado · {Path(ruta).name}")
        else:
            self._avisar("No se pudo escribir el PDF", "error")
        if self.tras_exportar:
            self.tras_exportar(ok, ruta)

    def exportar_docx(self, destino: Path | None = None) -> None:
        if not self.ruta or self.ocupado:
            return
        if destino is None:
            destino = self._pedir_destino("Exportar a Word", ".docx", "Documento de Word (*.docx)")
        if not destino:
            return
        self._set_ocupado(True)
        self._avisar("Exportando a Word…")
        # Word no entiende Mermaid: los diagramas se repintan en tema claro con
        # etiquetas SVG puras y se pasan a PNG antes de construir el .docx.
        self._js("lector.prepararExportacion({svg: true})")
        self._esperar("window.__exportListo === true", lambda: self._capturar(destino), 20,
                      lambda: self._fallo_exportacion("el documento tardó demasiado en prepararse"))

    def _capturar(self, destino: Path) -> None:
        self._js("lector.capturarDiagramas()")
        self._esperar(
            "window.__diagramas !== null && window.__diagramas !== undefined",
            lambda: self.pagina.runJavaScript("window.__diagramas", 0,
                                              lambda js: self._construir_docx(destino, js)),
            30,
            lambda: self._fallo_exportacion("los diagramas tardaron demasiado"),
        )

    def _construir_docx(self, destino: Path, js: str | None) -> None:
        self._js("lector.restaurar()")
        try:
            diagramas = json.loads(js) if js else []
        except (TypeError, ValueError):
            diagramas = []
        texto, carpeta = self.texto, self.ruta.parent

        # python-docx puede tardar (imágenes remotas): fuera del hilo de la UI.
        def trabajo():
            try:
                exportar.exportar_docx(texto, destino, carpeta, diagramas)
                self.senales.docx_listo.emit(str(destino), "")
            except Exception as e:  # noqa: BLE001 — se informa al usuario
                self.senales.docx_listo.emit(str(destino), f"{type(e).__name__}: {e}")

        threading.Thread(target=trabajo, daemon=True).start()

    def _docx_listo(self, ruta: str, error: str) -> None:
        self._set_ocupado(False)
        if self.tras_exportar:
            self.tras_exportar(not error, error or ruta)
            return
        if error:
            self._avisar("No se pudo exportar a Word", "error")
            QMessageBox.warning(self, "Error al exportar", error)
        else:
            self._avisar(f"Word guardado · {Path(ruta).name}")

    # -------------------------------------------------------------- varios
    def _acerca(self) -> None:
        QMessageBox.about(
            self,
            f"Acerca de {NOMBRE}",
            f"<h3>{NOMBRE} {__version__}</h3>"
            "<p>Visor de Markdown con exportación a PDF y Word.</p>"
            "<p style='color:gray'>Construido con Qt (PySide6, LGPLv3), markdown-it-py, "
            "Pygments, python-docx, Mermaid y KaTeX.</p>",
        )

    def closeEvent(self, evento):  # noqa: N802
        # El perfil debe morir después de la página o Qt avisa en la consola.
        self.visor.setPage(None)
        self.pagina.deleteLater()
        super().closeEvent(evento)


# --------------------------------------------------------------------------
# Arranque
# --------------------------------------------------------------------------

def _fuente_interfaz(app: QApplication) -> None:
    familias = set(QFontDatabase.families())
    for candidata in ("Inter", "Segoe UI Variable Text", "Segoe UI", "Cantarell", "Noto Sans"):
        if candidata in familias:
            f = QFont(candidata)
            f.setPointSizeF(app.font().pointSizeF())
            app.setFont(f)
            return


def _argumentos(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    p = argparse.ArgumentParser(
        prog="lectormd",
        description="Visor de Markdown con exportación a PDF y Word.",
        epilog="Ejemplo:  lectormd informe.md --pdf informe.pdf --docx informe.docx",
    )
    p.add_argument("archivos", nargs="*", type=Path, help="documentos .md que abrir")
    p.add_argument("--pdf", type=Path, metavar="SALIDA", help="exportar a PDF sin abrir la ventana")
    p.add_argument("--docx", type=Path, metavar="SALIDA", help="exportar a Word sin abrir la ventana")
    p.add_argument("-v", "--version", action="version", version=f"{NOMBRE} {__version__}")
    # Lo que no reconozca (p. ej. -platform de Qt) se le pasa a Qt.
    return p.parse_known_args(argv[1:])


def _exportar_por_terminal(entrada: Path, pdf: Path | None, docx: Path | None) -> int:
    """Exporta sin mostrar ventana: útil para scripts y conversiones en lote."""
    pendientes = [(t, d.resolve()) for t, d in (("pdf", pdf), ("docx", docx)) if d]
    v = Ventana(entrada)
    codigo = {"valor": 0}

    def siguiente():
        if not pendientes:
            QApplication.instance().exit(codigo["valor"])
            return
        tipo, destino = pendientes.pop(0)
        (v.exportar_pdf if tipo == "pdf" else v.exportar_docx)(destino)

    def terminado(ok: bool, detalle: str):
        print(f"{'✓' if ok else '✗'} {detalle}", file=sys.stdout if ok else sys.stderr, flush=True)
        if not ok:
            codigo["valor"] = 1
        QTimer.singleShot(0, siguiente)

    v.tras_exportar = terminado
    # En la plataforma offscreen "mostrar" no abre nada en pantalla, pero hace
    # que Chromium maquete y pinte la página como si estuviera visible.
    if QGuiApplication.platformName() == "offscreen":
        v.show()
    arranque = time.monotonic()

    def esperar_documento():
        def respuesta(listo):
            if listo:
                siguiente()
            elif time.monotonic() - arranque > 60:
                print("✗ el documento no terminó de cargar", file=sys.stderr)
                QApplication.instance().exit(1)
            else:
                QTimer.singleShot(100, esperar_documento)

        if v.listo:
            v.pagina.runJavaScript("window.__docCargado === true", 0, respuesta)
        else:
            QTimer.singleShot(100, esperar_documento)

    # Un error dentro de una llamada de Qt no detiene el bucle de eventos: sin
    # esto el proceso quedaría colgado en vez de fallar.
    def error_inesperado(tipo, valor, traza):
        sys.__excepthook__(tipo, valor, traza)
        codigo["valor"] = 1
        QApplication.instance().exit(1)

    sys.excepthook = error_inesperado
    QTimer.singleShot(100, esperar_documento)
    resultado = QApplication.instance().exec()

    # La página debe destruirse antes que su perfil; si no, Qt WebEngine puede
    # caerse al cerrar y el código de salida deja de ser fiable.
    v.visor.setPage(None)
    v.pagina.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    return resultado or codigo["valor"]


def _consola_segura() -> None:
    """Evita que un carácter que la consola no admite (p. ej. ✓ en la cp1252
    de Windows) haga fallar la exportación: se sustituye por '?'."""
    for flujo in (sys.stdout, sys.stderr):
        if flujo is not None and hasattr(flujo, "reconfigure"):
            flujo.reconfigure(errors="replace")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    args, resto_qt = _argumentos(argv)
    por_terminal = bool(args.pdf or args.docx)

    if por_terminal:
        _consola_segura()
        if len(args.archivos) != 1:
            print("Para exportar indica exactamente un documento .md", file=sys.stderr)
            return 2
        if not args.archivos[0].is_file():
            print(f"No existe: {args.archivos[0]}", file=sys.stderr)
            return 2
        # Sin ventana: plataforma offscreen y sin GPU, que en ese modo falla.
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        banderas = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
        if "--disable-gpu" not in banderas:
            os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = f"{banderas} --disable-gpu".strip()

    app = QApplication([argv[0], *resto_qt])
    app.setApplicationName(NOMBRE)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(NOMBRE)
    app.setDesktopFileName("lectormd")
    app.setStyle("Fusion")
    _fuente_interfaz(app)

    if por_terminal:
        return _exportar_por_terminal(args.archivos[0], args.pdf, args.docx)

    ventanas = [Ventana(r) for r in args.archivos] or [Ventana()]
    for v in ventanas:
        v.show()
    app._ventanas = ventanas  # que el recolector no las cierre
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
