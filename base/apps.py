"""
Configuración y contrato del módulo «base».
"""

from django.apps import apps
from django.conf import settings

from .contrato import Capa, ModuloConfig


class BaseConfig(ModuloConfig):
    """
    Contrato del módulo «base». De momento no aporta permisos, menú ni ayuda: solo carga el registro de
    módulos al arrancar. Las piezas de interfaz (plantilla, tabla filtrable, botón «copiar») llegarán en
    las piezas siguientes de la fase 0.
    """

    name = "base"
    verbose_name = "Base"
    capa = Capa.BASE
    descripcion = (
        "Piezas comunes a toda la aplicación: el contrato de módulo, el registro de módulos y el diseño "
        "común de la interfaz."
    )

    # Django llama a este método una vez, cuando ya ha cargado todas las apps. Aquí se lee el contrato de
    # todos los módulos y se activan las comprobaciones del contrato.
    def ready(self):
        # Importar el fichero basta para que Django registre las comprobaciones que contiene.
        from . import comprobaciones  # noqa: F401
        from .registro import registro

        registro.cargar(apps.get_app_configs(), raiz=settings.BASE_DIR)
