# Guten.AI - Editor EPUB Modular

Editor de libros electrónicos con arquitectura de componentes independientes.

## 🚀 Características

- 🏗️ **Arquitectura modular**: Componentes independientes y testeables
- 🎨 **Interfaz moderna**: GTK4 + libadwaita
- 📝 **Editor avanzado**: HTML/CSS con resaltado de sintaxis
- 👁️ **Previsualización**: Tiempo real con WebKit
- 🔧 **API unificada**: EpubManager como núcleo central

## 📦 Instalación

```bash
# Clonar repositorio
git clone https://github.com/guten-ai/guten.git
cd guten

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
python gutenai/main.py
```

## 🏗️ Arquitectura

### Componentes Principales

1. **EpubManager** (`core/epub_manager.py`)
   - Gestión centralizada del estado EPUB
   - API unificada para todos los componentes
   - Sistema de señales para comunicación

2. **Sidebar Izquierdo** (`components/sidebar_left.py`)
   - Navegador de estructura EPUB
   - Organización por categorías de recursos
   - Árbol colapsable y búsqueda

3. **Panel Central** (`components/editor_panel.py`)
   - Editor multimodo según tipo de recurso
   - HTML: Editor con toolbar de formato
   - CSS: Editor con resaltado de sintaxis
   - Imágenes: Vista de galería

4. **Sidebar Derecho** (`components/sidebar_right.py`)
   - Previsualización WebKit en tiempo real
   - Visor de imágenes con zoom
   - Inspector de metadatos

### Principios de Diseño

- **Separación de responsabilidades**: Cada componente tiene una función específica
- **Comunicación por señales**: Eventos GObject para coordinación
- **Testing independiente**: Cada componente puede probarse por separado
- **Extensibilidad**: Fácil añadir nuevos tipos de recursos y modos

## 🧪 Desarrollo

### Probar Componentes Independientemente

```bash
# Desde el directorio raíz del proyecto
cd gutenai

# Probar sidebar izquierdo
python -m components.sidebar_left

# Probar editor central
python -m components.editor_panel

# Probar sidebar derecho  
python -m components.sidebar_right

# Aplicación integrada completa
python -m components.integrated_app
```

### Estructura del Proyecto

```
gutenai/
├── main.py                     # Aplicación principal
├── core/
│   ├── __init__.py
│   └── epub_manager.py        # Gestor central EPUB
├── components/
│   ├── __init__.py
│   ├── sidebar_left.py        # Navegador estructura
│   ├── editor_panel.py        # Editor central
│   ├── sidebar_right.py       # Previsualización
│   └── integrated_app.py      # App integrada
├── widgets/
│   ├── __init__.py
│   └── custom_widgets.py      # Widgets personalizados
└── tests/
    └── __init__.py
```

## 🔧 Dependencias

- **Python 3.8+**
- **PyGObject 3.42+**: Bindings GTK4
- **ebooklib 0.18+**: Manipulación EPUB
- **GTK4**: Toolkit de interfaz
- **libadwaita**: Componentes UI modernos
- **WebKit2**: Previsualización HTML (opcional)
- **GtkSourceView**: Resaltado sintaxis (opcional)

## 📚 Uso

### Operaciones Básicas

1. **Crear nuevo libro**: Archivo → Nuevo EPUB
2. **Abrir libro existente**: Archivo → Abrir EPUB
3. **Navegar recursos**: Panel izquierdo → Categorías
4. **Editar contenido**: Seleccionar recurso → Editor central
5. **Previsualizar**: Panel derecho → WebKit automático
6. **Guardar cambios**: Ctrl+S o Archivo → Guardar

### Atajos de Teclado

- `Ctrl+N`: Nuevo libro
- `Ctrl+O`: Abrir libro
- `Ctrl+S`: Guardar
- `Ctrl+Shift+S`: Guardar como
- `Ctrl+F`: Búsqueda global
- `Ctrl+Shift+P`: Command palette
- `F11`: Pantalla completa

## 🤝 Contribuir

1. Fork del repositorio
2. Crear rama feature: `git checkout -b feature-nueva`
3. Commit cambios: `git commit -am 'Añadir feature'`
4. Push rama: `git push origin feature-nueva`
5. Crear Pull Request

### Pautas de Desarrollo

- Mantener independencia entre componentes
- Añadir tests para nuevas funcionalidades
- Seguir convenciones de código Python (PEP 8)
- Documentar funciones públicas
- Usar señales GObject para comunicación

## 📄 Licencia

GPL v3.0 - Ver archivo LICENSE para detalles.

## 🙏 Reconocimientos

- **ebooklib**: Librería Python para EPUB
- **GTK Team**: Toolkit de interfaz
- **GNOME**: libadwaita y WebKit
- **Python**: Lenguaje base del proyecto
