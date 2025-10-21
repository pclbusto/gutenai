# Integración EpubCheck en GutenAI

Este documento describe la integración del validador epubcheck en GutenAI, proporcionando validación estándar de archivos EPUB.

## 🚀 Características

- **Wrapper completo** para epubcheck con API Python nativa
- **Parser estructurado** de resultados JSON de epubcheck
- **Interfaz GTK4** moderna para mostrar resultados de validación
- **Integración transparente** con el flujo de trabajo de GutenAI
- **Múltiples perfiles** de validación EPUB
- **Validación en tiempo real** durante la edición

## 📋 Requisitos

### Software requerido
- **epubcheck 5.3.0+** instalado en el sistema
- El comando `epubcheck` debe estar disponible en el PATH

### Verificar instalación
```bash
epubcheck --version
# Debería mostrar: EPUBCheck v5.3.0 o superior
```

## 🏗️ Arquitectura

### Componentes principales

1. **`utils/epubcheck_wrapper.py`** - Wrapper principal y parser
2. **`gtk_ui/epubcheck_dialog.py`** - Interfaz GTK4 para validación
3. **Integración en `actions.py`** - Acción de menú para validar
4. **`examples/test_epubcheck.py`** - Ejemplos de uso

### Clases principales

#### `EpubCheckWrapper`
```python
wrapper = EpubCheckWrapper()

# Validación simple
is_valid, errors = wrapper.validate_epub_simple("libro.epub")

# Validación completa
result = wrapper.validate_epub(
    "libro.epub",
    profile=ValidationProfile.DEFAULT,
    include_usage=True
)
```

#### `EpubCheckResult`
Estructura de datos que contiene:
- **`checker`** - Información del proceso de validación
- **`publication`** - Metadatos del EPUB
- **`messages`** - Lista de errores, advertencias y mensajes
- **`items`** - Información detallada de cada archivo

#### `EpubCheckDialog`
Interfaz GTK4 con:
- Selector de archivos EPUB
- Configuración de perfiles de validación
- Vista detallada de resultados
- Información de la publicación

## 🎯 Uso

### Desde la interfaz de GutenAI

1. **Menú → Herramientas → Validar EPUB** (`Ctrl+Shift+V`)
2. Si hay un proyecto abierto, valida automáticamente el EPUB generado
3. Si no hay proyecto, permite seleccionar un archivo EPUB externo

### API programática

#### Validación rápida
```python
from utils.epubcheck_wrapper import quick_validate

is_valid, errors = quick_validate("mi_libro.epub")
if not is_valid:
    for error in errors:
        print(f"Error: {error}")
```

#### Validación detallada
```python
from utils.epubcheck_wrapper import EpubCheckWrapper, ValidationProfile

wrapper = EpubCheckWrapper()
result = wrapper.validate_epub(
    "mi_libro.epub",
    profile=ValidationProfile.EDUPUB,
    include_usage=True,
    fail_on_warnings=False
)

print(f"EPUB válido: {result.is_valid}")
print(f"Errores: {result.checker.nError}")
print(f"Advertencias: {result.checker.nWarning}")
print(f"Título: {result.publication.title}")
```

#### Obtener información básica
```python
from utils.epubcheck_wrapper import get_epub_info

info = get_epub_info("mi_libro.epub")
if info:
    print(f"Título: {info.title}")
    print(f"Autor: {', '.join(info.creator)}")
    print(f"Idioma: {info.language}")
```

### Perfiles de validación

```python
from utils.epubcheck_wrapper import ValidationProfile

# Perfiles disponibles:
ValidationProfile.DEFAULT    # Validación estándar
ValidationProfile.DICT      # Diccionarios y Glosarios
ValidationProfile.EDUPUB    # EDUPUB (libros educativos)
ValidationProfile.IDX       # Índices
ValidationProfile.PREVIEW   # Vistas previas
```

## 🔧 Configuración

### Variables de entorno
- `EPUBCHECK_COMMAND` - Comando personalizado para epubcheck (por defecto: "epubcheck")

### Configuración del wrapper
```python
# Usar comando personalizado
wrapper = EpubCheckWrapper("/ruta/personalizada/epubcheck")

# Verificar instalación
installed, version = wrapper.check_installation()
if not installed:
    print(f"Error: {version}")
```

## 📊 Interpretación de resultados

### Estado de validación
```python
result = wrapper.validate_epub("libro.epub")

# ¿Es válido?
if result.is_valid:
    print("✓ EPUB VÁLIDO")
else:
    print("✗ EPUB INVÁLIDO")

# Tipos de problemas
print(f"Errores fatales: {result.checker.nFatal}")
print(f"Errores: {result.checker.nError}")
print(f"Advertencias: {result.checker.nWarning}")
```

### Mensajes de validación
```python
from utils.epubcheck_wrapper import MessageLevel

for message in result.messages:
    level = message.severity

    if level == MessageLevel.FATAL:
        print(f"💀 FATAL: {message.message}")
    elif level == MessageLevel.ERROR:
        print(f"❌ ERROR: {message.message}")
    elif level == MessageLevel.WARNING:
        print(f"⚠️  ADVERTENCIA: {message.message}")
    elif level == MessageLevel.USAGE:
        print(f"💡 USO: {message.message}")
```

### Información de la publicación
```python
pub = result.publication

print(f"Título: {pub.title}")
print(f"Autor(es): {', '.join(pub.creator)}")
print(f"Idioma: {pub.language}")
print(f"Versión EPUB: {pub.ePubVersion}")
print(f"Caracteres: {pub.charsCount:,}")
print(f"Documentos en spine: {pub.nSpines}")

# Características especiales
if pub.hasAudio:
    print("📢 Contiene audio")
if pub.hasVideo:
    print("🎥 Contiene video")
if pub.hasFixedFormat:
    print("📐 Formato fijo")
if pub.isScripted:
    print("📜 Contiene scripts")

# Fuentes embebidas
if pub.embeddedFonts:
    print(f"🔤 Fuentes: {', '.join(pub.embeddedFonts)}")
```

## 🐛 Resolución de problemas

### Errores comunes

#### "epubcheck no encontrado"
```bash
# Instalar epubcheck (Ubuntu/Debian)
sudo apt install epubcheck

# Verificar instalación
which epubcheck
epubcheck --version
```

#### "Timeout al ejecutar epubcheck"
```python
# Aumentar timeout para archivos grandes
wrapper = EpubCheckWrapper()
result = wrapper.validate_epub("libro_grande.epub")  # Timeout automático de 60s
```

#### "Error al parsear JSON"
```python
# Capturar errores de parsing
try:
    result = wrapper.validate_epub("libro.epub")
except json.JSONDecodeError as e:
    print(f"Error en salida de epubcheck: {e}")
except subprocess.CalledProcessError as e:
    print(f"Error ejecutando epubcheck: {e}")
```

### Logs de depuración

```python
import logging

# Configurar logging para ver detalles
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('utils.epubcheck_wrapper')

# El wrapper mostrará comandos ejecutados
wrapper = EpubCheckWrapper()
result = wrapper.validate_epub("libro.epub")
```

## 🧪 Tests y ejemplos

### Ejecutar tests
```bash
# Test completo con archivo de ejemplo
python examples/test_epubcheck.py

# Test del wrapper directamente
python utils/epubcheck_wrapper.py libro.epub
```

### Test desde la interfaz
```bash
# Abrir diálogo de validación independiente
python gtk_ui/epubcheck_dialog.py [archivo.epub]
```

## 🔄 Integración con flujo de trabajo

### Validación automática en exportación
La validación puede integrarse en el proceso de exportación:

```python
# En el futuro, podría añadirse:
def export_and_validate(self, output_path):
    # Exportar EPUB
    self.core.export_epub(output_path)

    # Validar automáticamente
    wrapper = EpubCheckWrapper()
    result = wrapper.validate_epub(output_path)

    if result.is_valid:
        self.show_info("EPUB exportado y validado correctamente")
    else:
        self.show_warning(f"EPUB exportado con {result.total_issues} problemas")
```

### Validación en tiempo de desarrollo
```python
# Validar durante la edición (futuro)
def on_resource_save(self, resource_href):
    # Guardar recurso
    self.core.save_resource(resource_href)

    # Validación incremental (si se implementa)
    # quick_check_resource(resource_href)
```

## 📚 Documentación adicional

- **EpubCheck oficial**: https://github.com/w3c/epubcheck
- **Especificación EPUB 3**: https://www.w3.org/publishing/epub3/
- **GTK4 Documentation**: https://docs.gtk.org/gtk4/

## 🤝 Contribuir

Para mejoras en la integración de epubcheck:

1. Reportar bugs en el wrapper o parser
2. Sugerir nuevas características para la interfaz
3. Mejorar la interpretación de mensajes
4. Añadir más perfiles de validación personalizados

El código está diseñado para ser extensible y mantenible.