"""
Configuración y contrato del módulo «mantenimiento».
"""

from base.contrato import Ayuda, Capa, EntradaDeMenu, ModuloConfig, Permiso, Vista


class MantenimientoConfig(ModuloConfig):
    """
    Contrato del módulo «mantenimiento». Aporta la sección «Desarrollo y mantenimiento» del menú, que
    ve quien tiene el permiso «mantenimiento.ver» (de entrada, solo el superadmin), con dos subsecciones:
    las herramientas de pruebas (importar grupos y usuarios, datos de ejemplo) y la entrada a la
    trastienda. La documentación y las guías de desarrollo están en el módulo «ayuda».
    """

    name = "mantenimiento"
    verbose_name = "Desarrollo y mantenimiento"
    capa = Capa.FUNCIONAL
    descripcion = (
        "Herramientas para quien mantiene la plataforma: la importación masiva de grupos y usuarios para "
        "las pruebas, los datos de ejemplo y la entrada a la trastienda. Más adelante, la salud del sistema."
    )
    permisos = (
        # Sin roles por defecto: solo lo tiene el superadmin (que lo tiene todo).
        Permiso("mantenimiento.ver", "Importar datos de prueba, crear los datos de ejemplo y entrar en la trastienda"),
    )
    menu = (
        EntradaDeMenu(
            codigo="mantenimiento.desarrollo",
            nombre="Desarrollo y mantenimiento",
            url="mantenimiento:importar_grupos",
            icono="⚒",
            color="#ea580c",
            permiso="mantenimiento.ver",
            subsecciones=(
                EntradaDeMenu(
                    codigo="mantenimiento.pruebas",
                    permiso="mantenimiento.ver",
                    nombre="Pruebas",
                    url="mantenimiento:importar_grupos",
                    icono="⚗",
                    color="#e11d48",
                    vistas=(
                        Vista("Importar grupos", "mantenimiento:importar_grupos"),
                        Vista("Importar usuarios", "mantenimiento:importar_usuarios"),
                        Vista("Datos de ejemplo", "mantenimiento:datos_de_ejemplo"),
                    ),
                ),
                EntradaDeMenu(
                    codigo="mantenimiento.trastienda",
                    permiso="mantenimiento.ver",
                    nombre="Trastienda",
                    url="mantenimiento:trastienda",
                    icono="⚠",
                    color="#dc2626",
                    vistas=(Vista("Trastienda", "mantenimiento:trastienda"),),
                ),
            ),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="mantenimiento.pruebas",
            titulo="Pruebas",
            texto=(
                "Herramientas para preparar datos de prueba de forma masiva.\n\n"
                "«Importar grupos»: organizaciones y grupos (con sus grupos padre, a cualquier profundidad) a "
                "partir de una hoja de cálculo.\n\n"
                "«Importar usuarios»: alias con su contraseña, sus grupos, su rol y su asamblea base. Solo "
                "funciona si está activado «Permitir el alta masiva de usuarios», porque crea cuentas sin "
                "pasar por la bóveda.\n\n"
                "En los dos casos: descarga la plantilla (.ods de LibreOffice), rellénala, súbela, revisa la "
                "vista previa y confirma. No se crea nada hasta confirmar, y se crea todo o nada.\n\n"
                "«Datos de ejemplo»: crea o borra de un golpe los datos inventados de todos los módulos "
                "(organizaciones de ríos, grupos de afluentes, usuarios de animales y árboles…). Borrarlos no "
                "toca al superadmin. Solo funciona en desarrollo."
            ),
        ),
        Ayuda(
            seccion="mantenimiento.trastienda",
            titulo="Trastienda",
            texto="El panel técnico de Django, para emergencias. El trabajo diario se hace en la aplicación.",
        ),
    )
