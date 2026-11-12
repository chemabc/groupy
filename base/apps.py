"""
Configuración y contrato del módulo «base».
"""

from django.apps import apps
from django.conf import settings

from .contrato import Ayuda, Capa, EntradaDeMenu, ModuloConfig, Vista


class BaseConfig(ModuloConfig):
    """
    Contrato del módulo «base». Aporta la sección «Inicio» del menú, que de momento sirve para ver
    funcionando la plantilla general, y carga el registro de módulos al arrancar.
    """

    name = "base"
    verbose_name = "Base"
    capa = Capa.BASE
    descripcion = (
        "Piezas comunes a toda la aplicación: el contrato de módulo, el registro de módulos y el diseño "
        "común de la interfaz."
    )
    menu = (
        EntradaDeMenu(
            codigo="base.inicio",
            nombre="Inicio",
            url="base:inicio",
            orden=0,
            vistas=(
                Vista("Estructura", "base:inicio"),
                Vista("Componentes", "base:componentes"),
            ),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="base.inicio",
            titulo="Inicio",
            texto=(
                "Esta es la portada provisional mientras se construye la aplicación.\n\n"
                "«Estructura» explica las partes de la pantalla y permite elegir el tema, el tamaño de "
                "letra y la densidad. «Componentes» muestra las piezas comunes de la interfaz."
            ),
        ),
    )

    # Django llama a este método una vez, cuando ya ha cargado todas las apps. Aquí se lee el contrato de
    # todos los módulos y se activan las comprobaciones del contrato.
    def ready(self):
        # Importar el fichero basta para que Django registre las comprobaciones que contiene.
        from . import comprobaciones  # noqa: F401
        from .registro import registro

        registro.cargar(apps.get_app_configs(), raiz=settings.BASE_DIR)
