# Guía de Usuario de GutenAI

## ¿Qué es GutenAI?
GutenAI es un editor modular de libros EPUB con interfaz GTK4/libadwaita. Permite abrir, modificar y exportar libros digitales con herramientas visuales y soporte para HTML, CSS e imágenes.

## Requisitos previos
- **Sistema**: Linux con GTK4, libadwaita y WebKit instalados (`python-gobject`, `libadwaita-1`, `libwebkit2gtk-4.0`).
- **Python**: versión 3.10+ con `pip`.
- **Dependencias**: instala `pip install -r requirements.txt` dentro de un entorno virtual (`python -m venv .venv && source .venv/bin/activate`).
- **Material de prueba**: la carpeta `libros/` incluye EPUBs de demostración.

## Instalación y primer arranque
1. Clona el repositorio y entra a la raíz.
2. Crea/activa el entorno virtual y ejecuta `pip install -r requirements.txt`.
3. Inicia la app con `python main.py` o usa `./run_gutenai.sh` (recomendado porque fuerza el intérprete del entorno).
4. Al abrirse, verás la ventana principal vacía lista para cargar un libro.

![Ventana principal sin libro](../assets/usuario/pantalla-inicio.png)

## Recorrido por la interfaz
1. **Barra superior**: muestra el nombre del libro, acciones rápidas y menú con preferencias.
2. **Sidebar izquierda**: árbol de recursos (documentos, estilos, imágenes) sincronizado con el manifest EPUB.
3. **Editor central**: presenta el contenido seleccionado con herramientas contextualizadas (HTML, CSS o visor de imágenes).
4. **Panel derecho**: previsualización en vivo del recurso, ideal para validar estilos y maquetación.

![Ventana principal con libro](../assets/usuario/pantalla-editor.png)


## Crear un nuevo proyecto
En la barra de título, esquina superior derecha, está el menú hamburguesa (☰) con las opciones principales. Por ahora, la opción disponible para arrancar es **Nuevo Proyecto** (*New Project*), accesible también con `Ctrl+N` (ver [Atajos de teclado](../usuario/atajos.md)).

Al elegir **Nuevo Proyecto**, GutenAI genera en la carpeta indicada la estructura base de un EPUB sin comprimir:
- `text/`: capítulos en XHTML (se incluye `chap-1.xhtml` de ejemplo).
- `styles/`: hojas de estilo CSS (arranca con `style.css` editable).
- `images/`: recursos gráficos.
- `fonts/`: tipografías personalizadas.
- `audio/`: pista o efectos de sonido (vacío por defecto).
- `video/`: material audiovisual (vacío por defecto).
- `metadata/`: incluye `content.opf` con autor, título, idioma, derechos, etc.

Tras crear el proyecto, la barra lateral izquierda muestra la estructura agrupada (Texto, Estilos, Imágenes, Fuentes, Audio, Video y Metadatos). A partir de ahí puedes añadir contenido, editar XHTML o ajustar CSS según necesites.

## Abrir un proyecto existente
El menú hamburguesa (☰) también incluye dos vías para trabajar con contenido ya creado:

- **Abrir EPUB** (`Ctrl+O`): carga un archivo EPUB comprimido para editarlo directamente. Es ideal para pulir un libro finalizado, hacer correcciones rápidas o revisar su estructura sin descomprimir. Ten en cuenta que el archivo permanece empaquetado, así que no tendrás acceso directo a imágenes o estilos desde el gestor de archivos (no se recomienda buscar la carpeta temporal de procesamiento).
- **Abrir carpeta de proyecto** (`Ctrl+Shift+O`): abre un EPUB ya descomprimido, con la estructura interna tal como la genera GutenAI al crear un proyecto nuevo. Permite navegar la carpeta con el explorador, abrir imágenes en GIMP/Krita/Inkscape, editar CSS con herramientas externas e integrar recursos (fuentes, audio, video). Es el modo recomendado para flujos de trabajo técnicos o integrados con otras apps o con Git. Más combinaciones en [Atajos de teclado](../usuario/atajos.md).

¿Cuál elegir?
- *Nuevo Proyecto*: para empezar desde cero.
- *Abrir EPUB*: para tocar un archivo final o publicado.
- *Abrir carpeta de proyecto*: para un flujo editable y abierto, compatible con herramientas externas.

## Flujo típico de trabajo
1. **Abrir o crear proyecto** (`Ctrl+O` / `Ctrl+Shift+O` / `Ctrl+N`): selecciona *Archivo → Abrir EPUB*, *Abrir carpeta de proyecto* o *Nuevo proyecto*. Si eliges abrir EPUB, el núcleo (`GutenCore`) descomprime el archivo en un workspace temporal. Si eliges abrir carpeta, trabajas sobre la estructura ya descomprimida. Si eliges proyecto nuevo, se genera en la carpeta que indiques la estructura completa de un EPUB sin comprimir (mimetype, `META-INF`, `OEBPS`, etc.); puedes seguir trabajando ahí directamente o exportarlo a EPUB y continuar sobre el archivo empaquetado. Consulta el resto de combinaciones en [Atajos de teclado](../usuario/atajos.md).
2. **Organizar recursos**: arrastra archivos dentro del sidebar para reordenar capítulos; la app actualiza el spine automáticamente.
3. **Editar contenido**: usa el editor central; la barra contextual ofrece atajos para encabezados, listas o estilos. Los cambios se aplican sobre el archivo del workspace.
4. **Previsualizar**: el panel derecho recarga en cuanto guardas (`Ctrl+S`) o cambias de recurso.
5. **Exportar** (`Ctrl+Shift+E`): desde *Archivo → Exportar EPUB* empaquetas el proyecto con las modificaciones. Más combinaciones en [Atajos de teclado](../usuario/atajos.md).

## Gestión de proyectos
- **Agregar recursos**: través del menú contextual del sidebar izquierdo puedes importar HTML, imágenes o estilos que se incorporan al manifest.
- **Renombrar o mover**: las rutas se actualizan en el workspace; recuerda revisar enlaces internos en documentos complejos.
- **Historial manual**: no hay sistema de versiones interno; utiliza git o haz copias en `libros/` para hitos importantes.

## Atajos y trucos
- Consulta la lista completa en [Atajos de teclado](../usuario/atajos.md).
- Mantén un ojo en las notificaciones de la cabecera; advierten cuando hay recursos sin guardar.
- Para ver cómo se organiza el árbol de recursos, revisa [Estructura del EPUB](../usuario/estructura_epub.md).

## Resolución de problemas frecuentes
- **La app no inicia**: ejecuta `python -c "import gi; gi.require_version('Gtk','4.0')"` para verificar bindings. Reinstala `PyGObject` si falla.
- **Previsualización vacía**: confirma que `libwebkit2gtk` esté presente y que no haya bloqueadores (Wayland requiere `GDK_BACKEND=x11` en algunos entornos).
- **Errores al exportar**: revisa la consola para warnings de `GutenCore`. Puede faltar declarar un recurso en el manifest tras añadirlo manualmente.
- **Iconos sin actualizar**: corre `python setup.py` después de reemplazar los SVG/PNG y relanza la sesión.

Amplía esta sección con incidentes nuevos e incluye capturas de diálogos de error (`assets/usuario/popup-error.png`) para facilitar la identificación visual.
