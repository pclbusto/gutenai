#!/usr/bin/env python3
"""Instala GutenAI: iconos, .desktop, venv y dependencias."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

TARGET_BASE = Path.home() / ".local" / "share" / "icons" / "hicolor"
DESKTOP_TARGET = Path.home() / ".local" / "share" / "applications"
PNG_SIZES = (128, 64)


def require_pillow():
    """Carga Pillow o sugiere instalarlo si falta."""
    try:
        from PIL import Image, ImageOps  # type: ignore
    except ImportError as exc:
        print(
            "Pillow no está instalado. Ejecutá:\n"
            "  pip install Pillow\n"
            "(usando tu entorno virtual si corresponde)."
        )
        raise SystemExit(exc) from exc
    return Image, ImageOps


def install_pngs(source: Path, Image, ImageOps) -> None:
    """Genera variantes PNG (128 y 64) y las copia al tema hicolor."""
    if not source.exists():
        raise SystemExit(f"No se encontró el icono base: {source}")

    # Lista de nombres de iconos a instalar
    icon_names = ["gutenai", "gutenai.com", "com.gutenai.editor"]

    for size in PNG_SIZES:
        target_dir = TARGET_BASE / f"{size}x{size}" / "apps"
        target_dir.mkdir(parents=True, exist_ok=True)

        with Image.open(source) as img:
            icon = ImageOps.fit(img.convert("RGBA"), (size, size), method=Image.LANCZOS)

            # Instalar con ambos nombres
            for icon_name in icon_names:
                target_path = target_dir / f"{icon_name}.png"
                icon.save(target_path, format="PNG")
                print(f"✔ Icono {icon_name} {size}x{size} instalado en {target_path}")


def install_svg(source: Path) -> None:
    """Copia el SVG al tema hicolor."""
    if not source.exists():
        print(f"⚠ No se encontró {source}; se omite la copia del SVG.")
        return

    target_dir = TARGET_BASE / "scalable" / "apps"
    target_dir.mkdir(parents=True, exist_ok=True)

    # Lista de nombres de iconos a instalar
    icon_names = ["gutenai", "gutenai.com", "com.gutenai.editor"]

    # Instalar con todos los nombres
    for icon_name in icon_names:
        target_path = target_dir / f"{icon_name}.svg"
        shutil.copy2(source, target_path)
        print(f"✔ Icono SVG {icon_name} instalado en {target_path}")


def refresh_icon_cache() -> None:
    """Actualiza la cache de iconos si la utilidad está disponible."""
    helper = shutil.which("gtk4-update-icon-cache") or shutil.which("gtk-update-icon-cache")
    if not helper:
        print("ℹ No se encontró gtk4-update-icon-cache; omito refrescar la cache.")
        return

    # Asegura que exista un index.theme para que update-icon-cache funcione
    index_theme = TARGET_BASE / "index.theme"
    if not index_theme.exists():
        system_index = Path("/usr/share/icons/hicolor/index.theme")
        if system_index.exists():
            try:
                shutil.copy2(system_index, index_theme)
                print(f"✔ Copiado {system_index} a {index_theme}")
            except Exception as exc:
                print(f"⚠ Advertencia: no se pudo copiar index.theme: {exc}")
        else:
            print("⚠ Advertencia: No se encontró index.theme en el sistema, la actualización puede fallar.")

    if not index_theme.exists():
         print("⚠ Saltando gtk-update-icon-cache porque falta index.theme local.")
         return

    try:
        subprocess.run([helper, str(TARGET_BASE)], check=True)
        print("✔ Cache de iconos actualizada.")
    except subprocess.CalledProcessError as exc:
        print(f"⚠ No se pudo actualizar la cache de iconos: {exc}")


def setup_venv(repo_root: Path) -> Path:
    """Crea el venv si no existe y retorna la ruta al python del venv."""
    venv_dir = repo_root / ".venv"
    venv_python = venv_dir / "bin" / "python3"

    if not venv_dir.exists():
        print("→ Creando entorno virtual...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        print("✔ Entorno virtual creado en .venv/")
    else:
        print("✔ Entorno virtual ya existe en .venv/")

    return venv_python


def install_requirements(venv_python: Path, repo_root: Path) -> None:
    """Instala los requirements.txt en el venv."""
    requirements = repo_root / "requirements.txt"

    if not requirements.exists():
        print("⚠ No se encontró requirements.txt, saltando instalación de dependencias.")
        return

    print("→ Instalando dependencias desde requirements.txt...")
    try:
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-r", str(requirements)],
            check=True,
            capture_output=True,
            text=True
        )
        print("✔ Dependencias instaladas correctamente.")
    except subprocess.CalledProcessError as exc:
        print(f"⚠ Error al instalar dependencias: {exc}")
        print(exc.stderr)


def update_shell_script(repo_root: Path) -> None:
    """Actualiza las rutas en run_gutenai.sh con la ruta absoluta del proyecto."""
    script_path = repo_root / "run_gutenai.sh"

    if not script_path.exists():
        print(f"⚠ No se encontró {script_path}")
        return

    content = script_path.read_text()

    # Reemplazar la ruta de cd con la ruta actual
    new_content = content.replace(
        'cd "/home/pedro/Documents/Python Projects/gutenai"',
        f'cd "{repo_root}"'
    )

    if new_content != content:
        script_path.write_text(new_content)
        print(f"✔ Actualizada la ruta en run_gutenai.sh a: {repo_root}")
    else:
        print("✔ run_gutenai.sh ya tiene la ruta correcta.")

    # Hacer el script ejecutable
    script_path.chmod(0o755)


def install_desktop_file(repo_root: Path) -> None:
    """Copia el .desktop con las rutas correctas a ~/.local/share/applications/."""
    source = repo_root / "data" / "com.gutenai.editor.desktop"

    if not source.exists():
        print(f"⚠ No se encontró {source}")
        return

    # Leer el contenido
    content = source.read_text()

    # Actualizar la ruta del Exec
    script_path = repo_root / "run_gutenai.sh"
    content = content.replace(
        'Exec="/home/pedro/Documents/Python Projects/gutenai/run_gutenai.sh"',
        f'Exec="{script_path}"'
    )

    # Crear el directorio de destino si no existe
    DESKTOP_TARGET.mkdir(parents=True, exist_ok=True)

    # Escribir el archivo
    target = DESKTOP_TARGET / "com.gutenai.editor.desktop"
    target.write_text(content)
    print(f"✔ Archivo .desktop instalado en {target}")

    # Validar el .desktop si está disponible desktop-file-validate
    validator = shutil.which("desktop-file-validate")
    if validator:
        try:
            subprocess.run([validator, str(target)], check=True, capture_output=True)
            print("✔ Archivo .desktop validado correctamente.")
        except subprocess.CalledProcessError as exc:
            print(f"⚠ Advertencia al validar .desktop: {exc.stderr.decode()}")

    # Actualizar la base de datos de aplicaciones
    updater = shutil.which("update-desktop-database")
    if updater:
        try:
            subprocess.run([updater, str(DESKTOP_TARGET)], check=True, capture_output=True)
            print("✔ Base de datos de aplicaciones actualizada.")
        except subprocess.CalledProcessError as exc:
            print(f"⚠ No se pudo actualizar la base de datos: {exc}")


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    png_source = repo_root / "gutenai.png"
    svg_source = repo_root / "gutenai.svg"

    print("=" * 60)
    print("  Instalador de GutenAI")
    print("=" * 60)
    print(f"Ruta del proyecto: {repo_root}\n")

    # 1. Configurar venv
    print("[1/6] Configurando entorno virtual...")
    venv_python = setup_venv(repo_root)

    # 2. Instalar dependencias
    print("\n[2/6] Instalando dependencias...")
    install_requirements(venv_python, repo_root)

    # 3. Actualizar script
    print("\n[3/6] Actualizando run_gutenai.sh...")
    update_shell_script(repo_root)

    # 4. Instalar iconos
    print("\n[4/6] Instalando iconos...")
    Image, ImageOps = require_pillow()
    install_pngs(png_source, Image, ImageOps)
    install_svg(svg_source)
    refresh_icon_cache()

    # 5. Instalar archivo .desktop
    print("\n[5/6] Instalando archivo .desktop...")
    install_desktop_file(repo_root)

    print("\n[6/6] Finalización")
    print("=" * 60)
    print("✔ Instalación completada exitosamente!")
    print(f"  - Entorno virtual: {repo_root / '.venv'}")
    print(f"  - Lanzador instalado en: {DESKTOP_TARGET / 'com.gutenai.editor.desktop'}")
    print(f"  - Iconos instalados en: {TARGET_BASE}")
    print("\nPodés buscar 'GutenAI' en tu menú de aplicaciones.")
    print("=" * 60)


if __name__ == "__main__":
    main()
