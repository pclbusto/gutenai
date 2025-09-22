"""
Guten.AI - Core EPUB Manager
Gestor central del estado EPUB y API unificada para componentes
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import GObject, Gio
from typing import Optional, Dict, Any, List, Tuple, Union
import os
import json
import tempfile
import shutil
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import ebooklib
    from ebooklib import epub
    EBOOKLIB_AVAILABLE = True
except ImportError:
    logger.warning("ebooklib no está disponible. Algunas funcionalidades estarán limitadas.")
    EBOOKLIB_AVAILABLE = False
    # Mock classes para desarrollo sin ebooklib
    class epub:
        class EpubBook:
            pass
        class EpubHtml:
            pass
        class EpubItem:
            pass

class EpubResourceType:
    """Tipos de recursos EPUB"""
    DOCUMENT = "document"
    STYLE = "style"
    IMAGE = "image"
    FONT = "font"
    AUDIO = "audio"
    VIDEO = "video"
    OTHER = "other"

class EpubResource:
    """Wrapper para recursos EPUB con interfaz unificada"""
    
    def __init__(self, epub_item: Any, resource_type: str):
        self.epub_item = epub_item
        self.resource_type = resource_type
        self._cached_content: Optional[Union[str, bytes]] = None
        
    @property
    def id(self) -> str:
        """ID único del recurso"""
        if hasattr(self.epub_item, 'get_id'):
            return self.epub_item.get_id()
        elif hasattr(self.epub_item, 'file_name'):
            return self.epub_item.file_name
        else:
            return str(self.epub_item)
    
    @property
    def file_name(self) -> str:
        """Nombre del archivo"""
        if hasattr(self.epub_item, 'file_name'):
            return self.epub_item.file_name
        elif hasattr(self.epub_item, 'get_name'):
            return self.epub_item.get_name()
        else:
            return self.id
    
    @property
    def title(self) -> str:
        """Título legible del recurso"""
        if hasattr(self.epub_item, 'title'):
            return self.epub_item.title
        elif hasattr(self.epub_item, 'get_title'):
            return self.epub_item.get_title()
        else:
            # Generar título basado en el nombre del archivo
            name = self.file_name
            if '/' in name:
                name = name.split('/')[-1]
            if '.' in name:
                name = os.path.splitext(name)[0]
            return name.replace('_', ' ').replace('-', ' ').title()
    
    @property
    def media_type(self) -> str:
        """Tipo MIME del recurso"""
        if hasattr(self.epub_item, 'media_type'):
            return self.epub_item.media_type
        elif hasattr(self.epub_item, 'get_type'):
            # Mapear tipos ebooklib a MIME
            type_map = {
                9: 'application/xhtml+xml',  # ITEM_DOCUMENT
                10: 'text/css',              # ITEM_STYLE
                3: 'image/jpeg',             # ITEM_IMAGE (generic)
            }
            return type_map.get(self.epub_item.get_type(), 'application/octet-stream')
        else:
            # Determinar por extensión
            ext = os.path.splitext(self.file_name)[1].lower()
            mime_map = {
                '.html': 'text/html',
                '.xhtml': 'application/xhtml+xml',
                '.css': 'text/css',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.svg': 'image/svg+xml',
                '.ttf': 'font/ttf',
                '.otf': 'font/otf',
                '.woff': 'font/woff',
                '.woff2': 'font/woff2',
                '.mp3': 'audio/mpeg',
                '.ogg': 'audio/ogg',
                '.wav': 'audio/wav',
                '.mp4': 'video/mp4',
                '.webm': 'video/webm',
            }
            return mime_map.get(ext, 'application/octet-stream')
    
    def get_content(self) -> Union[str, bytes, None]:
        """Obtener contenido del recurso"""
        if self._cached_content is not None:
            return self._cached_content
        
        if not hasattr(self.epub_item, 'get_content'):
            return None
        
        try:
            content = self.epub_item.get_content()
            
            # Si es contenido de texto, decodificar
            if isinstance(content, bytes) and self.resource_type in [
                EpubResourceType.DOCUMENT, EpubResourceType.STYLE
            ]:
                try:
                    content = content.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        content = content.decode('latin-1')
                    except UnicodeDecodeError:
                        content = content.decode('utf-8', errors='ignore')
            
            self._cached_content = content
            return content
            
        except Exception as e:
            logger.error(f"Error obteniendo contenido de {self.file_name}: {e}")
            return None
    
    def set_content(self, content: Union[str, bytes]) -> bool:
        """Establecer contenido del recurso"""
        if not hasattr(self.epub_item, 'set_content'):
            return False
        
        try:
            # Convertir a bytes si es necesario
            if isinstance(content, str):
                content = content.encode('utf-8')
            
            self.epub_item.set_content(content)
            self._cached_content = content
            return True
            
        except Exception as e:
            logger.error(f"Error estableciendo contenido de {self.file_name}: {e}")
            return False
    
    def get_size(self) -> int:
        """Obtener tamaño del recurso en bytes"""
        content = self.get_content()
        if content is None:
            return 0
        
        if isinstance(content, str):
            return len(content.encode('utf-8'))
        else:
            return len(content)
    
    def get_metadata(self) -> Dict[str, Any]:
        """Obtener metadatos del recurso"""
        metadata = {
            'id': self.id,
            'file_name': self.file_name,
            'title': self.title,
            'media_type': self.media_type,
            'resource_type': self.resource_type,
            'size': self.get_size(),
        }
        
        # Metadatos específicos por tipo
        if self.resource_type == EpubResourceType.DOCUMENT:
            content = self.get_content()
            if content and isinstance(content, str):
                # Análisis básico de HTML
                import re
                metadata.update({
                    'word_count': len(content.split()),
                    'character_count': len(content),
                    'heading_count': len(re.findall(r'<h[1-6]', content, re.IGNORECASE)),
                    'paragraph_count': len(re.findall(r'<p\b', content, re.IGNORECASE)),
                    'image_count': len(re.findall(r'<img\b', content, re.IGNORECASE)),
                    'link_count': len(re.findall(r'<a\b', content, re.IGNORECASE)),
                })
        
        elif self.resource_type == EpubResourceType.STYLE:
            content = self.get_content()
            if content and isinstance(content, str):
                # Análisis básico de CSS
                import re
                selectors = len(re.findall(r'[^{}]+\s*{', content))
                properties = len(re.findall(r'[^:]+:[^;]+;', content))
                metadata.update({
                    'selector_count': selectors,
                    'property_count': properties,
                })
        
        return metadata

class SignalManager(GObject.Object):
    """
    Gestor de comunicación entre componentes
    Sistema de callbacks para eventos inter-componente
    """
    
    def __init__(self):
        super().__init__()
        self._callbacks: Dict[str, List[callable]] = {}
        self._signal_history: List[Tuple[str, Any]] = []
        self.max_history = 100
    
    def register_callback(self, signal_name: str, callback: callable, priority: int = 0):
        """
        Registrar callback para una señal
        
        Args:
            signal_name: Nombre de la señal
            callback: Función callback
            priority: Prioridad (mayor número = mayor prioridad)
        """
        if signal_name not in self._callbacks:
            self._callbacks[signal_name] = []
        
        # Insertar manteniendo orden por prioridad
        inserted = False
        for i, (existing_callback, existing_priority) in enumerate(self._callbacks[signal_name]):
            if priority > existing_priority:
                self._callbacks[signal_name].insert(i, (callback, priority))
                inserted = True
                break
        
        if not inserted:
            self._callbacks[signal_name].append((callback, priority))
        
        logger.debug(f"Callback registrado para señal '{signal_name}' con prioridad {priority}")
    
    def unregister_callback(self, signal_name: str, callback: callable):
        """Desregistrar callback"""
        if signal_name in self._callbacks:
            self._callbacks[signal_name] = [
                (cb, prio) for cb, prio in self._callbacks[signal_name] 
                if cb != callback
            ]
    
    def emit_signal(self, signal_name: str, *args, **kwargs):
        """
        Emitir señal a todos los callbacks registrados
        
        Args:
            signal_name: Nombre de la señal
            *args, **kwargs: Argumentos para los callbacks
        """
        # Registrar en historial
        self._signal_history.append((signal_name, args))
        if len(self._signal_history) > self.max_history:
            self._signal_history.pop(0)
        
        logger.debug(f"Emitiendo señal '{signal_name}' con args: {args}")
        
        if signal_name in self._callbacks:
            for callback, priority in self._callbacks[signal_name]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error en callback para señal '{signal_name}': {e}")
                    # Continuar con otros callbacks aunque uno falle
    
    def get_signal_history(self) -> List[Tuple[str, Any]]:
        """Obtener historial de señales"""
        return self._signal_history.copy()
    
    def clear_callbacks(self, signal_name: Optional[str] = None):
        """Limpiar callbacks"""
        if signal_name:
            self._callbacks.pop(signal_name, None)
        else:
            self._callbacks.clear()

class EpubManager(GObject.Object):
    """
    Gestor central del EPUB - API unificada para todos los componentes
    Maneja el estado del libro y proporciona interfaz consistente
    """
    
    __gsignals__ = {
        'book-loaded': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        'book-closed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'resource-changed': (GObject.SignalFlags.RUN_FIRST, None, (str, object)),
        'resource-added': (GObject.SignalFlags.RUN_FIRST, None, (str, object)),
        'resource-removed': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'resource-renamed': (GObject.SignalFlags.RUN_FIRST, None, (str, str)),  # old_id, new_id
        'structure-updated': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        'content-modified': (GObject.SignalFlags.RUN_FIRST, None, (str, str)),  # resource_id, content
        'metadata-changed': (GObject.SignalFlags.RUN_FIRST, None, (str, object)),  # key, value
        'book-saved': (GObject.SignalFlags.RUN_FIRST, None, (str,)),  # file_path
        'error-occurred': (GObject.SignalFlags.RUN_FIRST, None, (str, str)),  # error_type, message
    }
    
    def __init__(self):
        super().__init__()
        
        # Estado del libro
        self._current_book: Optional[Any] = None
        self._current_resource_id: Optional[str] = None
        self._book_path: Optional[str] = None
        self._is_modified: bool = False
        
        # Cache de recursos
        self._resources_cache: Dict[str, List[EpubResource]] = {}
        self._resources_by_id: Dict[str, EpubResource] = {}
        
        # Configuración
        self._auto_save_enabled: bool = False
        self._auto_save_interval: int = 30  # segundos
        self._auto_save_timeout_id: Optional[int] = None
        
        # Historial de cambios (para undo/redo futuro)
        self._change_history: List[Dict[str, Any]] = []
        self.max_history = 50
        
        # Directorio temporal para recursos
        self._temp_dir: Optional[str] = None
        
    def __del__(self):
        """Cleanup al destruir el objeto"""
        self._cleanup_temp_dir()
    
    # ========================================
    # PROPIEDADES PÚBLICAS
    # ========================================
    
    @property
    def current_book(self) -> Optional[Any]:
        """Libro EPUB actual"""
        return self._current_book
    
    @property
    def current_resource_id(self) -> Optional[str]:
        """ID del recurso actualmente seleccionado"""
        return self._current_resource_id
    
    @property
    def book_path(self) -> Optional[str]:
        """Ruta del archivo EPUB"""
        return self._book_path
    
    @property
    def is_modified(self) -> bool:
        """Si el libro tiene cambios sin guardar"""
        return self._is_modified
    
    @property
    def book_title(self) -> str:
        """Título del libro actual"""
        if not self._current_book:
            return "Ningún libro cargado"
        
        try:
            if hasattr(self._current_book, 'get_metadata'):
                metadata = self._current_book.get_metadata('DC', 'title')
                if metadata and len(metadata) > 0:
                    return metadata[0][0]
            elif hasattr(self._current_book, 'title'):
                return self._current_book.title
        except Exception as e:
            logger.warning(f"Error obteniendo título: {e}")
        
        return "Sin título"
    
    @property
    def book_author(self) -> str:
        """Autor del libro actual"""
        if not self._current_book:
            return ""
        
        try:
            if hasattr(self._current_book, 'get_metadata'):
                metadata = self._current_book.get_metadata('DC', 'creator')
                if metadata and len(metadata) > 0:
                    return metadata[0][0]
        except Exception as e:
            logger.warning(f"Error obteniendo autor: {e}")
        
        return "Autor desconocido"
    
    @property
    def book_language(self) -> str:
        """Idioma del libro actual"""
        if not self._current_book:
            return ""
        
        try:
            if hasattr(self._current_book, 'get_metadata'):
                metadata = self._current_book.get_metadata('DC', 'language')
                if metadata and len(metadata) > 0:
                    return metadata[0][0]
        except Exception as e:
            logger.warning(f"Error obteniendo idioma: {e}")
        
        return "es"
    
    # ========================================
    # GESTIÓN DE LIBROS
    # ========================================
    
    def create_new_book(self, title: str = "Nuevo Libro", author: str = "Autor", 
                       language: str = "es") -> bool:
        """
        Crear un nuevo libro EPUB
        
        Args:
            title: Título del libro
            author: Autor del libro
            language: Idioma del libro
            
        Returns:
            True si se creó exitosamente
        """
        if not EBOOKLIB_AVAILABLE:
            self.emit('error-occurred', 'dependency', 'ebooklib no está disponible')
            return False
        
        try:
            # Crear libro vacío
            book = epub.EpubBook()
            book.set_identifier(f'guten-book-{hash(title)}')
            book.set_title(title)
            book.set_language(language)
            book.add_author(author)
            
            # Añadir capítulo inicial
            intro_chapter = epub.EpubHtml(
                title='Introducción',
                file_name='intro.xhtml',
                lang=language
            )
            intro_chapter.content = f'''<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Introducción</title>
</head>
<body>
    <h1>{title}</h1>
    <p>Comienza a escribir tu libro aquí...</p>
</body>
</html>'''
            
            book.add_item(intro_chapter)
            
            # Añadir CSS básico
            style = epub.EpubItem(
                uid="default_style",
                file_name="style/default.css",
                media_type="text/css",
                content="""
body {
    font-family: Georgia, serif;
    line-height: 1.6;
    margin: 2em;
    color: #333;
}

h1, h2, h3, h4, h5, h6 {
    color: #2c3e50;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
}

p {
    margin-bottom: 1em;
    text-align: justify;
}

blockquote {
    background: #f9f9f9;
    border-left: 4px solid #ccc;
    margin: 1em 0;
    padding: 0.5em 1em;
    font-style: italic;
}
"""
            )
            book.add_item(style)
            
            # Configurar TOC y spine
            book.toc = (epub.Link("intro.xhtml", "Introducción", "intro"),)
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            book.spine = ['nav', intro_chapter]
            
            # Cargar libro
            self._load_book_object(book)
            
            logger.info(f"Nuevo libro creado: {title}")
            return True
            
        except Exception as e:
            logger.error(f"Error creando nuevo libro: {e}")
            self.emit('error-occurred', 'creation', str(e))
            return False
    
    def load_book(self, file_path: str) -> bool:
        """
        Cargar un archivo EPUB
        
        Args:
            file_path: Ruta al archivo EPUB
            
        Returns:
            True si se cargó exitosamente
        """
        if not EBOOKLIB_AVAILABLE:
            self.emit('error-occurred', 'dependency', 'ebooklib no está disponible')
            return False
        
        if not os.path.exists(file_path):
            self.emit('error-occurred', 'file_not_found', f'Archivo no encontrado: {file_path}')
            return False
        
        try:
            book = epub.read_epub(file_path)
            self._book_path = file_path
            self._load_book_object(book)
            
            logger.info(f"Libro cargado: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error cargando libro {file_path}: {e}")
            self.emit('error-occurred', 'loading', str(e))
            return False
    
    def _load_book_object(self, book: Any):
        """Cargar objeto libro en el manager"""
        # Cerrar libro anterior si existe
        if self._current_book:
            self.close_book()
        
        self._current_book = book
        self._is_modified = False
        self._current_resource_id = None
        
        # Limpiar y reconstruir cache
        self._resources_cache.clear()
        self._resources_by_id.clear()
        self._build_resources_cache()
        
        # Configurar directorio temporal
        self._setup_temp_dir()
        
        # Emitir señal
        self.emit('book-loaded', book)
    
    def close_book(self):
        """Cerrar libro actual"""
        if self._current_book:
            # Limpiar estado
            self._current_book = None
            self._current_resource_id = None
            self._book_path = None
            self._is_modified = False
            
            # Limpiar caches
            self._resources_cache.clear()
            self._resources_by_id.clear()
            self._change_history.clear()
            
            # Limpiar directorio temporal
            self._cleanup_temp_dir()
            
            # Emitir señal
            self.emit('book-closed')
            
            logger.info("Libro cerrado")
    
    def save_book(self, file_path: Optional[str] = None) -> bool:
        """
        Guardar el libro EPUB
        
        Args:
            file_path: Ruta donde guardar (None para usar ruta actual)
            
        Returns:
            True si se guardó exitosamente
        """
        if not self._current_book:
            self.emit('error-occurred', 'no_book', 'No hay libro para guardar')
            return False
        
        if not EBOOKLIB_AVAILABLE:
            self.emit('error-occurred', 'dependency', 'ebooklib no está disponible')
            return False
        
        save_path = file_path or self._book_path
        if not save_path:
            self.emit('error-occurred', 'no_path', 'No se especificó ruta de guardado')
            return False
        
        try:
            # Asegurar que el directorio existe
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # Guardar libro
            epub.write_epub(save_path, self._current_book)
            
            # Actualizar estado
            self._book_path = save_path
            self._is_modified = False
            
            # Emitir señal
            self.emit('book-saved', save_path)
            
            logger.info(f"Libro guardado: {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error guardando libro: {e}")
            self.emit('error-occurred', 'saving', str(e))
            return False
    
    # ========================================
    # GESTIÓN DE RECURSOS
    # ========================================
    
    def _build_resources_cache(self):
        """Construir caché de recursos organizados por categorías"""
        if not self._current_book:
            return
        
        # Inicializar categorías
        self._resources_cache = {
            EpubResourceType.DOCUMENT: [],
            EpubResourceType.STYLE: [],
            EpubResourceType.IMAGE: [],
            EpubResourceType.FONT: [],
            EpubResourceType.AUDIO: [],
            EpubResourceType.VIDEO: [],
            EpubResourceType.OTHER: []
        }
        
        # Categorizar recursos
        for item in self._current_book.get_items():
            resource_type = self._determine_resource_type(item)
            epub_resource = EpubResource(item, resource_type)
            
            self._resources_cache[resource_type].append(epub_resource)
            self._resources_by_id[epub_resource.id] = epub_resource
        
        # Emitir señal de estructura actualizada
        self.emit('structure-updated', self._resources_cache)
        
        logger.debug(f"Cache de recursos actualizado: {len(self._resources_by_id)} recursos")
    
    def _determine_resource_type(self, item: Any) -> str:
        """Determinar el tipo de recurso"""
        if not EBOOKLIB_AVAILABLE:
            return EpubResourceType.OTHER
        
        try:
            # Por tipo ebooklib
            if hasattr(item, 'get_type'):
                epub_type = item.get_type()
                if epub_type == ebooklib.ITEM_DOCUMENT:
                    return EpubResourceType.DOCUMENT
                elif epub_type == ebooklib.ITEM_STYLE:
                    return EpubResourceType.STYLE
                elif epub_type == ebooklib.ITEM_IMAGE:
                    return EpubResourceType.IMAGE
            
            # Por nombre de archivo
            if hasattr(item, 'file_name'):
                file_name = item.file_name.lower()
                
                if file_name.endswith(('.html', '.xhtml', '.htm')):
                    return EpubResourceType.DOCUMENT
                elif file_name.endswith('.css'):
                    return EpubResourceType.STYLE
                elif file_name.endswith(('.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp')):
                    return EpubResourceType.IMAGE
                elif file_name.endswith(('.ttf', '.otf', '.woff', '.woff2')):
                    return EpubResourceType.FONT
                elif file_name.endswith(('.mp3', '.ogg', '.wav', '.m4a')):
                    return EpubResourceType.AUDIO
                elif file_name.endswith(('.mp4', '.webm', '.ogv', '.m4v')):
                    return EpubResourceType.VIDEO
            
        except Exception as e:
            logger.warning(f"Error determinando tipo de recurso: {e}")
        
        return EpubResourceType.OTHER
    
    def get_resources_by_category(self, category: str) -> List[EpubResource]:
        """
        Obtener recursos por categoría
        
        Args:
            category: Categoría de recurso
            
        Returns:
            Lista de recursos de la categoría
        """
        return self._resources_cache.get(category, []).copy()
    
    def get_all_categories(self) -> Dict[str, List[EpubResource]]:
        """Obtener todas las categorías de recursos"""
        return {
            category: resources.copy() 
            for category, resources in self._resources_cache.items()
        }
    
    def get_resource(self, resource_id: str) -> Optional[EpubResource]:
        """
        Obtener recurso por ID
        
        Args:
            resource_id: ID del recurso
            
        Returns:
            Recurso o None si no existe
        """
        return self._resources_by_id.get(resource_id)
    
    def select_resource(self, resource_id: str, resource_obj: Optional[Any] = None):
        """
        Seleccionar un recurso para edición
        
        Args:
            resource_id: ID del recurso
            resource_obj: Objeto del recurso (opcional)
        """
        if resource_id not in self._resources_by_id:
            logger.warning(f"Recurso no encontrado: {resource_id}")
            return
        
        self._current_resource_id = resource_id
        resource = self._resources_by_id[resource_id]
        
        self.emit('resource-changed', resource_id, resource_obj or resource)
        
        logger.debug(f"Recurso seleccionado: {resource_id}")
    
    def get_resource_content(self, resource_id: str) -> Optional[Union[str, bytes]]:
        """
        Obtener contenido de un recurso
        
        Args:
            resource_id: ID del recurso
            
        Returns:
            Contenido del recurso o None
        """
        resource = self.get_resource(resource_id)
        if not resource:
            return None
        
        return resource.get_content()
    
    def update_resource_content(self, resource_id: str, content: Union[str, bytes]) -> bool:
        """
        Actualizar contenido de un recurso
        
        Args:
            resource_id: ID del recurso
            content: Nuevo contenido
            
        Returns:
            True si se actualizó exitosamente
        """
        resource = self.get_resource(resource_id)
        if not resource:
            return False
        
        # Guardar en historial para undo/redo futuro
        old_content = resource.get_content()
        self._add_to_history('content_change', {
            'resource_id': resource_id,
            'old_content': old_content,
            'new_content': content
        })
        
        # Actualizar contenido
        success = resource.set_content(content)
        if success:
            self._is_modified = True
            self.emit('content-modified', resource_id, content if isinstance(content, str) else "<binary>")
            
            # Auto-guardar si está habilitado
            if self._auto_save_enabled:
                self._schedule_auto_save()
        
        return success
    
    # ========================================
    # METADATOS
    # ========================================
    
    def get_book_metadata(self) -> Dict[str, Any]:
        """Obtener metadatos del libro"""
        if not self._current_book:
            return {}
        
        metadata = {
            'title': self.book_title,
            'author': self.book_author,
            'language': self.book_language,
            'file_path': self._book_path,
            'is_modified': self._is_modified,
            'resource_count': len(self._resources_by_id),
        }
        
        # Estadísticas por categoría
        for category, resources in self._resources_cache.items():
            metadata[f'{category}_count'] = len(resources)
        
        # Metadatos adicionales de ebooklib
        if hasattr(self._current_book, 'get_metadata'):
            try:
                # Dublin Core metadata
                dc_fields = ['identifier', 'title', 'creator', 'subject', 'description', 
                           'publisher', 'contributor', 'date', 'type', 'format', 
                           'source', 'language', 'relation', 'coverage', 'rights']
                
                for field in dc_fields:
                    try:
                        field_data = self._current_book.get_metadata('DC', field)
                        if field_data:
                            metadata[f'dc_{field}'] = [item[0] for item in field_data]
                    except:
                        continue
                
            except Exception as e:
                logger.warning(f"Error obteniendo metadatos DC: {e}")
        
        return metadata
    
    def update_book_metadata(self, key: str, value: Any) -> bool:
        """
        Actualizar metadatos del libro
        
        Args:
            key: Clave del metadato
            value: Nuevo valor
            
        Returns:
            True si se actualizó exitosamente
        """
        if not self._current_book:
            return False
        
        try:
            # Metadatos básicos
            if key == 'title':
                self._current_book.set_title(str(value))
            elif key == 'language':
                self._current_book.set_language(str(value))
            elif key == 'author':
                # Limpiar autores existentes y añadir nuevo
                if hasattr(self._current_book, 'add_author'):
                    # Esto es una simplificación - ebooklib maneja autores de forma más compleja
                    self._current_book.add_author(str(value))
            
            self._is_modified = True
            self.emit('metadata-changed', key, value)
            
            logger.debug(f"Metadato actualizado: {key} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"Error actualizando metadato {key}: {e}")
            return False
    
    # ========================================
    # GESTIÓN DE RECURSOS AVANZADA
    # ========================================
    
    def add_resource(self, file_path: str, resource_type: Optional[str] = None) -> Optional[str]:
        """
        Añadir nuevo recurso al libro
        
        Args:
            file_path: Ruta al archivo del recurso
            resource_type: Tipo forzado del recurso (opcional)
            
        Returns:
            ID del recurso añadido o None si falló
        """
        if not self._current_book or not os.path.exists(file_path):
            return None
        
        if not EBOOKLIB_AVAILABLE:
            self.emit('error-occurred', 'dependency', 'ebooklib no está disponible')
            return None
        
        try:
            file_name = os.path.basename(file_path)
            
            # Leer contenido del archivo
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Determinar tipo de recurso
            if not resource_type:
                resource_type = self._determine_resource_type_by_extension(file_name)
            
            # Crear item apropiado
            if resource_type == EpubResourceType.DOCUMENT:
                item = epub.EpubHtml(
                    title=os.path.splitext(file_name)[0],
                    file_name=file_name,
                    lang=self.book_language
                )
                item.content = content.decode('utf-8')
            else:
                # Determinar media type
                media_type = self._get_media_type_by_extension(file_name)
                item = epub.EpubItem(
                    uid=f"resource_{hash(file_name)}",
                    file_name=file_name,
                    media_type=media_type,
                    content=content
                )
            
            # Añadir al libro
            self._current_book.add_item(item)
            
            # Actualizar cache
            epub_resource = EpubResource(item, resource_type)
            self._resources_cache[resource_type].append(epub_resource)
            self._resources_by_id[epub_resource.id] = epub_resource
            
            self._is_modified = True
            self.emit('resource-added', epub_resource.id, epub_resource)
            self.emit('structure-updated', self._resources_cache)
            
            logger.info(f"Recurso añadido: {file_name}")
            return epub_resource.id
            
        except Exception as e:
            logger.error(f"Error añadiendo recurso {file_path}: {e}")
            self.emit('error-occurred', 'resource_add', str(e))
            return None
    
    def remove_resource(self, resource_id: str) -> bool:
        """
        Eliminar recurso del libro
        
        Args:
            resource_id: ID del recurso a eliminar
            
        Returns:
            True si se eliminó exitosamente
        """
        resource = self.get_resource(resource_id)
        if not resource or not self._current_book:
            return False
        
        try:
            # Eliminar del libro
            self._current_book.items.remove(resource.epub_item)
            
            # Eliminar del cache
            category = resource.resource_type
            if resource in self._resources_cache[category]:
                self._resources_cache[category].remove(resource)
            
            if resource_id in self._resources_by_id:
                del self._resources_by_id[resource_id]
            
            # Si era el recurso seleccionado, deseleccionar
            if self._current_resource_id == resource_id:
                self._current_resource_id = None
            
            self._is_modified = True
            self.emit('resource-removed', resource_id)
            self.emit('structure-updated', self._resources_cache)
            
            logger.info(f"Recurso eliminado: {resource_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error eliminando recurso {resource_id}: {e}")
            return False
    
    def rename_resource(self, resource_id: str, new_name: str) -> bool:
        """
        Renombrar recurso
        
        Args:
            resource_id: ID del recurso actual
            new_name: Nuevo nombre del archivo
            
        Returns:
            True si se renombró exitosamente
        """
        resource = self.get_resource(resource_id)
        if not resource:
            return False
        
        try:
            old_name = resource.file_name
            
            # Actualizar nombre en el item
            if hasattr(resource.epub_item, 'file_name'):
                resource.epub_item.file_name = new_name
            
            # Actualizar cache si cambió el ID
            new_id = resource.id  # El ID puede haber cambiado
            if new_id != resource_id:
                del self._resources_by_id[resource_id]
                self._resources_by_id[new_id] = resource
                
                # Actualizar recurso seleccionado
                if self._current_resource_id == resource_id:
                    self._current_resource_id = new_id
            
            self._is_modified = True
            self.emit('resource-renamed', resource_id, new_id)
            
            logger.info(f"Recurso renombrado: {old_name} -> {new_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error renombrando recurso {resource_id}: {e}")
            return False
    
    def _determine_resource_type_by_extension(self, file_name: str) -> str:
        """Determinar tipo de recurso por extensión"""
        ext = os.path.splitext(file_name)[1].lower()
        
        type_map = {
            '.html': EpubResourceType.DOCUMENT,
            '.xhtml': EpubResourceType.DOCUMENT,
            '.htm': EpubResourceType.DOCUMENT,
            '.css': EpubResourceType.STYLE,
            '.jpg': EpubResourceType.IMAGE,
            '.jpeg': EpubResourceType.IMAGE,
            '.png': EpubResourceType.IMAGE,
            '.gif': EpubResourceType.IMAGE,
            '.svg': EpubResourceType.IMAGE,
            '.webp': EpubResourceType.IMAGE,
            '.ttf': EpubResourceType.FONT,
            '.otf': EpubResourceType.FONT,
            '.woff': EpubResourceType.FONT,
            '.woff2': EpubResourceType.FONT,
            '.mp3': EpubResourceType.AUDIO,
            '.ogg': EpubResourceType.AUDIO,
            '.wav': EpubResourceType.AUDIO,
            '.m4a': EpubResourceType.AUDIO,
            '.mp4': EpubResourceType.VIDEO,
            '.webm': EpubResourceType.VIDEO,
            '.ogv': EpubResourceType.VIDEO,
            '.m4v': EpubResourceType.VIDEO,
        }
        
        return type_map.get(ext, EpubResourceType.OTHER)
    
    def _get_media_type_by_extension(self, file_name: str) -> str:
        """Obtener media type por extensión"""
        ext = os.path.splitext(file_name)[1].lower()
        
        mime_map = {
            '.html': 'text/html',
            '.xhtml': 'application/xhtml+xml',
            '.htm': 'text/html',
            '.css': 'text/css',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.webp': 'image/webp',
            '.ttf': 'font/ttf',
            '.otf': 'font/otf',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
            '.mp3': 'audio/mpeg',
            '.ogg': 'audio/ogg',
            '.wav': 'audio/wav',
            '.m4a': 'audio/mp4',
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.ogv': 'video/ogg',
            '.m4v': 'video/mp4',
        }
        
        return mime_map.get(ext, 'application/octet-stream')
    
    # ========================================
    # AUTO-GUARDADO
    # ========================================
    
    def set_auto_save(self, enabled: bool, interval: int = 30):
        """
        Configurar auto-guardado
        
        Args:
            enabled: Si habilitar auto-guardado
            interval: Intervalo en segundos
        """
        self._auto_save_enabled = enabled
        self._auto_save_interval = interval
        
        if not enabled and self._auto_save_timeout_id:
            GObject.source_remove(self._auto_save_timeout_id)
            self._auto_save_timeout_id = None
        
        logger.info(f"Auto-guardado {'habilitado' if enabled else 'deshabilitado'} (intervalo: {interval}s)")
    
    def _schedule_auto_save(self):
        """Programar auto-guardado"""
        if not self._auto_save_enabled or not self._book_path:
            return
        
        # Cancelar timeout anterior
        if self._auto_save_timeout_id:
            GObject.source_remove(self._auto_save_timeout_id)
        
        # Programar nuevo auto-guardado
        self._auto_save_timeout_id = GObject.timeout_add_seconds(
            self._auto_save_interval,
            self._auto_save_callback
        )
    
    def _auto_save_callback(self) -> bool:
        """Callback de auto-guardado"""
        if self._is_modified and self._book_path:
            success = self.save_book()
            if success:
                logger.info("Auto-guardado completado")
            else:
                logger.warning("Error en auto-guardado")
        
        self._auto_save_timeout_id = None
        return False  # No repetir
    
    # ========================================
    # HISTORIAL Y UTILIDADES
    # ========================================
    
    def _add_to_history(self, action_type: str, data: Dict[str, Any]):
        """Añadir acción al historial"""
        self._change_history.append({
            'type': action_type,
            'data': data,
            'timestamp': GObject.get_current_time()
        })
        
        # Limitar tamaño del historial
        if len(self._change_history) > self.max_history:
            self._change_history.pop(0)
    
    def get_change_history(self) -> List[Dict[str, Any]]:
        """Obtener historial de cambios"""
        return self._change_history.copy()
    
    def _setup_temp_dir(self):
        """Configurar directorio temporal"""
        if not self._temp_dir:
            self._temp_dir = tempfile.mkdtemp(prefix='guten_')
            logger.debug(f"Directorio temporal creado: {self._temp_dir}")
    
    def _cleanup_temp_dir(self):
        """Limpiar directorio temporal"""
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir)
                logger.debug(f"Directorio temporal limpiado: {self._temp_dir}")
            except Exception as e:
                logger.warning(f"Error limpiando directorio temporal: {e}")
            finally:
                self._temp_dir = None
    
    def get_temp_dir(self) -> Optional[str]:
        """Obtener directorio temporal"""
        if not self._temp_dir:
            self._setup_temp_dir()
        return self._temp_dir
    
    def export_resource_to_temp(self, resource_id: str) -> Optional[str]:
        """
        Exportar recurso a archivo temporal
        
        Args:
            resource_id: ID del recurso
            
        Returns:
            Ruta del archivo temporal o None
        """
        resource = self.get_resource(resource_id)
        if not resource:
            return None
        
        temp_dir = self.get_temp_dir()
        if not temp_dir:
            return None
        
        try:
            file_path = os.path.join(temp_dir, resource.file_name)
            content = resource.get_content()
            
            if content is None:
                return None
            
            # Crear directorio si es necesario
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Escribir archivo
            if isinstance(content, str):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            else:
                with open(file_path, 'wb') as f:
                    f.write(content)
            
            return file_path
            
        except Exception as e:
            logger.error(f"Error exportando recurso {resource_id} a temporal: {e}")
            return None
    
    # ========================================
    # BÚSQUEDA Y ANÁLISIS
    # ========================================
    
    def search_in_content(self, query: str, resource_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Buscar en el contenido de los recursos
        
        Args:
            query: Texto a buscar
            resource_types: Tipos de recursos donde buscar (None = todos)
            
        Returns:
            Lista de resultados con metadatos
        """
        if not query.strip():
            return []
        
        results = []
        search_types = resource_types or [EpubResourceType.DOCUMENT, EpubResourceType.STYLE]
        
        for resource_type in search_types:
            for resource in self._resources_cache.get(resource_type, []):
                content = resource.get_content()
                if not content or not isinstance(content, str):
                    continue
                
                # Búsqueda simple (case-insensitive)
                content_lower = content.lower()
                query_lower = query.lower()
                
                if query_lower in content_lower:
                    # Encontrar todas las ocurrencias
                    start = 0
                    matches = []
                    
                    while True:
                        pos = content_lower.find(query_lower, start)
                        if pos == -1:
                            break
                        
                        # Contexto alrededor del match
                        context_start = max(0, pos - 50)
                        context_end = min(len(content), pos + len(query) + 50)
                        context = content[context_start:context_end]
                        
                        matches.append({
                            'position': pos,
                            'context': context,
                            'line_number': content[:pos].count('\n') + 1
                        })
                        
                        start = pos + 1
                    
                    if matches:
                        results.append({
                            'resource_id': resource.id,
                            'resource_title': resource.title,
                            'resource_type': resource.resource_type,
                            'match_count': len(matches),
                            'matches': matches
                        })
        
        return results
    
    def get_book_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas del libro"""
        if not self._current_book:
            return {}
        
        stats = {
            'total_resources': len(self._resources_by_id),
            'total_size': 0,
            'word_count': 0,
            'character_count': 0,
        }
        
        # Estadísticas por categoría
        for category, resources in self._resources_cache.items():
            stats[f'{category}_count'] = len(resources)
            category_size = sum(resource.get_size() for resource in resources)
            stats[f'{category}_size'] = category_size
            stats['total_size'] += category_size
        
        # Estadísticas de texto
        for resource in self._resources_cache.get(EpubResourceType.DOCUMENT, []):
            content = resource.get_content()
            if content and isinstance(content, str):
                # Remover tags HTML para contar palabras
                import re
                text_only = re.sub(r'<[^>]+>', ' ', content)
                text_only = re.sub(r'\s+', ' ', text_only).strip()
                
                words = text_only.split()
                stats['word_count'] += len(words)
                stats['character_count'] += len(text_only)
        
        return stats

# =============================================
# FUNCIONES DE UTILIDAD
# =============================================

def create_epub_manager() -> EpubManager:
    """Factory function para crear EpubManager"""
    return EpubManager()

def create_signal_manager() -> SignalManager:
    """Factory function para crear SignalManager"""
    return SignalManager()

# =============================================
# PRUEBAS Y DEMO
# =============================================

def test_epub_manager():
    """Función de prueba para EpubManager"""
    print("🧪 Probando EpubManager...")
    
    # Crear managers
    epub_manager = create_epub_manager()
    signal_manager = create_signal_manager()
    
    # Registrar callbacks de prueba
    signal_manager.register_callback('book-loaded', 
        lambda book: print(f"📚 Libro cargado: {epub_manager.book_title}"))
    
    signal_manager.register_callback('resource-changed',
        lambda resource_id, resource_obj: print(f"📄 Recurso seleccionado: {resource_id}"))
    
    signal_manager.register_callback('content-modified',
        lambda resource_id, content: print(f"✏️ Contenido modificado: {resource_id}"))
    
    # Conectar señales del EpubManager al SignalManager
    epub_manager.connect('book-loaded', lambda manager, book: signal_manager.emit_signal('book-loaded', book))
    epub_manager.connect('resource-changed', lambda manager, rid, robj: signal_manager.emit_signal('resource-changed', rid, robj))
    epub_manager.connect('content-modified', lambda manager, rid, content: signal_manager.emit_signal('content-modified', rid, content))
    
    # Prueba 1: Crear nuevo libro
    print("\n1️⃣ Creando nuevo libro...")
    success = epub_manager.create_new_book("Libro de Prueba", "Autor de Prueba")
    print(f"   Resultado: {'✅' if success else '❌'}")
    
    if success:
        # Mostrar información del libro
        metadata = epub_manager.get_book_metadata()
        print(f"   Título: {metadata['title']}")
        print(f"   Autor: {metadata['author']}")
        print(f"   Recursos: {metadata['resource_count']}")
        
        # Mostrar categorías
        categories = epub_manager.get_all_categories()
        for category, resources in categories.items():
            if resources:
                print(f"   {category}: {len(resources)} recursos")
        
        # Prueba 2: Seleccionar recurso
        print("\n2️⃣ Seleccionando primer recurso de texto...")
        text_resources = epub_manager.get_resources_by_category(EpubResourceType.DOCUMENT)
        if text_resources:
            first_resource = text_resources[0]
            epub_manager.select_resource(first_resource.id, first_resource)
            
            # Obtener y mostrar contenido
            content = epub_manager.get_resource_content(first_resource.id)
            if content:
                print(f"   Contenido ({len(content)} caracteres):")
                print(f"   {content[:100]}...")
        
        # Prueba 3: Modificar contenido
        print("\n3️⃣ Modificando contenido...")
        if text_resources:
            new_content = """<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Introducción Modificada</title>
</head>
<body>
    <h1>Libro de Prueba</h1>
    <p>Este contenido ha sido <strong>modificado</strong> por la prueba del EpubManager.</p>
    <p>Timestamp: """ + str(GObject.get_current_time()) + """</p>
</body>
</html>"""
            
            success = epub_manager.update_resource_content(first_resource.id, new_content)
            print(f"   Actualización: {'✅' if success else '❌'}")
            print(f"   Modificado: {'✅' if epub_manager.is_modified else '❌'}")
        
        # Prueba 4: Estadísticas
        print("\n4️⃣ Estadísticas del libro...")
        stats = epub_manager.get_book_statistics()
        print(f"   Palabras: {stats.get('word_count', 0)}")
        print(f"   Caracteres: {stats.get('character_count', 0)}")
        print(f"   Tamaño total: {stats.get('total_size', 0)} bytes")
        
        # Prueba 5: Búsqueda
        print("\n5️⃣ Búsqueda en contenido...")
        results = epub_manager.search_in_content("modificado")
        print(f"   Resultados: {len(results)}")
        for result in results:
            print(f"   - {result['resource_title']}: {result['match_count']} coincidencias")
    
    print("\n✅ Pruebas completadas")

if __name__ == '__main__':
    test_epub_manager()