# Gestión de Proyectos

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

### ¿Cuál elegir?
- *Nuevo Proyecto*: para empezar desde cero.
- *Abrir EPUB*: para tocar un archivo final o publicado.
- *Abrir carpeta de proyecto*: para un flujo editable y abierto, compatible con herramientas externas.

## Gestión de recursos
- **Agregar recursos**: través del menú contextual del sidebar izquierdo puedes importar HTML, imágenes o estilos que se incorporan al manifest.
- **Renombrar o mover**: las rutas se actualizan en el workspace; recuerda revisar enlaces internos en documentos complejos.
- **Historial manual**: no hay sistema de versiones interno; utiliza git o haz copias en `libros/` para hitos importantes.
