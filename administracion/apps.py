"""
Configuración y contrato del módulo «administracion».
"""

from base.contrato import Ayuda, Capa, EntradaDeMenu, ModuloConfig, Permiso, Vista


class AdministracionConfig(ModuloConfig):
    """
    Contrato del módulo «administracion»: las pantallas del superadmin que juntan varios módulos (la
    bóveda, los alias, los grupos…). De momento, la sección «Usuarios»: personas reales de la bóveda (con
    los dominios de correo permitidos) y alias de la plataforma.
    """

    name = "administracion"
    verbose_name = "Administración"
    capa = Capa.FUNCIONAL
    descripcion = (
        "Pantallas del superadmin: personas reales (bóveda), dominios de correo permitidos y alias de la "
        "plataforma. Más adelante, organizaciones y tipologías."
    )
    permisos = (
        # Sin roles por defecto: solo el superadmin.
        Permiso("administracion.usuarios", "Gestionar los alias: verlos, activarlos o desactivarlos y nombrar superadmins"),
    )
    menu = (
        EntradaDeMenu(
            codigo="administracion.usuarios",
            nombre="Usuarios",
            url="administracion:personas",
            icono="☷",
            orden=800,
            permiso="administracion.usuarios",
            subsecciones=(
                EntradaDeMenu(
                    codigo="administracion.boveda",
                    nombre="Bóveda (personas reales)",
                    url="administracion:personas",
                    icono="▣",
                    vistas=(
                        Vista("Personas", "administracion:personas"),
                        Vista("Dominios permitidos", "administracion:dominios"),
                    ),
                ),
                EntradaDeMenu(
                    codigo="administracion.alias",
                    nombre="Alias (usuarios de la app)",
                    url="administracion:alias",
                    icono="@",
                    vistas=(Vista("Lista", "administracion:alias"),),
                ),
            ),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="administracion.boveda",
            titulo="Bóveda (personas reales)",
            texto=(
                "La identidad real de cada persona, guardada aparte de la plataforma: ninguna tabla une a una "
                "persona con su alias.\n\n"
                "«Personas»: en la lista, cada persona sale como «Persona 3f2a9c1e»; el nombre real, solo en su "
                "ficha. Desde aquí se da de alta a alguien (nombre, correo oficial y organización) y se valida "
                "(alta por el superadmin). Al validarla, su correo se borra y queda solo su huella, y su pase se "
                "marca como emitido: no podrá conseguir un segundo alias. Su alias se crea aparte.\n\n"
                "«Dominios permitidos»: los dominios de correo que admite cada organización para registrarse."
            ),
        ),
        Ayuda(
            seccion="administracion.alias",
            titulo="Alias (usuarios de la app)",
            texto=(
                "Las cuentas con seudónimo de la plataforma. «Origen» dice cómo se creó: alta directa (a mano o "
                "importada) o con un pase de la bóveda (registro real). Nunca se ve qué persona hay detrás.\n\n"
                "En la ficha de cada alias se ven todos sus grupos y se puede activar o desactivar la cuenta y "
                "nombrarle superadmin (para repartir el trabajo entre varias personas)."
            ),
        ),
    )
