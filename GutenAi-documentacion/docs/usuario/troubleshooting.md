# Solución de Problemas

## Problemas frecuentes
- **La app no inicia**: ejecuta `python -c "import gi; gi.require_version('Gtk','4.0')"` para verificar bindings. Reinstala `PyGObject` si falla.
- **Previsualización vacía**: confirma que `libwebkit2gtk` esté presente y que no haya bloqueadores (Wayland requiere `GDK_BACKEND=x11` en algunos entornos).
- **Errores al exportar**: revisa la consola para warnings de `GutenCore`. Puede faltar declarar un recurso en el manifest tras añadirlo manualmente.
- **Iconos sin actualizar**: corre `python setup.py` después de reemplazar los SVG/PNG y relanza la sesión.

Amplía esta sección con incidentes nuevos e incluye capturas de diálogos de error (`assets/usuario/popup-error.png`) para facilitar la identificación visual.
