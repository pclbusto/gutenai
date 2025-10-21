#!/usr/bin/env python3
"""
Ejemplo de uso del wrapper de epubcheck
Muestra diferentes formas de usar la validación EPUB
"""

import sys
from pathlib import Path

# Agregar el directorio padre al path para importar módulos de GutenAI
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.epubcheck_wrapper import (
    EpubCheckWrapper, ValidationProfile, quick_validate, get_epub_info
)


def test_basic_validation():
    """Test básico de validación"""
    print("=== Test de validación básica ===")

    # Buscar un archivo EPUB de ejemplo
    epub_files = list(Path.cwd().glob("*.epub"))
    if not epub_files:
        print("No se encontraron archivos EPUB en el directorio actual")
        return

    epub_file = epub_files[0]
    print(f"Validando: {epub_file}")

    # Validación rápida
    is_valid, errors = quick_validate(epub_file)

    print(f"¿Es válido? {is_valid}")
    if errors:
        print("Errores encontrados:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("No se encontraron errores")


def test_detailed_validation():
    """Test detallado de validación con diferentes opciones"""
    print("\n=== Test de validación detallada ===")

    epub_files = list(Path.cwd().glob("*.epub"))
    if not epub_files:
        print("No se encontraron archivos EPUB en el directorio actual")
        return

    epub_file = epub_files[0]
    wrapper = EpubCheckWrapper()

    try:
        # Validación con perfil por defecto
        result = wrapper.validate_epub(
            epub_file,
            profile=ValidationProfile.DEFAULT,
            include_usage=True
        )

        print(f"Archivo: {result.checker.filename}")
        print(f"Versión EPUB: {result.publication.ePubVersion}")
        print(f"Título: {result.publication.title}")
        print(f"Idioma: {result.publication.language}")
        print(f"Caracteres: {result.publication.charsCount:,}")

        print(f"\nResultados de validación:")
        print(f"  Errores fatales: {result.checker.nFatal}")
        print(f"  Errores: {result.checker.nError}")
        print(f"  Advertencias: {result.checker.nWarning}")
        print(f"  Tiempo de validación: {result.checker.elapsedTime}ms")

        if result.messages:
            print(f"\nMensajes ({len(result.messages)}):")
            for msg in result.messages[:5]:  # Mostrar solo los primeros 5
                print(f"  [{msg.severity.value}] {msg.message}")

            if len(result.messages) > 5:
                print(f"  ... y {len(result.messages) - 5} mensajes más")

        # Estadísticas de archivos
        spine_items = [item for item in result.items if item.isSpineItem]
        css_items = [item for item in result.items if item.media_type == "text/css"]
        image_items = [item for item in result.items if item.media_type and item.media_type.startswith("image/")]

        print(f"\nEstadísticas de archivos:")
        print(f"  Total de archivos: {len(result.items)}")
        print(f"  Documentos en spine: {len(spine_items)}")
        print(f"  Archivos CSS: {len(css_items)}")
        print(f"  Imágenes: {len(image_items)}")

        # Fuentes embebidas
        if result.publication.embeddedFonts:
            print(f"  Fuentes embebidas: {len(result.publication.embeddedFonts)}")
            for font in result.publication.embeddedFonts[:3]:
                print(f"    - {font}")

        print(f"\n¿EPUB válido? {'SÍ' if result.is_valid else 'NO'}")

    except Exception as e:
        print(f"Error durante la validación: {e}")


def test_epub_info():
    """Test de obtención de información básica"""
    print("\n=== Test de información de EPUB ===")

    epub_files = list(Path.cwd().glob("*.epub"))
    if not epub_files:
        print("No se encontraron archivos EPUB en el directorio actual")
        return

    for epub_file in epub_files[:3]:  # Procesar hasta 3 archivos
        print(f"\nArchivo: {epub_file.name}")

        info = get_epub_info(epub_file)
        if info:
            print(f"  Título: {info.title or 'No especificado'}")
            print(f"  Autor(es): {', '.join(info.creator) if info.creator else 'No especificado'}")
            print(f"  Idioma: {info.language or 'No especificado'}")
            print(f"  Versión EPUB: {info.ePubVersion or 'No especificado'}")
            print(f"  Caracteres: {info.charsCount:,}")
            print(f"  ¿Tiene audio? {'Sí' if info.hasAudio else 'No'}")
            print(f"  ¿Tiene video? {'Sí' if info.hasVideo else 'No'}")
            print(f"  ¿Formato fijo? {'Sí' if info.hasFixedFormat else 'No'}")
        else:
            print("  No se pudo obtener información (posible error de validación)")


def test_different_profiles():
    """Test con diferentes perfiles de validación"""
    print("\n=== Test con diferentes perfiles ===")

    epub_files = list(Path.cwd().glob("*.epub"))
    if not epub_files:
        print("No se encontraron archivos EPUB en el directorio actual")
        return

    epub_file = epub_files[0]
    wrapper = EpubCheckWrapper()

    profiles = [
        (ValidationProfile.DEFAULT, "Por defecto"),
        (ValidationProfile.DICT, "Diccionarios"),
        (ValidationProfile.EDUPUB, "EDUPUB"),
        (ValidationProfile.IDX, "Índices"),
        (ValidationProfile.PREVIEW, "Vista previa")
    ]

    for profile, name in profiles:
        try:
            print(f"\nValidando con perfil '{name}'...")
            result = wrapper.validate_epub(epub_file, profile=profile)

            total_issues = result.checker.nFatal + result.checker.nError + result.checker.nWarning
            print(f"  Problemas encontrados: {total_issues}")
            print(f"  Tiempo: {result.checker.elapsedTime}ms")

        except Exception as e:
            print(f"  Error con perfil '{name}': {e}")


def main():
    """Función principal que ejecuta todos los tests"""
    print("Probando el wrapper de epubcheck para GutenAI\n")

    # Verificar que epubcheck esté disponible
    wrapper = EpubCheckWrapper()
    installed, version = wrapper.check_installation()

    if not installed:
        print(f"ERROR: {version}")
        print("Instala epubcheck y asegúrate de que esté en el PATH")
        return 1

    print(f"Usando {version}\n")

    # Ejecutar tests
    test_basic_validation()
    test_detailed_validation()
    test_epub_info()
    test_different_profiles()

    print("\n=== Tests completados ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())