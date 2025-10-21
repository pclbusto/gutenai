# Arquitectura de GutenAI

## Visión general
GutenAI se compone de tres capas colaborativas:
1. **Interfaz (GTK4/libadwaita)**: ventanas, paneles y mecanismos de interacción del usuario.
2. **Núcleo (`GutenCore`)**: lógica de negocio que manipula la estructura EPUB y orquesta el workspace.
3. **Recursos externos**: archivos EPUB, assets, iconos y dependencias de sistema.

Añade un diagrama general en `docs/assets/arquitectura/diagrama-capas.png` para visualizar estas relaciones.

## Componentes principales
- `GutenAIApplication` (`gtk_ui/main_window.py`): punto de entrada y ciclo de vida GTK.
- `GutenAIWindow`: contenedor principal que conecta sidebars, editor y previsualización.
- `SidebarLeft`: renderiza la jerarquía de recursos del EPUB utilizando datos proporcionados por el núcleo.
- `CentralEditor`: instancia editores especializados (HTML, CSS, imágenes) según el recurso activo.
- `SidebarRight`: previsualiza contenido HTML y recursos multimedia con WebKit.
- `GutenCore` (`core/guten_core.py`): gestiona manifest, spine, metadatos y sincronización con disco.

Para cada componente, captura pantallas o diagramas de flujo en `assets/arquitectura/` (`diagrama-sidebar-left.png`, etc.).

## Flujo de apertura y edición
1. El usuario selecciona un EPUB → `GutenAIWindow` invoca `GutenCore.open_epub()`.
2. `GutenCore` descomprime el paquete en el workspace y carga el OPF en memoria.
3. `SidebarLeft` se actualiza con la nueva estructura y el usuario elige un recurso.
4. `CentralEditor` solicita el contenido y habilita la edición.
5. Al guardar, `CentralEditor` envía los cambios a `GutenCore`, que persiste en disco y actualiza el OPF.
6. `SidebarRight` escucha el cambio y renderiza la vista previa correspondiente.

Documenta este flujo con un diagrama de secuencia en `diagrama-flujo-edicion.png` si necesitas más detalle.

## Interacción y señales
- La UI emplea señales de GTK/GObject para avisar cambios de recurso, guardados y errores.
- `GutenCore` expone hooks para operaciones largas (exportar, validar) y avisos de inconsistencias.
- Cualquier extensión debe respetar la separación: la UI nunca manipula archivos directos, sino que delega en el core.

## Puntos de extensión
- **Nuevos tipos de recurso**: amplía `MEDIA_TO_KIND` y proporciona un handler específico en `CentralEditor`.
- **Automatización**: scripts externos pueden usar `GutenCore` en modo CLI para tareas batch.
- **Integración continua**: configura pipelines que ejecuten `python -m unittest` y validen assets.

> [!TIP]
> Registra decisiones de arquitectura significativas en esta página con fecha y motivo para mantener historial.
