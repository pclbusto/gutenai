#!/usr/bin/env python3
"""
Script de configuración para Guten.AI
Organiza la estructura del proyecto y crea archivos necesarios
"""

import os
import sys
from pathlib import Path

def create_project_structure():
    """Crear estructura de directorios del proyecto"""
    
    print("🏗️  Configurando estructura del proyecto Guten.AI...")
    
    # Estructura de directorios
    directories = [
        "gutenai",
        "gutenai/core",
        "gutenai/components", 
        "gutenai/widgets",
        "gutenai/tests",
        "gutenai/resources",
        "gutenai/resources/icons",
        "gutenai/resources/css",
        "docs",
        "examples"
    ]
    
    # Crear directorios
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"📁 {directory}/")
    
    # Archivos __init__.py para módulos Python
    init_files = [
        "gutenai/__init__.py",
        "gutenai/core/__init__.py", 
        "gutenai/components/__init__.py",
        "gutenai/widgets/__init__.py",
        "gutenai/tests/__init__.py"
    ]
    
    for init_file in init_files:
        with open(init_file, 'w') as f:
            f.write('"""Guten.AI - Editor EPUB Modular"""\n')
        print(f"📄 {init_file}")
    
    return True

def create_main_files():
    """Crear archivos principales del proyecto"""
    
    files = {
        "requirements.txt": """# Guten.AI Dependencies
ebooklib>=0.18
PyGObject>=3.42.0
""",
        
        "gutenai/main.py": """#!/usr/bin/env python3
\"\"\"
Guten.AI - Aplicación Principal
\"\"\"

import sys
import os

# Añadir directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from components.integrated_app import main
    
    if __name__ == '__main__':
        sys.exit(main())
        
except ImportError as e:
    print(f"Error importando módulos: {e}")
    print("Asegúrate de tener instaladas las dependencias:")
    print("pip install -r requirements.txt")
    sys.exit(1)
""",

        "README.md": """# Guten.AI - Editor EPUB Modular

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
""",

        ".gitignore": """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Project specific
*.epub
temp/
tmp/
.guten/
""",

        "gutenai/run_component.py": """#!/usr/bin/env python3
\"\"\"
Script helper para ejecutar componentes independientemente
\"\"\"

import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Uso: python run_component.py <componente>")
        print("Componentes disponibles:")
        print("  sidebar_left    - Navegador de estructura EPUB")
        print("  editor_panel    - Editor central multimodo")
        print("  sidebar_right   - Previsualización WebKit")
        print("  integrated_app  - Aplicación completa integrada")
        return 1
    
    component = sys.argv[1]
    
    try:
        if component == "sidebar_left":
            from components.sidebar_left import test_sidebar
            return test_sidebar()
            
        elif component == "editor_panel":
            from components.editor_panel import test_editor
            return test_editor()
            
        elif component == "sidebar_right":
            from components.sidebar_right import test_preview
            return test_preview()
            
        elif component == "integrated_app":
            from components.integrated_app import main
            return main()
            
        else:
            print(f"Componente desconocido: {component}")
            return 1
            
    except ImportError as e:
        print(f"Error importando componente {component}: {e}")
        print("Asegúrate de estar en el directorio correcto y tener las dependencias instaladas.")
        return 1
    except Exception as e:
        print(f"Error ejecutando componente {component}: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
""",

        "setup.cfg": """[metadata]
name = guten-ai
version = 0.1.0
description = Editor EPUB modular con arquitectura de componentes independientes
long_description = file: README.md
long_description_content_type = text/markdown
url = https://github.com/guten-ai/guten
author = Equipo Guten.AI
author_email = dev@guten.ai
license = GPL-3.0
license_file = LICENSE
classifiers =
    Development Status :: 3 - Alpha
    Intended Audience :: Developers
    Intended Audience :: End Users/Desktop
    License :: OSI Approved :: GNU General Public License v3 (GPLv3)
    Operating System :: POSIX :: Linux
    Programming Language :: Python :: 3
    Programming Language :: Python :: 3.8
    Programming Language :: Python :: 3.9
    Programming Language :: Python :: 3.10
    Programming Language :: Python :: 3.11
    Topic :: Multimedia :: Graphics :: Editors
    Topic :: Text Processing :: Markup :: HTML
    Topic :: Text Processing :: Markup :: XML

[options]
packages = find:
python_requires = >=3.8
install_requires =
    ebooklib>=0.18
    PyGObject>=3.42.0

[options.packages.find]
where = .
include = gutenai*

[options.extras_require]
dev =
    pytest>=6.0
    black
    flake8
    mypy

[options.entry_points]
console_scripts =
    guten = gutenai.main:main
""",

        "Makefile": """# Guten.AI Makefile

.PHONY: help install run test clean components

help:
	@echo "Comandos disponibles:"
	@echo "  install     - Instalar dependencias"
	@echo "  run        - Ejecutar aplicación principal"
	@echo "  test       - Ejecutar tests"
	@echo "  components - Listar componentes disponibles"
	@echo "  clean      - Limpiar archivos temporales"
	@echo ""
	@echo "Componentes individuales:"
	@echo "  make sidebar-left    - Probar sidebar izquierdo"
	@echo "  make editor-panel    - Probar editor central"
	@echo "  make sidebar-right   - Probar sidebar derecho"
	@echo "  make integrated-app  - Probar app integrada"

install:
	pip install -r requirements.txt

run:
	cd gutenai && python main.py

test:
	cd gutenai && python -m pytest tests/

components:
	@echo "Componentes disponibles para testing individual:"
	@echo "  - sidebar_left: Navegador de estructura EPUB"
	@echo "  - editor_panel: Editor central multimodo"
	@echo "  - sidebar_right: Previsualización WebKit"
	@echo "  - integrated_app: Aplicación completa"

sidebar-left:
	cd gutenai && python run_component.py sidebar_left

editor-panel:
	cd gutenai && python run_component.py editor_panel

sidebar-right:
	cd gutenai && python run_component.py sidebar_right

integrated-app:
	cd gutenai && python run_component.py integrated_app

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.epub" -delete
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf temp/
	rm -rf tmp/
"""
    }
    
    # Crear archivos
    for file_path, content in files.items():
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"📄 {file_path}")
    
    return True

def create_test_files():
    """Crear archivos de prueba"""
    
    test_files = {
        "gutenai/tests/test_epub_manager.py": """#!/usr/bin/env python3
\"\"\"
Tests para EpubManager
\"\"\"

import unittest
import sys
import os

# Añadir path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.epub_manager import EpubManager, SignalManager
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False

@unittest.skipUnless(IMPORTS_AVAILABLE, "Módulos no disponibles")
class TestEpubManager(unittest.TestCase):
    
    def setUp(self):
        self.epub_manager = EpubManager()
        self.signal_manager = SignalManager()
    
    def test_create_new_book(self):
        \"\"\"Test creación de nuevo libro\"\"\"
        success = self.epub_manager.create_new_book("Test Book", "Test Author")
        self.assertTrue(success)
        self.assertEqual(self.epub_manager.book_title, "Test Book")
    
    def test_signal_manager(self):
        \"\"\"Test sistema de señales\"\"\"
        callback_called = False
        
        def test_callback(*args):
            nonlocal callback_called
            callback_called = True
        
        self.signal_manager.register_callback("test_signal", test_callback)
        self.signal_manager.emit_signal("test_signal")
        
        self.assertTrue(callback_called)

if __name__ == '__main__':
    unittest.main()
""",

        "gutenai/tests/test_components.py": """#!/usr/bin/env python3
\"\"\"
Tests para componentes UI
\"\"\"

import unittest
import sys
import os

# Añadir path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestComponents(unittest.TestCase):
    
    def test_imports(self):
        \"\"\"Test que los componentes se puedan importar\"\"\"
        try:
            from components import sidebar_left
            from components import editor_panel
            from components import sidebar_right
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Error importando componentes: {e}")

if __name__ == '__main__':
    unittest.main()
"""
    }
    
    for file_path, content in test_files.items():
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"🧪 {file_path}")
    
    return True

def check_dependencies():
    """Verificar dependencias del sistema"""
    
    print("🔍 Verificando dependencias...")
    
    dependencies = {
        "Python 3.8+": sys.version_info >= (3, 8),
        "PyGObject": True,
        "ebooklib": True,
    }
    
    # Verificar PyGObject
    try:
        import gi
        dependencies["PyGObject"] = True
        print("✅ PyGObject disponible")
    except ImportError:
        dependencies["PyGObject"] = False
        print("❌ PyGObject no encontrado")
    
    # Verificar ebooklib
    try:
        import ebooklib
        dependencies["ebooklib"] = True
        print("✅ ebooklib disponible")
    except ImportError:
        dependencies["ebooklib"] = False
        print("❌ ebooklib no encontrado")
    
    # Verificar GTK4
    try:
        gi.require_version('Gtk', '4.0')
        gi.require_version('Adw', '1')
        print("✅ GTK4 y libadwaita disponibles")
    except:
        print("⚠️  GTK4 o libadwaita no disponibles completamente")
    
    # Verificar WebKit (opcional)
    try:
        gi.require_version('WebKit', '6.0')
        print("✅ WebKit disponible")
    except:
        print("⚠️  WebKit no disponible (previsualización limitada)")
    
    # Verificar GtkSourceView (opcional)
    try:
        gi.require_version('GtkSource', '5')
        print("✅ GtkSourceView disponible")
    except:
        print("⚠️  GtkSourceView no disponible (resaltado limitado)")
    
    return all(dependencies.values())

def main():
    """Función principal del setup"""
    
    print("🚀 Configurando Guten.AI - Editor EPUB Modular")
    print("=" * 50)
    
    # Verificar si estamos en el directorio correcto
    if os.path.exists("gutenai") and not os.path.exists("setup.py"):
        print("⚠️  Parece que ya tienes una estructura de proyecto.")
        response = input("¿Quieres continuar y sobrescribir archivos? (y/N): ")
        if response.lower() not in ['y', 'yes', 'sí', 's']:
            print("❌ Configuración cancelada")
            return 1
    
    # Crear estructura
    print("\n📁 Creando estructura de directorios...")
    if not create_project_structure():
        print("❌ Error creando estructura")
        return 1
    
    print("\n📄 Creando archivos principales...")
    if not create_main_files():
        print("❌ Error creando archivos")
        return 1
    
    print("\n🧪 Creando archivos de prueba...")
    if not create_test_files():
        print("❌ Error creando tests")
        return 1
    
    print("\n🔍 Verificando dependencias...")
    check_dependencies()
    
    print("\n✅ ¡Configuración completada!")
    print("\n🚀 Para comenzar:")
    print("1. Instalar dependencias:")
    print("   pip install -r requirements.txt")
    print("\n2. Ejecutar aplicación:")
    print("   cd gutenai && python main.py")
    print("\n3. O probar componentes individuales:")
    print("   cd gutenai && python run_component.py sidebar_left")
    print("   cd gutenai && python run_component.py editor_panel")
    print("   cd gutenai && python run_component.py sidebar_right")
    print("   cd gutenai && python run_component.py integrated_app")
    print("\n4. Usar Makefile:")
    print("   make install")
    print("   make run")
    print("   make sidebar-left")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())