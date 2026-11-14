"""
Piezas con las que se escribe la disposición del menú (config/menu.py), además de los códigos sueltos y de
los pares (código, (subsecciones…)). Ver docs/diseno.md, apartado 4, «Disposición del menú» y «Menú en
tres bloques».

- Bloque: un trozo del menú con un título («Administrar», «Plataforma») y un tono de color, para que se vea
  siempre si se está en lo propio o actuando por otras personas. El primer bloque no lleva título.
- Pestanas: una entrada cuyas subsecciones no salen en el menú de la izquierda, sino como pestañas arriba
  (por ejemplo, «Calendario y eventos»: Calendario · Eventos de mis grupos · Mis eventos · Convocar). Así se
  juntan en una sección pantallas de módulos distintos. Si la subsección elegida tiene varias vistas, salen
  en una segunda fila, más pequeña.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Bloque:
    """Un bloque del menú izquierdo, con su título y sus entradas."""

    # Título que se ve encima del bloque («Administrar»). Vacío: sin título (el bloque de lo propio).
    titulo: str
    # Tono de color del bloque: «» (el normal), «administrar» o «plataforma». La plantilla
    # (base/pagina.html) da a cada tono su franja de color, y la zona central, una banda que lo recuerda.
    tono: str
    # Las entradas del bloque, escritas como en el resto de la disposición.
    elementos: tuple
    # Frase de la banda que sale arriba en las pantallas del bloque («Estás administrando…»). Vacía: sin
    # banda.
    banda: str = ""


@dataclass(frozen=True)
class Pestanas:
    """Una entrada con sus subsecciones como pestañas arriba (no en el menú de la izquierda)."""

    # Código de la entrada.
    codigo: str
    # Códigos de sus subsecciones, en el orden de las pestañas.
    hijas: tuple
