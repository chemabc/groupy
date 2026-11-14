"""
Grafo de grupos («Organizaciones y grupos → Mis grupos → Grafo»): los mismos grupos que los árboles
(grupos/arboles.py), dibujados como un grafo de Mermaid, cada organización en su caja, con las relaciones
libres entre grupos («colabora», «apoya»…) como flechas de puntos. Ver docs/diseno.md, apartado 8.1,
«Grafo de grupos».

Aquí solo se escribe el texto del grafo (Mermaid lo convierte en dibujo en el navegador, con la isla
«documento» de interfaz.js, la misma de los diagramas de la ayuda) y la dirección de la ficha de cada
grupo, para que se pueda pulsar.
"""

from django.db.models import Q
from django.urls import reverse

from .arboles import arboles_de
from .models import Grupo, RelacionEntreGrupos

# Estilos de las cajas (los mismos colores que los árboles): organización violeta, asamblea base amarilla,
# heredados en gris, administrados con borde ámbar y los de fuera (solo por una relación) punteados.
ESTILOS = """  classDef organizacion fill:#ede9fe,stroke:#7c3aed,color:#3b0764
  classDef grupo fill:#ffffff,stroke:#64748b,color:#0f172a
  classDef base fill:#fde047,stroke:#a16207,color:#422006,font-weight:bold
  classDef heredado fill:#f8fafc,stroke:#cbd5e1,color:#94a3b8
  classDef administra fill:#ffffff,stroke:#d97706,stroke-width:2px,color:#0f172a
  classDef fuera fill:#f1f5f9,stroke:#94a3b8,stroke-dasharray:4 3,color:#64748b"""


# Pone un texto entre comillas para Mermaid: las comillas de dentro se cambian por su código (#quot;)
# para que no corten la etiqueta.
def _etiqueta(texto):
    return '"' + str(texto).replace('"', "#quot;") + '"'


# Texto del grafo de una persona y las direcciones de cada nodo. Devuelve (texto, enlaces): el texto en
# Mermaid y un diccionario {nombre del nodo: dirección de su ficha}. Vacío ("", {}) si no está en ningún
# grupo. Cuesta las consultas de arboles_de (de 2 a 5) más 1 o 2 de las relaciones.
#   - usuario: quien mira.
def grafo_de(usuario):
    arboles = arboles_de(usuario)
    if not arboles:
        return "", {}
    lineas = ["flowchart TB", ESTILOS]
    enlaces = {}
    vistos = set()

    # Escribe un grupo y sus subgrupos (con su flecha «contiene») dentro de la caja de su organización.
    def escribir(nodo, sangria):
        nombre = f"g{nodo.id}"
        vistos.add(nodo.id)
        clase = "base" if nodo.base else "heredado" if nodo.heredado else "administra" if nodo.administra and not nodo.directo else "grupo"
        texto = nodo.nombre + (f" · {nodo.rol}" if nodo.rol else "")
        lineas.append(f"{sangria}{nombre}[{_etiqueta(texto)}]:::{clase}")
        enlaces[nombre] = reverse("grupos:grupo", args=[nodo.id])
        for hijo in nodo.hijos:
            escribir(hijo, sangria)
            lineas.append(f"{sangria}{nombre} --> g{hijo.id}")

    for arbol in arboles:
        organizacion = arbol.organizacion
        lineas.append(f"  subgraph o{organizacion.pk}[{_etiqueta(organizacion.nombre)}]")
        for raiz in arbol.raices:
            escribir(raiz, "    ")
        lineas.append("  end")
        lineas.append(f"  class o{organizacion.pk} organizacion")
    # Relaciones libres que tocan a alguno de los grupos dibujados. El otro extremo, si no estaba, sale
    # punteado (se ve por la relación, como en «Relaciones»).
    relaciones = list(
        RelacionEntreGrupos.objects.filter(Q(origen_id__in=vistos) | Q(destino_id__in=vistos)).values_list("origen_id", "destino_id", "tipo")
    )
    fuera = {grupo for origen, destino, _tipo in relaciones for grupo in (origen, destino)} - vistos
    for grupo in Grupo.objects.filter(pk__in=fuera) if fuera else []:
        lineas.append(f"  g{grupo.pk}[{_etiqueta(grupo.nombre)}]:::fuera")
        enlaces[f"g{grupo.pk}"] = reverse("grupos:grupo", args=[grupo.pk])
    for origen, destino, tipo in relaciones:
        lineas.append(f"  g{origen} -. {_etiqueta(tipo)} .-> g{destino}")
    return "\n".join(lineas), enlaces
