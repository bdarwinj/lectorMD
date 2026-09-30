# HANDOVER — lectorMD

Historial de trabajo y estado del proyecto. Se actualiza al terminar cada
tarea. Vocabulario de estado: `VERIFICADO`, `SIN VERIFICAR`, `DEFECTUOSO`,
`PENDIENTE`, `DESCARTADO` (ver `CLAUDE.md`).

## Estado actual

- Versión publicada: **2.0.0** (etiqueta `v2.0.0` sobre `ef7bd26`, release en
  GitHub del 2026-09-23 con .deb, AppImage, instalador y portable de Windows).
- CI: última ejecución en `main` y en `v2.0.0` con éxito (2026-09-23).
- Árbol de trabajo limpio y sincronizado con `origin/main` a 2026-09-29.

## Defectos y mejoras conocidos

Anotados durante el análisis del 2026-09-29. Ninguno se ha tocado todavía.

| # | Estado | Descripción |
|---|---|---|
| D1 | PENDIENTE | `dist/paquetes/` local se compiló el 2026-09-22 antes de `ef7bd26`: no incluye la corrección del modo terminal. Los paquetes buenos son los de la release de GitHub. |
| D2 | PENDIENTE | No hay tests automáticos; solo la prueba de humo de la CI. |
| D3 | PENDIENTE | No hay `pyproject.toml`: el paquete no se instala con pip ni tiene *entry point*. |
| D4 | PENDIENTE | CSP de `shell.html`: `script-src file:` admite cualquier script local, no solo los del programa (hoy no explotable porque el cuerpo entra por `innerHTML`). |
| D5 | PENDIENTE | `img-src http: https:` y la exportación a Word descargan imágenes remotas al abrir/exportar: filtra la IP de quien lee (píxel de rastreo). |
| D6 | PENDIENTE | En Ubuntu 24.04+ se desactiva el sandbox de Chromium (`app.py`, `_preparar_entorno`). Decisión documentada; revisar si hay alternativa. |
| D7 | PENDIENTE | Datos duplicados: paletas en `style.css` y `PALETAS` de `app.py`; `AVISOS` en `renderer.py` y `exportar.py` con colores distintos; `lectormd.svg` en `assets/` y `packaging/iconos/`. |
| D8 | PENDIENTE | Código sin uso: `renderer.renderizar_archivo()` y los campos `tiene_mermaid` / `tiene_matematicas` de `Documento`. |
| D9 | PENDIENTE | `mathml2omml==0.0.2` fijada y muy pequeña: si falla, las fórmulas caen a texto plano sin aviso. |
| D10 | PENDIENTE | `PySide6<6.12`: habrá que probar y subir el tope cuando salga Qt 6.12. |
| D11 | PENDIENTE | GitHub muestra a `claude` en Contributors. Origen: el primer push (2026-09-23 05:23Z) subió `4e59add` y `e0891d2` con `Co-Authored-By: Claude Opus 5.5`; a los 7 min un force-push los sustituyó por `4631f04` y `492112c`, que están limpios. Los commits viejos siguen en GitHub sin rama, los referencia la ejecución de Actions `35822208398` y la barra lateral de Contributors está en caché. El historial actual (local y remoto) está limpio. 2026-09-29: se sube un commit nuevo para forzar el recálculo; borrar la ejecución `35822208398` queda para el autor (Actions → ejecución → «Delete workflow run»). Si persiste: GitHub Support. |

## Historial

### 2026-09-29 — Análisis del proyecto y reglas de trabajo

- Análisis completo: documentación, código, empaquetado, historial git, CI y
  release. Resultado: tabla de defectos D1–D10.
- Creados `CLAUDE.md` (reglas no negociables, formato de reporte, referencia
  rápida) y este `HANDOVER.md`.
- Estado: `SIN VERIFICAR` — pendiente de revisión del autor.
- Desvíos: ninguno.

### 2026-09-29 — Atribución de IA visible en GitHub (D11)

- Encontrado el origen: commits `4e59add` y `e0891d2` del primer push, con
  `Co-Authored-By: Claude`, sustituidos por force-push pero aún en GitHub.
- Commit de `CLAUDE.md` y `HANDOVER.md` subido a `main` para que GitHub
  recalcule Contributors.
- Estado: `SIN VERIFICAR` — hay que mirar la barra lateral del repositorio.
- Desvíos: el borrado de la ejecución `35822208398` lo bloqueó el entorno;
  no se intentó por otra vía. Lo hace el autor desde la web.

### 2026-09-29 — Autor y canal de YouTube en «Acerca de»

- `lectormd/app.py`, `_acerca()`: añadido «Creado por Darwin J. Bolívar V.» y
  el enlace https://www.youtube.com/@bdarwinj, con el color de acento del tema.
  `QMessageBox.about` ya abre los enlaces externos (comprobado en PySide6 6.11.2).
- Estado: `SIN VERIFICAR` — captura offscreen correcta; falta verlo en la
  ventana real (tema oscuro) y comprobar que el enlace abre el navegador.
- Desvíos: ninguno.
