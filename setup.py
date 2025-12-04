#!/usr/bin/env python3
"""Instala los iconos de GutenAI en el tema hicolor del usuario."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

TARGET_BASE = Path.home() / ".local" / "share" / "icons" / "hicolor"
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
    icon_names = ["gutenai", "gutenai.com"]

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
    icon_names = ["gutenai", "gutenai.com"]

    # Instalar con ambos nombres
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

    try:
        subprocess.run([helper, str(TARGET_BASE)], check=True)
        print("✔ Cache de iconos actualizada.")
    except subprocess.CalledProcessError as exc:
        print(f"⚠ No se pudo actualizar la cache de iconos: {exc}")


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    png_source = repo_root / "gutenai.png"
    svg_source = repo_root / "gutenai.svg"

    Image, ImageOps = require_pillow()
    install_pngs(png_source, Image, ImageOps)
    install_svg(svg_source)
    refresh_icon_cache()


if __name__ == "__main__":
    main()
