# CLAUDE.md — lectorMD

Visor de Markdown de escritorio (Windows y Linux) con exportación a PDF y Word.
Python 3.12 + PySide6 (Qt WebEngine). Todo el proyecto —código, comentarios,
commits— está en español: sigue igual.

El historial de trabajo, el estado de cada tarea y los defectos conocidos
viven en **`HANDOVER.md`**. Léelo al empezar cada sesión y actualízalo al
terminar cada tarea.

## Reglas no negociables

### 1. Si te falta un dato, para y pregunta

No continúes con un valor supuesto "por ahora". Aplica a nombres de clases y
señales de Qt, APIs de PySide6, elementos y atributos de OOXML/OMML, funciones
del objeto `lector` en `app.js`, versiones de dependencias (PySide6, Mermaid,
KaTeX, mathml2omml), rutas de empaquetado y opciones de PyInstaller o Inno
Setup — y **especialmente** a datos del autor o del proyecto: nombre y correo
del mantenedor, textos legales y de licencias de terceros, número de versión,
notas de publicación, contenido de `DEMO.md`. Si no te lo dieron, escribe
`[PENDIENTE: dato del autor]`.

Un dato inventado es peor que un hueco: una licencia de terceros mal atribuida
o una versión falsa acaba dentro de un instalador publicado.

### 2. Si tienes que romper una regla, dilo antes de escribir código

Romper una regla puede ser correcto. **Romperla en silencio nunca lo es.** La
sección "Desvíos" del reporte es obligatoria incluso vacía.

### 3. Nunca marques nada como terminado por tu cuenta

Vocabulario único de estado: `VERIFICADO`, `SIN VERIFICAR`, `DEFECTUOSO`,
`PENDIENTE`, `DESCARTADO`. **Prohibido el ✅.**

"El código está escrito" es `SIN VERIFICAR`. Si la verificación necesita abrir
la ventana, revisar un PDF o un .docx a ojo (Word, LibreOffice), probar en
Windows o esperar a la CI de GitHub, **no puedes marcarla tú**: propón el
procedimiento y espera.

### 4. Lee antes de escribir

Abre los archivos implicados y di qué encontraste realmente, incluso si
contradice `HANDOVER.md`. Cuando lo contradiga, corrígelo.

### 5. Cambio mínimo, una tarea por vez

Nada de refactorizaciones oportunistas ni de adelantar fases. Si ves otra cosa
que arreglar, anótala como defecto en `HANDOVER.md` y sigue con lo tuyo.

### 6. Commits

- Commits pequeños y frecuentes, mensajes descriptivos. Un commit por unidad
  lógica.
- Ningún commit NUEVO lleva atribución de IA. Ni `Co-Authored-By`, ni
  `co-authored-by`, ni atribuciones a Claude, ChatGPT, OpenAI o Anthropic, ni
  trailers equivalentes. El commit lo firma quien responde de él.

## Reporte al terminar cada tarea

Al final de cada respuesta que cierre una tarea, y resumido también en
`HANDOVER.md`:

```
## Reporte
Hecho:      qué se cambió (archivos y motivo)
Estado:     VERIFICADO | SIN VERIFICAR | DEFECTUOSO | PENDIENTE | DESCARTADO
            (+ cómo se verificó, o el procedimiento propuesto para verificarlo)
Desvíos:    reglas rotas y por qué — "ninguno" si no hubo
Pendientes: lo que queda abierto, incluidos los [PENDIENTE: …]
```

## Referencia rápida del proyecto

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m lectormd DEMO.md                                  # abrir el visor
.venv/bin/python -m lectormd DEMO.md --pdf demo.pdf --docx demo.docx  # modo terminal
PYTHON=.venv/bin/python bash packaging/linux/build.sh                 # .deb + AppImage
```

- `lectormd/app.py` — ventana Qt, exportación PDF, modo terminal.
- `lectormd/renderer.py` — Markdown → HTML (markdown-it-py + Pygments).
- `lectormd/exportar.py` — Markdown → .docx (python-docx, ecuaciones OMML).
- `lectormd/assets/` — `shell.html` (con la CSP), `style.css`, `app.js`, Mermaid y KaTeX.
- `packaging/` — receta de PyInstaller, scripts de Linux y Windows, iconos.
- `.github/workflows/build.yml` — compila, prueba y publica; ignora los cambios que solo tocan `.md`.

No hay tests automáticos: la única comprobación es la prueba de humo de la CI
(exportar `DEMO.md`). La versión vive en `lectormd/__init__.py` y debe coincidir
con la etiqueta `vX.Y.Z`.
