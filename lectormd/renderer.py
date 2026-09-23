"""Conversión de Markdown a HTML para lectorMD.

Usa markdown-it-py (CommonMark + tablas + tachado) y le añade tres cosas que
no trae de fábrica: fórmulas con $...$, bloques ```mermaid y listas de tareas.
El resaltado de código lo pone Pygments.
"""

from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from markdown_it import MarkdownIt
from pygments import highlight as pyg_highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

# Temas de Pygments para cada modo. Se emiten los dos y el CSS elige.
ESTILO_CLARO = "friendly"
ESTILO_OSCURO = "github-dark"

# Avisos tipo GitHub: > [!NOTE], > [!WARNING], etc.
AVISOS = {
    "note": ("Nota", "info"),
    "tip": ("Consejo", "tip"),
    "important": ("Importante", "important"),
    "warning": ("Atención", "warning"),
    "caution": ("Cuidado", "caution"),
}


@dataclass
class Documento:
    """Resultado de renderizar un archivo .md."""

    cuerpo: str = ""
    indice: list[dict] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    titulo: str = ""
    palabras: int = 0
    minutos: int = 0
    tiene_mermaid: bool = False
    tiene_matematicas: bool = False


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------

def _slug(texto: str) -> str:
    """Convierte un encabezado en un id apto para URL, respetando acentos."""
    txt = unicodedata.normalize("NFKD", texto)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    txt = re.sub(r"[^\w\s-]", "", txt.lower())
    txt = re.sub(r"[\s_-]+", "-", txt).strip("-")
    return txt or "seccion"


def _separar_front_matter(texto: str) -> tuple[dict, str]:
    """Extrae el bloque YAML inicial delimitado por --- si existe."""
    if not texto.startswith("---"):
        return {}, texto
    fin = re.search(r"^---\s*$", texto[3:], re.MULTILINE)
    if not fin:
        return {}, texto
    crudo = texto[3 : 3 + fin.start()]
    resto = texto[3 + fin.end() :].lstrip("\n")
    try:
        datos = yaml.safe_load(crudo)
    except yaml.YAMLError:
        return {}, texto
    return (datos if isinstance(datos, dict) else {}), resto


# --------------------------------------------------------------------------
# Reglas propias de markdown-it
# --------------------------------------------------------------------------

def _math_inline(state, silent: bool) -> bool:
    """Reconoce $...$ y $$...$$ dentro de una línea."""
    src, pos = state.src, state.pos
    if src[pos] != "$":
        return False

    doble = src.startswith("$$", pos)
    marca = "$$" if doble else "$"
    inicio = pos + len(marca)
    if inicio >= len(src):
        return False
    # En $...$ el contenido no puede empezar por espacio: evita capturar "$ 5".
    if not doble and src[inicio] in " \t\n":
        return False

    i = inicio
    while True:
        cierre = src.find(marca, i)
        if cierre == -1:
            return False
        # Un $ escapado con \ no cuenta como cierre.
        barras = 0
        j = cierre - 1
        while j >= 0 and src[j] == "\\":
            barras += 1
            j -= 1
        if barras % 2 == 1:
            i = cierre + len(marca)
            continue
        break

    contenido = src[inicio:cierre]
    if not contenido.strip():
        return False
    if not doble and src[cierre - 1] in " \t\n":
        return False
    # "$20 y $30" no son fórmulas: si tras el cierre viene un dígito, se descarta.
    if not doble and cierre + 1 < len(src) and src[cierre + 1].isdigit():
        return False

    if not silent:
        token = state.push("math_inline", "", 0)
        token.content = contenido
        token.markup = marca
        token.meta = {"display": doble}

    state.pos = cierre + len(marca)
    return True


def _math_block(state, linea_ini: int, linea_fin: int, silent: bool) -> bool:
    """Reconoce bloques $$ ... $$ que ocupan líneas completas."""
    ini = state.bMarks[linea_ini] + state.tShift[linea_ini]
    tope = state.eMarks[linea_ini]
    if ini + 2 > tope or state.src[ini : ini + 2] != "$$":
        return False
    if silent:
        return True

    primera = state.src[ini + 2 : tope]
    lineas: list[str] = []
    cerrado = False

    if primera.strip().endswith("$$"):
        lineas.append(primera.strip()[:-2])
        cerrado = True
    elif primera.strip():
        lineas.append(primera)

    actual = linea_ini
    while not cerrado:
        actual += 1
        if actual >= linea_fin:
            break
        texto = state.src[state.bMarks[actual] : state.eMarks[actual]]
        if texto.strip().endswith("$$"):
            recorte = texto.strip()[:-2]
            if recorte:
                lineas.append(recorte)
            cerrado = True
            break
        lineas.append(texto)

    if not cerrado:
        return False

    state.line = actual + 1
    token = state.push("math_block", "", 0)
    token.block = True
    token.content = "\n".join(lineas).strip()
    token.markup = "$$"
    token.map = [linea_ini, state.line]
    return True


def _marcar_tareas(state) -> None:
    """Convierte '- [ ] texto' en casillas reales dentro de la lista."""
    tokens = state.tokens
    for i, tok in enumerate(tokens):
        if tok.type != "inline":
            continue
        if i < 2 or tokens[i - 1].type != "paragraph_open":
            continue
        if i < 3 or tokens[i - 2].type != "list_item_open":
            continue
        m = re.match(r"^\[([ xX])\]\s+", tok.content)
        if not m:
            continue

        marcada = m.group(1).lower() == "x"
        tok.content = tok.content[m.end() :]
        if tok.children:
            hijo = tok.children[0]
            if hijo.type == "text":
                hijo.content = re.sub(r"^\[([ xX])\]\s+", "", hijo.content)

        casilla = f'<input type="checkbox" disabled{" checked" if marcada else ""}> '
        marca = type(tok)("html_inline", "", 0)
        marca.content = casilla
        tok.children = [marca] + list(tok.children or [])

        tokens[i - 2].attrJoin("class", "tarea hecha" if marcada else "tarea")
        # La lista contenedora también se marca, para quitarle las viñetas.
        for j in range(i - 3, -1, -1):
            if tokens[j].type in ("bullet_list_open", "ordered_list_open"):
                tokens[j].attrJoin("class", "lista-tareas")
                break


def _resaltar(codigo: str, lenguaje: str, _attrs) -> str:
    """Resalta un bloque con Pygments y le añade cabecera con copiar."""
    lexer = None
    if lenguaje:
        try:
            lexer = get_lexer_by_name(lenguaje, stripall=False)
        except ClassNotFound:
            lexer = None
    if lexer is None:
        try:
            lexer = guess_lexer(codigo)
        except ClassNotFound:
            etiqueta = lenguaje or "texto"
            cuerpo = f"<pre><code>{html.escape(codigo)}</code></pre>"
            return _envolver_codigo(cuerpo, etiqueta, codigo)

    formateador = HtmlFormatter(nowrap=False, cssclass="hl")
    cuerpo = pyg_highlight(codigo, lexer, formateador)
    etiqueta = lenguaje or getattr(lexer, "name", "texto")
    return _envolver_codigo(cuerpo, etiqueta, codigo)


def _envolver_codigo(cuerpo: str, etiqueta: str, crudo: str) -> str:
    return (
        '<figure class="bloque-codigo">'
        f'<figcaption><span class="lenguaje">{html.escape(etiqueta)}</span>'
        f'<button class="copiar" type="button" data-codigo="{html.escape(crudo)}">Copiar</button>'
        "</figcaption>"
        f"{cuerpo}</figure>\n"
    )


# --------------------------------------------------------------------------
# Constructor del parser
# --------------------------------------------------------------------------

def _crear_parser() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": True, "typographer": True, "highlight": _resaltar})
    md.enable(["table", "strikethrough"])

    md.inline.ruler.before("escape", "math_inline", _math_inline)
    md.block.ruler.before(
        "fence",
        "math_block",
        _math_block,
        {"alt": ["paragraph", "reference", "blockquote", "list"]},
    )
    md.core.ruler.push("tareas", _marcar_tareas)

    def _r_math_inline(self, tokens, idx, options, env):
        tok = tokens[idx]
        clase = "formula bloque" if tok.meta.get("display") else "formula"
        env["mat"] = True
        return (
            f'<span class="{clase}" data-display="{1 if tok.meta.get("display") else 0}">'
            f"{html.escape(tok.content)}</span>"
        )

    def _r_math_block(self, tokens, idx, options, env):
        env["mat"] = True
        return (
            '<div class="formula-bloque"><span class="formula" data-display="1">'
            f"{html.escape(tokens[idx].content)}</span></div>\n"
        )

    def _r_fence(self, tokens, idx, options, env):
        tok = tokens[idx]
        info = (tok.info or "").strip()
        lenguaje = info.split()[0] if info else ""
        if lenguaje.lower() == "mermaid":
            env["mermaid"] = True
            return (
                '<figure class="diagrama">'
                f'<div class="mermaid">{html.escape(tok.content)}</div>'
                "</figure>\n"
            )
        return _resaltar(tok.content, lenguaje, tok.attrs)

    md.add_render_rule("math_inline", _r_math_inline)
    md.add_render_rule("math_block", _r_math_block)
    md.add_render_rule("fence", _r_fence)
    return md


_MD = _crear_parser()


# --------------------------------------------------------------------------
# Post-proceso del árbol de tokens
# --------------------------------------------------------------------------

def _anclar_encabezados(tokens) -> list[dict]:
    """Pone id a cada encabezado y devuelve el índice del documento."""
    indice: list[dict] = []
    usados: dict[str, int] = {}

    for i, tok in enumerate(tokens):
        if tok.type != "heading_open":
            continue
        nivel = int(tok.tag[1])
        texto = tokens[i + 1].content.strip() if i + 1 < len(tokens) else ""
        if not texto:
            continue

        base = _slug(texto)
        if base in usados:
            usados[base] += 1
            base = f"{base}-{usados[base]}"
        else:
            usados[base] = 0

        tok.attrSet("id", base)
        tok.attrJoin("class", "encabezado")
        if nivel <= 3:
            indice.append({"nivel": nivel, "texto": texto, "id": base})

    return indice


def _convertir_avisos(htm: str) -> str:
    """Transforma las citas > [!NOTE] en tarjetas de aviso."""

    def reemplazo(m: re.Match) -> str:
        tipo = m.group(1).lower()
        etiqueta, clase = AVISOS[tipo]
        return f'<blockquote class="aviso aviso-{clase}"><p class="aviso-titulo">{etiqueta}</p>\n<p>'

    patron = re.compile(
        r"<blockquote>\s*<p>\s*\[!(" + "|".join(AVISOS) + r")\]\s*(?:<br\s*/?>)?\s*",
        re.IGNORECASE,
    )
    return patron.sub(reemplazo, htm)


def _sacar_titulo(titulo: str, tokens, indice: list[dict]) -> tuple[str, list[dict]]:
    """Quita del cuerpo el h1 que ya se muestra en la cabecera.

    Sin esto el título aparece dos veces: una en la cabecera del visor y otra
    como primer encabezado del documento.
    """
    pos = next((i for i, tok in enumerate(tokens) if tok.type == "heading_open"), None)
    if pos is None or tokens[pos].tag != "h1":
        return titulo, indice

    texto = tokens[pos + 1].content.strip()
    if titulo and texto != titulo:
        return titulo, indice

    hid = tokens[pos].attrGet("id")
    del tokens[pos : pos + 3]
    return (titulo or texto), [e for e in indice if e["id"] != hid]


# --------------------------------------------------------------------------
# API pública
# --------------------------------------------------------------------------

@dataclass
class Analisis:
    """Árbol de tokens listo para renderizar a HTML o exportar a Word."""

    meta: dict
    tokens: list
    indice: list[dict]
    titulo: str
    env: dict
    fuente: str


def analizar(texto: str) -> Analisis:
    """Parsea el Markdown sin generar HTML todavía."""
    meta, cuerpo_md = _separar_front_matter(texto)

    env: dict = {}
    tokens = _MD.parse(cuerpo_md, env)
    indice = _anclar_encabezados(tokens)

    # Título: front-matter primero, si no el h1 inicial (que se saca del cuerpo).
    titulo = str(meta.get("title") or meta.get("titulo") or "")
    titulo, indice = _sacar_titulo(titulo, tokens, indice)

    return Analisis(meta, tokens, indice, titulo, env, cuerpo_md)


def renderizar(texto: str) -> Documento:
    """Convierte texto Markdown en un Documento listo para mostrar."""
    a = analizar(texto)
    htm = _MD.renderer.render(a.tokens, _MD.options, a.env)
    htm = _convertir_avisos(htm)

    palabras = len(re.findall(r"\b[\w'’-]+\b", a.fuente))
    return Documento(
        cuerpo=htm,
        indice=a.indice,
        meta=a.meta,
        titulo=a.titulo,
        palabras=palabras,
        minutos=max(1, round(palabras / 220)),
        tiene_mermaid=bool(a.env.get("mermaid")),
        tiene_matematicas=bool(a.env.get("mat")),
    )


def renderizar_archivo(ruta: str | Path) -> Documento:
    """Lee un .md del disco y lo renderiza."""
    ruta = Path(ruta)
    texto = ruta.read_text(encoding="utf-8", errors="replace")
    doc = renderizar(texto)
    if not doc.titulo:
        doc.titulo = ruta.stem
    return doc


def css_resaltado() -> str:
    """CSS de Pygments para los dos temas, cada uno bajo su selector."""
    claro = HtmlFormatter(style=ESTILO_CLARO, cssclass="hl").get_style_defs(
        'body[data-tema="claro"] .hl'
    )
    oscuro = HtmlFormatter(style=ESTILO_OSCURO, cssclass="hl").get_style_defs(
        'body[data-tema="oscuro"] .hl'
    )
    return f"/* tema claro */\n{claro}\n/* tema oscuro */\n{oscuro}\n"
