# Estructura del EPUB

El panel lateral izquierdo (sidebar) muestra la estructura completa del EPUB con el que estás trabajando.
Desde allí podés acceder rápidamente a todos los recursos del libro.

Las secciones visibles son:
- **Texto**
- **Estilos**
- **Imágenes**
- **Fuentes**
- **Audio**
- **Video**
- **Metadata**

Podés ocultar o mostrar este panel para ganar más espacio de trabajo en el área central.
El atajo de teclado para alternar su visibilidad es `F9`.

## Sección: Texto

La categoría **Texto** agrupa todos los capítulos en formato XHTML, que conforman el contenido principal del libro.

> **Importante sobre el Orden de Lectura (Spine)**:
> El orden en el que ves los archivos listados en esta sección es **el orden real de lectura** del libro (lo que técnicamente se conoce como *Spine*).
>
> Si cambias el orden de los archivos aquí, cambiará el orden en el que aparecen las páginas al leer el EPUB.

En el encabezado de esta sección vas a encontrar varios íconos que permiten realizar acciones rápidas:

### 📄 1. Crear nuevo HTML
**Icono**: un papel (new file)

Crea un nuevo archivo XHTML dentro del proyecto. Ideal para agregar capítulos, secciones o páginas adicionales.

### 📁 2. Importar HTML
**Icono**: carpeta (import)

Permite traer archivos HTML/XHTML que ya tengas creados fuera del proyecto.
Por ejemplo, si escribiste capítulos en otro editor y querés integrarlos a Guten.AI, esta es la forma correcta de hacerlo.

### ⋮ 3. Menú de acciones
**Icono**: tres puntitos

Este menú ofrece operaciones avanzadas sobre los archivos de texto:

- **Seleccionar todo**: selecciona todos los capítulos de la categoría.
- **Agregar a la spine**: si algún archivo no está incluido en la secuencia de lectura, podés incorporarlo.
- **Quitar de la spine**: elimina el capítulo de la secuencia de lectura sin borrarlo del proyecto.
- **Vincular estilos**: permite asociar hojas de estilo CSS a uno o varios archivos XHTML.
    - *Nota*: Al seleccionar esta opción, se abre una ventana con todos los estilos disponibles en el EPUB. Allí podés marcar cuáles querés vincular a los capítulos seleccionados, o desmarcar para eliminar vínculos existentes.
- **Eliminar**: quita definitivamente el archivo HTML del proyecto.

## Renombrar recursos

Podés cambiar nombres de archivos desde el panel de la izquierda. Hay dos modos:

### Renombrado simple (un archivo)
- Cómo acceder: clic derecho sobre el recurso y elegí «Renombrar», o presioná `F2`.
- Validación: la ventana avisa si el nombre ya existe para evitar conflictos.
- Alcance: actualiza el workspace y los metadatos del proyecto (manifest y spine). Si tu documento contiene enlaces internos entre capítulos, revisalos después del cambio.

### Renombrado en lote de capítulos
- Acceso rápido: `Ctrl+Shift+R` (ver [Atajos de teclado](../usuario/atajos.md)). También disponible desde el menú contextual de la sección **Texto**.
- Pensado para: capítulos XHTML de la categoría **Texto**. Para estilos, imágenes u otros recursos usá el renombrado simple.
- Configuración de la ventana:
  - Prefijo fijo: parte del nombre que no cambia (por ej., `chap-`).
  - Número inicial: define desde qué número arranca la secuencia (por ej., `1`).
  - Número de dígitos: determina el relleno con ceros (por ej., `3` produce `001`, `002`, `003`).
  - Vista previa de ejemplo: muestra cómo quedarían los nombres generados antes de aplicar.
  - Archivos a renombrar: lista de capítulos dentro de **Texto** para elegir exactamente cuáles renombrar.
  - Acciones de selección: «Seleccionar todo», «Deseleccionar todos» y «Desde actual» (si ya estás parado en un capítulo, aplica desde ese hacia adelante).
  - Aplicar: botón «Aplicar renombrado» (arriba a la derecha) para ejecutar los cambios.
- Conflictos: si algún nombre destino ya existe, la herramienta lo indica y no aplica los cambios hasta que lo resuelvas.
