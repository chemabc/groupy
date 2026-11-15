"""
Configuración y contrato del módulo «proximamente».
"""

from dataclasses import dataclass

from base.contrato import Capa, EntradaDeMenu, ModuloConfig


@dataclass(frozen=True)
class Pendiente:
    """Una herramienta que aún no existe pero ya tiene su sitio en el menú."""

    # Nombre en la dirección y final del código («con_grupos» → «proximamente.con_grupos»).
    clave: str
    # Nombre en el menú.
    nombre: str
    # Qué hará, en una o dos frases. Se ve al pulsarla.
    descripcion: str
    # Icono y color en el menú (no se pueden repetir en todo el menú).
    icono: str
    color: str
    # Permiso para verla (las de administrar). Vacío: la ve todo el mundo.
    permiso: str = ""


# Las herramientas pendientes. Dónde sale cada una lo decide config/menu.py, como el resto del menú.
PENDIENTES = (
    # Lo propio
    Pendiente("con_grupos", "Con grupos", "Conversaciones con un grupo entero (con todas sus personas), en tiempo real.", "⚇", "#0f766f"),
    Pendiente(
        "con_personas", "Con personas",
        "Mensajes entre dos personas, por su alias. Antes hay que decidir cómo se cuida la privacidad y cómo se evita el acoso.",
        "⚉", "#1d4ed8",
    ),
    # Administrar
    Pendiente(
        "miembros", "Miembros",
        "Las personas de los grupos que administras, con su rol, su asamblea base y desde cuándo están.",
        "☰", "#c2410d", permiso="grupos.ver_arbol",
    ),
    Pendiente(
        "eventos_administrados", "Eventos de mis grupos",
        "Los eventos de los grupos que administras, también los pendientes de apoyos, para seguirlos y ayudar.",
        "✶", "#b91c1d", permiso="grupos.ver_arbol",
    ),
    Pendiente(
        "moderacion", "Moderación", "Avisos sobre contenido y ocultación provisional, en los grupos que administras.",
        "⚔", "#7f1d1d", permiso="grupos.ver_arbol",
    ),
    Pendiente(
        "web_publica", "Web pública", "La portada y el banco de recursos públicos de la organización.",
        "⌂", "#155e75", permiso="audiencias.configurar",
    ),
)

# Las mismas, por su clave.
POR_CLAVE = {pendiente.clave: pendiente for pendiente in PENDIENTES}


class ProximamenteConfig(ModuloConfig):
    """
    Contrato del módulo «proximamente»: una entrada de menú por cada herramienta que aún no existe
    (PENDIENTES), para ir organizando el menú antes de construirlas. Al pulsarlas, una página dice que aún
    están vacías y qué harán. Cuando se construye una de verdad, su módulo declara su entrada y se cambia
    su código en config/menu.py.
    """

    name = "proximamente"
    verbose_name = "Próximamente"
    capa = Capa.FUNCIONAL
    descripcion = "Las herramientas que aún no existen, con su sitio en el menú, para ir organizándolo."
    menu = tuple(
        EntradaDeMenu(
            codigo=f"proximamente.{pendiente.clave}",
            nombre=pendiente.nombre,
            url=f"proximamente:{pendiente.clave}",
            icono=pendiente.icono,
            color=pendiente.color,
            permiso=pendiente.permiso,
        )
        for pendiente in PENDIENTES
    )
