"""
Configuración y contrato del módulo «base».
"""

from django.apps import apps
from django.conf import settings
from django.utils.module_loading import import_string

from .contrato import Ayuda, Capa, EntradaDeMenu, ModuloConfig, Vista


class BaseConfig(ModuloConfig):
    """
    Contrato del módulo «base». Aporta la sección «Inicio» del menú (la portada de cada cuenta) y la
    demostración de la plantilla («Componentes», para quien desarrolla), y carga el registro de módulos al
    arrancar.
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
            icono="⊡",
            color="#0284c7",
            vistas=(Vista("Panel", "base:inicio"), Vista("Mis datos", "base:mis_datos")),
        ),
        # La demostración de la plantilla general, para quien desarrolla (va en «Desarrollo y
        # mantenimiento», ver config/menu.py).
        EntradaDeMenu(
            codigo="base.componentes",
            nombre="Componentes",
            url="base:estructura",
            icono="◧",
            color="#64748b",
            permiso="mantenimiento.ver",
            vistas=(Vista("Estructura", "base:estructura"), Vista("Componentes", "base:componentes")),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="base.inicio",
            titulo="Inicio",
            texto=(
                "Tu portada.\n\n"
                "«Panel»: lo pendiente (comunicaciones y solicitudes, enviadas y recibidas) y los proyectos "
                "abiertos en los que participas.\n\n"
                "«Mis datos»: un resumen de tu cuenta, con un botón para editar cada parte.\n\n"
                "Los dos están aún por hacer."
            ),
            ejemplo="Al entrar por la mañana, el panel te dice que tienes una solicitud por apoyar y dos tareas de un proyecto.",
        ),
        Ayuda(
            seccion="base.componentes",
            titulo="Componentes",
            texto=(
                "Para quien desarrolla: «Estructura» explica las partes de la pantalla y «Componentes» muestra "
                "las piezas comunes de la interfaz (tablas filtrables, botón «copiar»…) con datos inventados."
            ),
        ),
    )

    # Django llama a este método una vez, cuando ya ha cargado todas las apps. Aquí se lee el contrato de
    # todos los módulos y se activan las comprobaciones del contrato.
    def ready(self):
        # Importar el fichero basta para que Django registre las comprobaciones que contiene.
        from . import comprobaciones  # noqa: F401
        from .registro import registro

        registro.cargar(apps.get_app_configs(), raiz=settings.BASE_DIR, disposicion=disposicion_del_menu())


# Devuelve la disposición del menú (config/menu.py), que dice el orden de las entradas y dentro de qué
# sección va cada una. Se busca por el ajuste DISPOSICION_DEL_MENU porque «base» no debe importar nada de
# fuera directamente. La usan BaseConfig.ready y las pruebas (base/pruebas.py, contratos_de_prueba).
def disposicion_del_menu():
    return import_string(settings.DISPOSICION_DEL_MENU)
