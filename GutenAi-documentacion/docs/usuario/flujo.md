# Flujo de Trabajo

## Flujo típico
1. **Abrir o crear proyecto** (`Ctrl+O` / `Ctrl+Shift+O` / `Ctrl+N`): selecciona *Archivo → Abrir EPUB*, *Abrir carpeta de proyecto* o *Nuevo proyecto*. Si eliges abrir EPUB, el núcleo (`GutenCore`) descomprime el archivo en un workspace temporal. Si eliges abrir carpeta, trabajas sobre la estructura ya descomprimida. Si eliges proyecto nuevo, se genera en la carpeta que indiques la estructura completa de un EPUB sin comprimir (mimetype, `META-INF`, `OEBPS`, etc.); puedes seguir trabajando ahí directamente o exportarlo a EPUB y continuar sobre el archivo empaquetado. Consulta el resto de combinaciones en [Atajos de teclado](../usuario/atajos.md).
2. **Organizar recursos**: arrastra archivos dentro del sidebar para reordenar capítulos; la app actualiza el spine automáticamente.
3. **Editar contenido**: usa el editor central; la barra contextual ofrece atajos para encabezados, listas o estilos. Los cambios se aplican sobre el archivo del workspace.
4. **Previsualizar**: el panel derecho recarga en cuanto guardas (`Ctrl+S`) o cambias de recurso.
5. **Exportar** (`Ctrl+Shift+E`): desde *Archivo → Exportar EPUB* empaquetas el proyecto con las modificaciones. Más combinaciones en [Atajos de teclado](../usuario/atajos.md).
