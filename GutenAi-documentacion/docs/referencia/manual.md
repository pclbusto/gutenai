# Manual de Referencia Técnica

## Estructura del proyecto
- `main.py`: punto de entrada que inicializa `GutenAIApplication` desde `gtk_ui`.
- `gtk_ui/`: widgets y controladores UI (`main_window.py`, `sidebar_left.py`, `central_editor.py`, acciones y diálogos).
- `core/guten_core.py`: núcleo que gestiona el workspace EPUB, manifest y operaciones IO.
- `utils/`: utilidades compartidas (transformaciones, helpers de archivos).
- `data/` y `libros/`: recursos de ejemplo y EPUBs de prueba.
- `tests/`: suite inicial con `unittest`; extiéndela paralelamente a los módulos que cubras.

Guarda diagramas de dependencias en `docs/assets/referencia/diagrama-modulos.png` y referencia cuando describas la interacción entre capas.

## Configuración del entorno
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Dependencias clave:
- `ebooklib`: empaquetado y lectura de EPUB.
- `PyGObject` (GTK4 + libadwaita + WebKit2).
- Opcionales: `watchdog` para reaccionar a cambios en disco, `Pillow` para `setup.py`.

## Comandos esenciales
- `python main.py`: ejecuta la aplicación (requiere entorno gráfico).
- `./run_gutenai.sh`: wrapper que usa `.venv/bin/python` directamente.
- `python setup.py`: genera e instala iconos PNG/SVG en el tema hicolor del usuario.
- `python -m unittest discover tests`: ejecuta la suite completa.
- `python -m core.guten_core`: ejecuta pruebas manuales sobre el núcleo (útil para depuración CLI).

Incluye capturas de consola en `assets/referencia/` si quieres ilustrar salidas (`cli-ejecucion.png`).

## APIs relevantes
### `GutenCore`
- `new_project(layout=...)`: crea un workspace con estructura `OEBPS`.
- `open_epub(path)`: abre un EPUB empaquetado.
- `add_manifest_item(...)` / `remove_manifest_item(...)`: gestionan recursos del OPF.
- `write()` y `export_epub(destino)`: persisten los cambios.
- Internamente mantiene cachés de manifest, spine y metadatos usando `xml.etree.ElementTree`.

> [!NOTE]
> Documenta cualquier método adicional que agregues y complementa con snippets colocados en bloques de código.

### UI (`gtk_ui`)
- `GutenAIWindow`: orquesta paneles y acciones.
- `SidebarLeft`: muestra árbol de recursos; escucha señales para refrescar estructura.
- `CentralEditor`: carga editores específicos según MIME.
- `SidebarRight`: previsualiza recursos (HTML/imágenes).
- `ActionManager` y `DialogManager`: encapsulan acciones y diálogos GTK.

## Estándares de contribución
- Sigue PEP 8 con cuatro espacios y `snake_case` para módulos.
- Añade type hints y docstrings en español.
- Divide commits por tema (core, UI, utilidades) y usa mensajes en presente.
- Ejecuta `python -m unittest` antes de abrir un PR y adjunta capturas o GIFs en cambios visuales.

## Recursos adicionales
- Guarda notas de depuración en `docs/assets/referencia/notas-debug.md` si necesitas ampliar.
- Actualiza `mkdocs.yml` cuando incorpores nueva documentación para mantener la navegación coherente.
