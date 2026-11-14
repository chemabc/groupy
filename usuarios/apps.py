"""
Configuración y contrato del módulo «usuarios».
"""

from base.contrato import Ayuda, Capa, DatosDeEjemplo, EntradaDeMenu, ModuloConfig, Vista


class UsuariosConfig(ModuloConfig):
    """
    Contrato del módulo «usuarios». Aporta la sección «Configuración de mi cuenta» (preferencias y contraseña) y los
    usuarios de ejemplo.
    """

    name = "usuarios"
    verbose_name = "Usuarios"
    capa = Capa.IDENTIDAD
    descripcion = (
        "Cuentas con seudónimo (alias) con las que se actúa en la plataforma: entrar y salir, contraseña "
        "y preferencias de presentación. La identidad real no está aquí, sino en la bóveda."
    )
    datos_de_ejemplo = DatosDeEjemplo(crear="usuarios.ejemplos.crear", borrar="usuarios.ejemplos.borrar")
    menu = (
        EntradaDeMenu(
            codigo="usuarios.cuenta",
            nombre="Configuración de mi cuenta",
            url="usuarios:preferencias",
            icono="✦",
            color="#db2777",
            vistas=(
                Vista("Preferencias", "usuarios:preferencias"),
                Vista("Contraseña", "usuarios:contrasena"),
            ),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="usuarios.cuenta",
            titulo="Configuración de mi cuenta",
            texto=(
                "Aquí cambias lo que es solo tuyo.\n\n"
                "«Preferencias»: el tema (claro, día u oscuro), el tamaño de la letra y la densidad. Se "
                "guardan en tu cuenta, así que te siguen al móvil o a otro ordenador.\n\n"
                "«Contraseña»: para cambiarla hace falta la actual. Nadie más puede verla, ni el "
                "superadmin."
            ),
        ),
    )
