"""
Configuración y contrato del módulo «tipologias».
"""

from base.contrato import Ayuda, Capa, DatosDeEjemplo, EntradaDeMenu, ModuloConfig, Permiso, Vista


class TipologiasConfig(ModuloConfig):
    """
    Contrato del módulo «tipologias»: los tipos de proyecto y de evento, en árbol, con sus campos
    personalizados. Aporta la sección «Configuración → Tipologías». Está en la capa de organización porque
    cada organización puede tener subtipos propios.
    """

    name = "tipologias"
    verbose_name = "Tipologías"
    capa = Capa.ORGANIZACION
    descripcion = (
        "Árbol de tipos de proyecto y de evento, cada uno con sus campos personalizados (que heredan sus "
        "subtipos). Los comunes los crea el superadmin; cada organización puede añadir subtipos propios."
    )
    permisos = (
        Permiso(
            "tipologias.gestionar",
            "Crear y cambiar los tipos de proyecto y de evento propios de la organización, con sus campos",
            roles=("admin_org",),
        ),
    )
    datos_de_ejemplo = DatosDeEjemplo(crear="tipologias.ejemplos.crear", borrar="tipologias.ejemplos.borrar")
    menu = (
        EntradaDeMenu(
            codigo="tipologias.configuracion",
            nombre="Configuración",
            url="tipologias:eventos",
            icono="⚙",
            orden=850,
            permiso="tipologias.gestionar",
            subsecciones=(
                EntradaDeMenu(
                    codigo="tipologias.tipologias",
                    nombre="Tipologías",
                    url="tipologias:eventos",
                    icono="❖",
                    vistas=(Vista("De eventos", "tipologias:eventos"), Vista("De proyectos", "tipologias:proyectos")),
                ),
            ),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="tipologias.tipologias",
            titulo="Tipologías",
            texto=(
                "Los tipos de evento y de proyecto (Reunión, Acción, Concentración…), en árbol. Cada tipo puede "
                "pedir datos extra al crear algo de ese tipo: sus campos (texto, número, fecha, sí o no, lista…). "
                "Un subtipo pide los campos de su tipo y los suyos.\n\n"
                "Los tipos comunes sirven en todas las organizaciones y solo los cambia el superadmin. El admin de "
                "cada organización puede añadir subtipos propios, que solo se ven en ella.\n\n"
                "A la izquierda, el árbol: pulsa un tipo para ver y cambiar sus campos. Los campos se ordenan "
                "arrastrándolos por el asa ⠿."
            ),
        ),
    )
