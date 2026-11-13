"""
Configuración y contrato del módulo «mantenimiento».
"""

from base.contrato import Ayuda, Capa, EntradaDeMenu, ModuloConfig, Permiso, Vista


class MantenimientoConfig(ModuloConfig):
    """
    Contrato del módulo «mantenimiento». Aporta la sección «Desarrollo y mantenimiento» del menú, que
    solo ve quien tiene el permiso «mantenimiento.ver» (de entrada, solo el superadmin): la documentación
    del proyecto (los ficheros de docs/, convertidos en páginas) y la entrada a la trastienda.
    """

    name = "mantenimiento"
    verbose_name = "Desarrollo y mantenimiento"
    capa = Capa.FUNCIONAL
    descripcion = (
        "Herramientas para quien mantiene la plataforma: la documentación del proyecto (diseño, registro y "
        "validación, tutorial y arranque) y la entrada a la trastienda. Más adelante, la salud del sistema."
    )
    permisos = (
        # Sin roles por defecto: solo lo tiene el superadmin (que lo tiene todo).
        Permiso("mantenimiento.ver", "Ver la documentación técnica y entrar en la trastienda"),
    )
    menu = (
        EntradaDeMenu(
            codigo="mantenimiento.desarrollo",
            nombre="Desarrollo y mantenimiento",
            url="mantenimiento:documentacion",
            icono="⚙",
            orden=950,
            permiso="mantenimiento.ver",
            vistas=(
                Vista("Documentación", "mantenimiento:documentacion"),
                Vista("Trastienda", "mantenimiento:trastienda"),
            ),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="mantenimiento.desarrollo",
            titulo="Desarrollo y mantenimiento",
            texto=(
                "Herramientas para quien mantiene la plataforma. Solo la ve el superadmin.\n\n"
                "«Documentación»: los documentos del proyecto (docs/ en el repositorio), siempre al día: el "
                "diseño con todo lo decidido, cómo funcionan el registro y la validación, el tutorial con lo "
                "aprendido y cómo arrancar y probar. A la izquierda, el índice del documento.\n\n"
                "«Trastienda»: el panel técnico de Django, para emergencias. El trabajo diario se hace en la "
                "aplicación."
            ),
        ),
    )
