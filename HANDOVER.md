# HANDOVER — lectorMD

Historial de trabajo y estado del proyecto. Se actualiza al terminar cada
tarea. Vocabulario de estado: `VERIFICADO`, `SIN VERIFICAR`, `DEFECTUOSO`,
`PENDIENTE`, `DESCARTADO` (ver `CLAUDE.md`).

## Estado actual

- Versión publicada: **2.0.2** (etiqueta `v2.0.2` sobre `049c927`, release en
  GitHub del 2026-09-30 con .deb, AppImage, instalador y portable de Windows).
  Anteriores: 2.0.1 (`efbce12`, no abre en Linux recientes: D12) y 2.0.0
  (`ef7bd26`, mismo fallo).
- CI: última ejecución en `main` y en `v2.0.2` con éxito (2026-09-30).
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
| D12 | DEFECTUOSO | 2.0.1 (.deb y AppImage de la CI) aborta al abrir la ventana en Zorin 18 / Ubuntu 24.04: `Could not initialize GLX`. Causa: la CI (Ubuntu 22.04) empaqueta `libstdc++.so.6` (GLIBCXX 3.4.30) y `libgcc_s.so.1`, más viejas que las que necesita Mesa del sistema (3.4.33). Corregido en `packaging/lectormd.spec` (se excluyen en Linux) y publicado en 2.0.2; falta abrir la 2.0.2 instalada. El modo terminal no falla porque usa offscreen sin GPU: por eso la prueba de humo de la CI no lo detectó. |
| D13 | PENDIENTE | La CI no prueba la ventana real: solo exporta en offscreen con `--disable-gpu`. Un fallo de GLX o del plugin xcb pasa sin detectarse. |
| D14 | PENDIENTE | La glib empaquetada (22.04) choca con módulos GIO del sistema (`libgvfsdbus.so: undefined symbol: g_task_set_static_name`). Hoy solo es un aviso; vigilar. |
| D15 | PENDIENTE | En este equipo no está instalado `libxcb-cursor0`: las compilaciones locales salen sin él y no abren ventana (`build.sh` solo avisa). También impide `python -m lectormd` en desarrollo. |

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

### 2026-09-29 — Versión 2.0.1

- `__version__` a 2.0.1 y comandos de instalación del README actualizados.
- Etiqueta `v2.0.1` subida. CI 36666791767: Linux, Windows y Publicar con
  éxito (pruebas de humo incluidas); release publicada con los 4 paquetes.
- Estado: CI y publicación `VERIFICADO`. «Acerca de» en los paquetes
  instalados `SIN VERIFICAR` (falta abrirlo en Linux y Windows).
- Desvíos: ninguno.

### 2026-09-29 — 2.0.1 no abre en Linux (D12)

- Diagnóstico: aborto por GLX. Con `LD_PRELOAD` de la libstdc++ del sistema
  abre; con una copia de `/opt/lectormd` sin `libstdc++.so.6` ni
  `libgcc_s.so.1` abre la ventana y exporta PDF y Word.
- `packaging/lectormd.spec`: esas dos bibliotecas se excluyen en Linux.
  Compilado en local: la poda las deja fuera (la ventana local no abre por D15,
  ajeno a esto).
- Estado: corrección `SIN VERIFICAR` en un paquete de la CI.
- Desvíos: ninguno.

### 2026-09-30 — Versión 2.0.2

- `f81e2e5` (corrección D12) y `049c927` (`__version__` 2.0.2, README).
- CI de `main` 36670618606 con éxito. Por decisión del autor se etiquetó
  `v2.0.2` sin esperar a probar aquí el .deb de la CI (la descarga iba a
  ~200 KB/s). CI 36671719109: Linux, Windows y Publicar con éxito; release
  publicada con los 4 paquetes.
- Estado: publicación `VERIFICADO`. Que la ventana abra con el .deb/AppImage
  de la 2.0.2 en Zorin 18: `SIN VERIFICAR`.
- Desvíos: ninguno (la prueba previa se omitió a petición del autor).
