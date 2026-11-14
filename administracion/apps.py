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
        "plataforma, y roles y permisos (qué puede hacer cada rol, excepciones y explicación de un permiso)."
    )
    permisos = (
        # Sin roles por defecto: solo el superadmin.
        Permiso("administracion.usuarios", "Gestionar los alias: verlos, activarlos o desactivarlos y nombrar superadmins"),
        Permiso(
            "administracion.roles",
            "Cambiar los roles y sus permisos, dar o quitar permisos sueltos y ver por qué alguien tiene un permiso",
        ),
    )
    menu = (
        EntradaDeMenu(
            codigo="administracion.usuarios",
            nombre="Usuarios",
            url="administracion:personas",
            icono="☺",
            color="#2563eb",
            permiso="administracion.usuarios",
            subsecciones=(
                EntradaDeMenu(
                    codigo="administracion.boveda",
                    nombre="Bóveda (personas reales)",
                    url="administracion:personas",
                    icono="▣",
                    color="#4f46e5",
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
                    color="#7c3aed",
                    vistas=(Vista("Lista", "administracion:alias"),),
                ),
                # Roles y permisos (13 de noviembre de 2026): dentro de «Usuarios», a petición de la
                # persona usuaria («al fin y al cabo son roles de usuarios»).
                EntradaDeMenu(
                    codigo="administracion.roles",
                    nombre="Roles y permisos",
                    url="administracion:roles",
                    icono="♔",
                    color="#92400e",
                    permiso="administracion.roles",
                    otras_rutas=("administracion:rol",),
                    vistas=(
                        Vista("Roles", "administracion:roles"),
                        Vista("Excepciones", "administracion:excepciones"),
                        Vista("Explicar un permiso", "administracion:explicar"),
                    ),
                ),
            ),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="administracion.roles",
            titulo="Roles y permisos",
            texto=(
                "Un permiso es algo que se puede hacer («Admitir personas en el grupo»); lo declara cada módulo. "
                "Un rol es un conjunto de permisos que se tiene en un grupo: «Usuario» (cualquier miembro; vale "
                "también en los grupos que contienen al suyo), «Admin del grupo» (solo en ese grupo) y «Admin de "
                "la organización» (en todos sus grupos). Puedes crear roles propios (por ejemplo, «Tesorería») y "
                "darlos cambiando el rol de una persona en la ficha de su grupo. El superadmin lo puede todo.\n\n"
                "«Roles»: pulsa uno para marcar o desmarcar sus permisos. Los cambios valen al momento para todo "
                "el mundo.\n\n"
                "«Excepciones»: dar o quitar un permiso suelto a una persona en un grupo, con su motivo. Quitar "
                "gana a cualquier rol.\n\n"
                "«Explicar un permiso»: eliges persona, grupo y permiso, y se ve paso a paso por qué lo tiene o "
                "no. Sirve para resolver dudas («¿por qué no puedo…?»)."
            ),
        ),
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
