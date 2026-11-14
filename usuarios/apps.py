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
        # «Configuración de mi cuenta» y sus subsecciones de la izquierda. Otros módulos ponen las suyas
        # dentro (avisos que recibo, archivo…) y «Mis datos» junta en pestañas los datos, los talentos y el
        # lugar (ver config/menu.py).
        EntradaDeMenu(
            codigo="usuarios.cuenta",
            nombre="Configuración de mi cuenta",
            url="usuarios:preferencias",
            icono="✦",
            color="#db2777",
        ),
        EntradaDeMenu(
            codigo="usuarios.usabilidad",
            nombre="Usabilidad",
            url="usuarios:preferencias",
            icono="◑",
            color="#be185e",
            vistas=(Vista("Tema, letra y densidad", "usuarios:preferencias"),),
        ),
        EntradaDeMenu(
            codigo="usuarios.mis_datos",
            nombre="Mis datos",
            url="proximamente:datos_de_cuenta",
            icono="☉",
            color="#9f1240",
        ),
        EntradaDeMenu(
            codigo="usuarios.contrasena",
            nombre="Contraseña",
            url="usuarios:contrasena",
            icono="⚿",
            color="#701a75",
        ),
    )
    ayuda = (
        Ayuda(
            seccion="usuarios.cuenta",
            titulo="Configuración de mi cuenta",
            texto=(
                "Aquí cambias lo que es solo tuyo: cómo se ve la aplicación, tus datos (también tus talentos y tu "
                "lugar), qué avisos recibes, tu contraseña y lo que se ha archivado."
            ),
        ),
        Ayuda(
            seccion="usuarios.usabilidad",
            titulo="Usabilidad",
            texto=(
                "El tema (claro, día u oscuro), el tamaño de la letra y la densidad. Se guardan en tu cuenta, así "
                "que te siguen al móvil o a otro ordenador."
            ),
        ),
        Ayuda(
            seccion="usuarios.contrasena",
            titulo="Contraseña",
            texto="Para cambiarla hace falta la actual. Nadie más puede verla, ni el superadmin.",
        ),
    )
