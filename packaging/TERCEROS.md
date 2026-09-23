# Componentes de terceros incluidos en lectorMD

Los ejecutables de lectorMD incluyen el siguiente software de terceros, cada
uno bajo su propia licencia.

## Qt 6 y PySide6 — LGPL v3

- Qt 6 (incluido Qt WebEngine) © The Qt Company Ltd. y colaboradores
- PySide6 y Shiboken6 © The Qt Company Ltd.

Se distribuyen bajo la GNU Lesser General Public License v3
(https://www.gnu.org/licenses/lgpl-3.0.html).

Las bibliotecas de Qt se enlazan de forma dinámica y van como archivos
separados dentro de la carpeta del programa (`_internal/PySide6`). Puedes
sustituirlas por otra versión compatible. El código fuente de Qt está en
https://download.qt.io/official_releases/qt/ y el de PySide6 en
https://code.qt.io/cgit/pyside/pyside-setup.git/

Qt WebEngine incorpora Chromium, cuyos componentes tienen sus propias
licencias (mayoritariamente BSD): https://www.chromium.org/chromium-os/licensing/

## Bibliotecas de Python

| Componente | Licencia |
|---|---|
| Python 3.12 | PSF License |
| markdown-it-py, mdurl | MIT |
| Pygments | BSD-2-Clause |
| PyYAML | MIT |
| python-docx | MIT |
| lxml (incluye libxml2 y libxslt) | BSD-3-Clause / MIT |
| typing_extensions | PSF-2.0 |
| latex2mathml | MIT |
| mathml2omml | MIT |

## Bibliotecas de JavaScript

| Componente | Licencia |
|---|---|
| Mermaid © Knut Sveidqvist y colaboradores | MIT |
| KaTeX (y sus fuentes) © Khan Academy y colaboradores | MIT |

Los textos completos de las licencias están en el sitio de cada proyecto.
