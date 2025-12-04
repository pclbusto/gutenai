"""
ui/statistics_dialog.py
Diálogo para mostrar estadísticas del libro y capítulos
"""
from . import *
from gi.repository import Gtk, Adw, GLib
from pathlib import Path
from typing import TYPE_CHECKING
import re

if TYPE_CHECKING:
    from .main_window import GutenAIWindow


class StatisticsDialog(Adw.Window):
    """Diálogo para mostrar estadísticas del EPUB"""

    def __init__(self, main_window: 'GutenAIWindow', current_chapter_only: bool = False):
        super().__init__()

        self.main_window = main_window
        self.core = main_window.core
        self.current_chapter_only = current_chapter_only

        if not self.core:
            return

        # Configuración de ventana
        if current_chapter_only:
            self.set_title("Estadísticas del Capítulo Actual")
            self.set_default_size(600, 400)
        else:
            self.set_title("Estadísticas del Libro")
            self.set_default_size(900, 700)

        self.set_modal(True)
        self.set_transient_for(main_window)

        # Crear interfaz
        self._setup_ui()

        # Calcular estadísticas en segundo plano
        self._calculate_statistics()

    def _setup_ui(self):
        """Configura la interfaz del diálogo"""

        # HeaderBar
        header_bar = Adw.HeaderBar()

        # Botón cerrar
        close_btn = Gtk.Button(label="Cerrar")
        close_btn.connect('clicked', lambda b: self.close())
        header_bar.pack_end(close_btn)

        # Botón exportar
        export_btn = Gtk.Button(label="Exportar")
        export_btn.set_icon_name("document-save-symbolic")
        export_btn.connect('clicked', self._on_export_stats)
        header_bar.pack_start(export_btn)

        # ScrolledWindow para el contenido
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        # Box principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scrolled.set_child(main_box)

        # Toast overlay
        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_child(scrolled)

        # Spinner mientras se calculan las estadísticas
        self.spinner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.spinner_box.set_valign(Gtk.Align.CENTER)
        self.spinner_box.set_margin_top(50)
        self.spinner_box.set_margin_bottom(50)

        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(48, 48)
        self.spinner.start()

        spinner_label = Gtk.Label(label="Calculando estadísticas...")
        spinner_label.add_css_class("title-2")

        self.spinner_box.append(self.spinner)
        self.spinner_box.append(spinner_label)
        main_box.append(self.spinner_box)

        # Contenedor para las estadísticas (oculto inicialmente)
        self.stats_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.stats_container.set_visible(False)
        main_box.append(self.stats_container)

        # Grupo de estadísticas globales
        self.global_group = Adw.PreferencesGroup()
        if self.current_chapter_only:
            self.global_group.set_title("Estadísticas del Capítulo")
        else:
            self.global_group.set_title("Estadísticas Generales")
        self.global_group.set_margin_start(12)
        self.global_group.set_margin_end(12)
        self.global_group.set_margin_top(12)
        self.stats_container.append(self.global_group)

        # Grupo de estadísticas por capítulo (solo para libro completo)
        if not self.current_chapter_only:
            self.chapters_group = Adw.PreferencesGroup()
            self.chapters_group.set_title("Estadísticas por Capítulo")
            self.chapters_group.set_margin_start(12)
            self.chapters_group.set_margin_end(12)
            self.chapters_group.set_margin_top(12)
            self.chapters_group.set_margin_bottom(12)
            self.stats_container.append(self.chapters_group)
        else:
            self.chapters_group = None

        # ToolbarView
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header_bar)
        toolbar_view.set_content(self.toast_overlay)
        self.set_content(toolbar_view)

    def _calculate_statistics(self):
        """Calcula las estadísticas en segundo plano"""
        import threading

        def calculate_thread():
            try:
                stats = self._compute_book_statistics()
                GLib.idle_add(self._show_statistics, stats)
            except Exception as e:
                GLib.idle_add(self._show_error, str(e))

        threading.Thread(target=calculate_thread, daemon=True).start()

    def _compute_book_statistics(self) -> dict:
        """Calcula todas las estadísticas del libro"""
        print("[Statistics] Iniciando cálculo de estadísticas...")

        # Obtener documentos del spine
        spine = self.core.get_spine()
        print(f"[Statistics] Spine tiene {len(spine)} documentos: {spine}")

        # Si solo queremos el capítulo actual, filtrar el spine
        if self.current_chapter_only:
            current_resource = self.main_window.current_resource
            if not current_resource:
                print("[Statistics] No hay capítulo actual seleccionado")
                raise Exception("No hay ningún capítulo abierto actualmente")

            # Buscar el idref del capítulo actual
            current_idref = None
            for idref in spine:
                item = self.core._get_item(idref)
                if item.href == current_resource:
                    current_idref = idref
                    break

            if current_idref:
                spine = [current_idref]
                print(f"[Statistics] Mostrando solo capítulo actual: {current_resource}")
            else:
                print(f"[Statistics] El archivo actual no está en el spine: {current_resource}")
                raise Exception("El archivo actual no es un capítulo del libro")

        # Estadísticas globales
        total_words = 0
        total_paragraphs = 0
        total_characters = 0
        total_characters_no_spaces = 0
        total_chapters = len(spine)

        # Estadísticas por capítulo
        chapters_stats = []

        for i, idref in enumerate(spine, 1):
            try:
                print(f"\n[Statistics] Procesando {i}/{len(spine)}: idref={idref}")

                # Convertir idref a href
                item = self.core._get_item(idref)
                href = item.href
                print(f"[Statistics] href={href}")

                # Leer contenido HTML
                html_content = self.core.read_text(href)
                print(f"[Statistics] HTML leído: {len(html_content)} caracteres")

                if not html_content or not html_content.strip():
                    print(f"[Statistics] ADVERTENCIA: HTML vacío para {href}")
                    continue

                # Extraer texto limpio
                text = self._extract_text_from_html(html_content)
                print(f"[Statistics] Texto extraído: {len(text)} caracteres")
                print(f"[Statistics] Primeros 200 chars: {text[:200]!r}")

                # Calcular estadísticas
                words = self._count_words(text)
                paragraphs = self._count_paragraphs(html_content)
                chars = len(text)
                chars_no_spaces = len(text.replace(' ', '').replace('\n', '').replace('\t', ''))

                print(f"[Statistics] Palabras: {words}, Párrafos: {paragraphs}")

                # Actualizar totales
                total_words += words
                total_paragraphs += paragraphs
                total_characters += chars
                total_characters_no_spaces += chars_no_spaces

                # Guardar estadísticas del capítulo
                chapter_name = Path(href).name
                chapters_stats.append({
                    'name': chapter_name,
                    'idref': idref,
                    'href': href,
                    'words': words,
                    'paragraphs': paragraphs,
                    'characters': chars,
                    'characters_no_spaces': chars_no_spaces
                })

            except Exception as e:
                print(f"[Statistics] ERROR procesando idref={idref}: {e}")
                import traceback
                traceback.print_exc()
                continue

        # Tiempo de lectura estimado (promedio 200-250 palabras por minuto)
        reading_time_minutes = total_words / 225 if total_words > 0 else 0
        reading_hours = int(reading_time_minutes / 60)
        reading_minutes = int(reading_time_minutes % 60)

        result = {
            'total_words': total_words,
            'total_paragraphs': total_paragraphs,
            'total_characters': total_characters,
            'total_characters_no_spaces': total_characters_no_spaces,
            'total_chapters': total_chapters,
            'reading_time_hours': reading_hours,
            'reading_time_minutes': reading_minutes,
            'chapters': chapters_stats
        }

        print(f"\n[Statistics] ===== RESUMEN FINAL =====")
        print(f"[Statistics] Total capítulos: {total_chapters}")
        print(f"[Statistics] Total palabras: {total_words}")
        print(f"[Statistics] Total párrafos: {total_paragraphs}")
        print(f"[Statistics] Total caracteres: {total_characters}")
        print(f"[Statistics] Capítulos procesados: {len(chapters_stats)}")
        print(f"[Statistics] ========================\n")

        return result

    def _extract_text_from_html(self, html_content: str) -> str:
        """Extrae texto limpio del HTML"""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, 'html.parser')

            # Buscar solo el contenido del body
            body = soup.find('body')
            if body is None:
                body = soup

            # Remover elementos no-texto
            for elemento in body(['script', 'style', 'meta', 'link', 'title', 'head']):
                elemento.decompose()

            # Extraer texto
            texto = body.get_text(separator=' ', strip=True)

            # Limpiar espacios múltiples
            texto = re.sub(r'\s+', ' ', texto)

            return texto.strip()

        except ImportError:
            print(f"[Statistics] BeautifulSoup no disponible, usando fallback")
            # Fallback sin BeautifulSoup (re ya está importado al inicio del archivo)

            # Buscar body
            body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
            if body_match:
                contenido = body_match.group(1)
            else:
                contenido = html_content

            # Remover tags HTML
            texto = re.sub(r'<[^>]+>', ' ', contenido)
            # Limpiar espacios
            texto = re.sub(r'\s+', ' ', texto)
            return texto.strip()

    def _count_words(self, text: str) -> int:
        """Cuenta palabras en el texto"""
        if not text or not text.strip():
            return 0

        # Dividir por espacios y filtrar vacíos
        words = [w for w in text.split() if w.strip()]
        return len(words)

    def _count_paragraphs(self, html_content: str) -> int:
        """Cuenta párrafos en el HTML"""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, 'html.parser')

            # Contar elementos que representan párrafos
            paragraphs = soup.find_all(['p', 'div'])

            # Filtrar solo los que tienen texto
            paragraphs_with_text = [p for p in paragraphs if p.get_text(strip=True)]

            return len(paragraphs_with_text)

        except ImportError:
            # Fallback sin BeautifulSoup
            import re
            # Contar tags <p>
            p_tags = re.findall(r'<p[^>]*>.*?</p>', html_content, re.DOTALL | re.IGNORECASE)
            return len(p_tags)

    def _show_statistics(self, stats: dict):
        """Muestra las estadísticas en la interfaz"""

        # Ocultar spinner
        self.spinner.stop()
        self.spinner_box.set_visible(False)

        # Mostrar contenedor de estadísticas
        self.stats_container.set_visible(True)

        # Estadísticas globales
        if not self.current_chapter_only:
            self._add_stat_row(self.global_group, "Capítulos", f"{stats['total_chapters']}")

        self._add_stat_row(self.global_group, "Palabras", f"{stats['total_words']:,}")
        self._add_stat_row(self.global_group, "Párrafos", f"{stats['total_paragraphs']:,}")
        self._add_stat_row(self.global_group, "Caracteres (con espacios)", f"{stats['total_characters']:,}")
        self._add_stat_row(self.global_group, "Caracteres (sin espacios)", f"{stats['total_characters_no_spaces']:,}")

        # Tiempo de lectura estimado
        reading_time = ""
        if stats['reading_time_hours'] > 0:
            reading_time = f"{stats['reading_time_hours']}h {stats['reading_time_minutes']}min"
        else:
            reading_time = f"{stats['reading_time_minutes']} minutos"

        self._add_stat_row(self.global_group, "Tiempo de lectura estimado", reading_time)

        # Estadísticas por capítulo (solo para libro completo)
        if not self.current_chapter_only and self.chapters_group:
            for chapter in stats['chapters']:
                chapter_row = Adw.ExpanderRow()
                chapter_row.set_title(chapter['name'])
                chapter_row.set_subtitle(f"{chapter['words']:,} palabras • {chapter['paragraphs']} párrafos")

                # Detalles del capítulo
                details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
                details_box.set_margin_start(12)
                details_box.set_margin_end(12)
                details_box.set_margin_top(6)
                details_box.set_margin_bottom(6)

                self._add_detail_label(details_box, "Palabras", f"{chapter['words']:,}")
                self._add_detail_label(details_box, "Párrafos", f"{chapter['paragraphs']}")
                self._add_detail_label(details_box, "Caracteres (con espacios)", f"{chapter['characters']:,}")
                self._add_detail_label(details_box, "Caracteres (sin espacios)", f"{chapter['characters_no_spaces']:,}")

                chapter_row.add_row(Adw.PreferencesRow(child=details_box))
                self.chapters_group.add(chapter_row)

    def _add_stat_row(self, group, title: str, value: str):
        """Agrega una fila de estadística"""
        row = Adw.ActionRow()
        row.set_title(title)

        value_label = Gtk.Label(label=value)
        value_label.add_css_class("title-2")
        value_label.set_valign(Gtk.Align.CENTER)

        row.add_suffix(value_label)
        group.add(row)

    def _add_detail_label(self, box, label: str, value: str):
        """Agrega una etiqueta de detalle"""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.set_margin_top(3)
        row.set_margin_bottom(3)

        label_widget = Gtk.Label(label=label + ":")
        label_widget.set_halign(Gtk.Align.START)
        label_widget.set_hexpand(True)
        label_widget.add_css_class("dim-label")

        value_widget = Gtk.Label(label=value)
        value_widget.set_halign(Gtk.Align.END)
        value_widget.add_css_class("monospace")

        row.append(label_widget)
        row.append(value_widget)
        box.append(row)

    def _show_error(self, error_message: str):
        """Muestra un error"""
        self.spinner.stop()
        self.spinner_box.set_visible(False)

        error_status = Adw.StatusPage()
        error_status.set_icon_name("dialog-error-symbolic")
        error_status.set_title("Error calculando estadísticas")
        error_status.set_description(error_message)

        self.stats_container.append(error_status)
        self.stats_container.set_visible(True)

    def _on_export_stats(self, button):
        """Exporta las estadísticas a un archivo de texto"""
        dialog = Gtk.FileDialog()
        dialog.set_title("Exportar estadísticas")
        dialog.set_initial_name("estadisticas_libro.txt")

        dialog.save(self, None, self._on_export_response)

    def _on_export_response(self, dialog, result):
        """Maneja la respuesta del diálogo de exportación"""
        try:
            file = dialog.save_finish(result)
            if file:
                output_path = Path(file.get_path())

                # Generar reporte de texto
                report = self._generate_text_report()

                # Guardar archivo
                output_path.write_text(report, encoding='utf-8')

                # Mostrar confirmación
                toast = Adw.Toast()
                toast.set_title(f"Estadísticas exportadas a {output_path.name}")
                toast.set_timeout(3)
                self.toast_overlay.add_toast(toast)

        except Exception as e:
            if "dismissed" not in str(e).lower():
                print(f"Error exportando estadísticas: {e}")

    def _generate_text_report(self) -> str:
        """Genera un reporte de texto con las estadísticas"""
        # Recalcular para tener los datos frescos
        stats = self._compute_book_statistics()

        metadata = self.core.get_metadata()
        book_title = metadata.get('title', 'Libro sin título')

        report = f"""ESTADÍSTICAS DEL LIBRO
{'=' * 60}

Título: {book_title}
Fecha del reporte: {GLib.DateTime.new_now_local().format('%Y-%m-%d %H:%M')}

ESTADÍSTICAS GENERALES
{'-' * 60}
Capítulos: {stats['total_chapters']}
Palabras totales: {stats['total_words']:,}
Párrafos totales: {stats['total_paragraphs']:,}
Caracteres (con espacios): {stats['total_characters']:,}
Caracteres (sin espacios): {stats['total_characters_no_spaces']:,}
Tiempo de lectura estimado: {stats['reading_time_hours']}h {stats['reading_time_minutes']}min

ESTADÍSTICAS POR CAPÍTULO
{'-' * 60}
"""

        for i, chapter in enumerate(stats['chapters'], 1):
            report += f"\n{i}. {chapter['name']}\n"
            report += f"   Palabras: {chapter['words']:,}\n"
            report += f"   Párrafos: {chapter['paragraphs']}\n"
            report += f"   Caracteres (con espacios): {chapter['characters']:,}\n"
            report += f"   Caracteres (sin espacios): {chapter['characters_no_spaces']:,}\n"

        report += f"\n{'=' * 60}\n"
        report += "Generado por GutenAI - Editor EPUB\n"

        return report


def show_statistics_dialog(main_window: 'GutenAIWindow', current_chapter_only: bool = False):
    """Muestra el diálogo de estadísticas"""
    if not main_window.core:
        main_window.show_error("No hay ningún proyecto abierto")
        return

    dialog = StatisticsDialog(main_window, current_chapter_only=current_chapter_only)
    dialog.present()
