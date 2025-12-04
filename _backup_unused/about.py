import gi
gi.require_version("Adw", "1")
from gi.repository import Adw

def create_about_window(parent):
    """Devuelve una Adw.AboutWindow configurada."""
    about = Adw.AboutWindow(transient_for=parent, modal=True)

    about.set_application_name("Guten.AI")
    about.set_application_icon("gutenai")
    about.set_version("1.0.0")
    about.set_comments("Editor de libros EPUB con inteligencia artificial")

    about.set_developer_name("Busto Pedro")
    about.set_translator_credits("Busto Pedro")

    # Enlace principal (el label será el dominio)
    about.set_website("https://github.com/pclbusto/gutenai")
    # Enlace adicional con texto custom
    about.add_link("Documentación del proyecto", "https://pclbusto.github.io/gutenai/")

    about.add_credit_section("Código fuente", ["Busto Pedro"])
    about.add_credit_section("Diseño", ["Busto Pedro"])
    about.add_credit_section("Arte", ["Busto Pedro"])

    about.set_license(
        "Este programa viene SIN NINGUNA GARANTÍA. "
        "Consulte la Licencia Pública General Reducida de GNU, "
        "versión 2.1 o posterior para obtener más detalles."
    )
    about.set_copyright(
        "© 2017–2022 Purism SPC\n© 2023-2024 GNOME Foundation Inc."
    )

    return about
