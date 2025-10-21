# 🔍 Panel de Búsqueda en GutenAI

## ✅ Nueva Funcionalidad Implementada

Se ha añadido un **panel de búsqueda deslizable** en la parte inferior del editor central con funcionalidades avanzadas de búsqueda y reemplazo.

## 🎯 Características

### **🔤 Búsqueda Avanzada**
- **Búsqueda en tiempo real** mientras escribes
- **Resaltado de resultados** en amarillo
- **Navegación entre resultados** con botones y atajos
- **Contador de resultados** (ej: "3 de 15")

### **⚙️ Opciones de Búsqueda**
- ✅ **Mayús/minús**: Coincidencia exacta de mayúsculas/minúsculas
- ✅ **Palabras completas**: Solo palabras enteras
- ✅ **Regex**: Expresiones regulares completas

### **🔄 Búsqueda y Reemplazo**
- **Reemplazar actual**: Reemplaza la coincidencia seleccionada
- **Reemplazar todo**: Reemplaza todas las coincidencias de una vez
- **Vista previa visual** de las coincidencias antes de reemplazar

### **⌨️ Atajos de Teclado**
- `Ctrl+F` - Abrir/cerrar panel de búsqueda
- `F3` - Siguiente resultado
- `Shift+F3` - Resultado anterior
- `Escape` - Cerrar panel de búsqueda
- `Enter` (en campo de búsqueda) - Siguiente resultado

### **🎨 Interfaz Moderna**
- **Panel deslizable** con animación suave
- **Diseño libadwaita** integrado con el tema
- **Botones con iconos** intuitivos
- **Tooltips explicativos** en todos los controles

## 🎮 Cómo Usar

### **1. Abrir Panel de Búsqueda**

**Opciones para abrir:**
- Presiona `Ctrl+F`
- Menú → Herramientas → Buscar en documento
- El panel se desliza desde abajo

### **2. Búsqueda Básica**

1. **Escribe tu texto** en el campo "Buscar en el documento..."
2. **Ve los resultados** resaltados automáticamente
3. **Navega** con `F3` (siguiente) o `Shift+F3` (anterior)
4. **Observa el contador** que muestra "X de Y" resultados

### **3. Búsqueda Avanzada**

**Activar opciones:**
- ☑️ **Mayús/minús**: Para búsquedas exactas (`Casa` ≠ `casa`)
- ☑️ **Palabras completas**: Solo palabras enteras (`cat` no encuentra `category`)
- ☑️ **Regex**: Usar patrones (`\\d+` para números, `[a-z]+` para letras)

**Ejemplos de regex:**
- `\\d+` - Encuentra números
- `[A-Z][a-z]+` - Encuentra palabras que empiecen con mayúscula
- `\\b\\w{5}\\b` - Encuentra palabras de exactamente 5 letras

### **4. Búsqueda y Reemplazo**

1. **Busca tu texto** en el campo superior
2. **Escribe el reemplazo** en "Reemplazar con..."
3. **Opciones:**
   - `Reemplazar` - Solo la coincidencia actual
   - `Reemplazar todo` - Todas las coincidencias

### **5. Cerrar Panel**

**Opciones para cerrar:**
- Presiona `Escape`
- Clic en el botón ❌
- Presiona `Ctrl+F` de nuevo

## 🛠️ Detalles Técnicos

### **Arquitectura**
- **Panel**: `Gtk.Revealer` con animación `SLIDE_UP`
- **Búsqueda**: Motor de regex Python con highlighting GTK
- **Integración**: Nuevas acciones en el sistema de acciones de GutenAI

### **Componentes**
```
CentralEditor
├── main_container (Gtk.Box)
│   ├── content_stack (editor/imagen)
│   └── search_overlay (Gtk.Overlay)
│       └── search_revealer (Gtk.Revealer)
│           └── search_panel (Gtk.Box)
│               ├── search_main_row
│               │   ├── search_entry
│               │   ├── prev_button
│               │   ├── next_button
│               │   ├── results_label
│               │   └── close_button
│               └── options_row
│                   ├── case_sensitive_check
│                   ├── whole_words_check
│                   ├── regex_check
│                   ├── replace_entry
│                   ├── replace_button
│                   └── replace_all_button
```

### **Nuevas Acciones**
- `win.search_in_document` - Abrir/cerrar búsqueda
- `win.search_next` - Siguiente resultado
- `win.search_prev` - Resultado anterior

### **Métodos Públicos**
```python
# Mostrar/ocultar panel
central_editor.show_search_panel()
central_editor.hide_search_panel()
central_editor.toggle_search_panel()

# Verificar estado
if central_editor.search_visible:
    print("Panel de búsqueda abierto")
```

## 🧪 Pruebas

### **Escenarios de Prueba**

1. **Búsqueda Básica**
   - Abre un documento HTML
   - Presiona `Ctrl+F`
   - Busca "div" → Debe resaltar todas las etiquetas div

2. **Búsqueda con Opciones**
   - Busca "HTML" con Mayús/minús activado
   - Debe distinguir entre "HTML" y "html"

3. **Regex**
   - Activa Regex
   - Busca `\\d+` → Debe encontrar todos los números

4. **Reemplazo**
   - Busca "class"
   - Reemplaza con "className"
   - Prueba tanto "Reemplazar" como "Reemplazar todo"

5. **Navegación**
   - Busca un término común
   - Usa `F3` y `Shift+F3` para navegar
   - Verifica que el contador se actualice

6. **Escape**
   - Abre búsqueda con `Ctrl+F`
   - Cierra con `Escape`
   - Verifica que el foco regrese al editor

## 🎨 Personalización

### **Estilos CSS**
El panel usa las siguientes clases CSS:
```css
.search-panel {
    /* Panel principal */
}

.search-panel entry {
    /* Campos de entrada */
}

.search-panel button {
    /* Botones */
}

.search-panel checkbutton {
    /* Checkboxes */
}
```

### **Colores de Resaltado**
- **Coincidencias**: Fondo amarillo
- **Tag GTK**: `search-highlight`

## 🚀 Uso en Flujo de Trabajo

### **Caso de Uso: Edición de EPUB**

1. **Abrir capítulo** desde el sidebar izquierdo
2. **Buscar elemento** específico (`<p class="quote">`)
3. **Usar regex** para encontrar patrones complejos
4. **Reemplazar en masa** atributos o estilos
5. **Navegar rápidamente** entre coincidencias
6. **Cerrar búsqueda** y continuar editando

### **Flujo Típico**
```
Ctrl+F → Escribir búsqueda → F3/Shift+F3 → Editar → Escape
```

## ✨ Beneficios

- **🚀 Productividad**: Encuentra y edita contenido rápidamente
- **🎯 Precisión**: Opciones avanzadas para búsquedas exactas
- **🔄 Eficiencia**: Reemplazo masivo con vista previa
- **⌨️ Accesibilidad**: Atajos de teclado estándar
- **🎨 UX**: Interfaz moderna y responsiva

¡El panel de búsqueda está completamente integrado y listo para usar en GutenAI! 🎉