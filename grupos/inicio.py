"""
Tarjeta «Mis grupos» de «Inicio → Mis datos» (declarada en grupos/apps.py; dónde sale lo decide
config/inicio.py): tus grupos en árbol, uno por organización, con tu rol en cada uno y tu asamblea base en
amarillo (el componente de grupos/arboles.py). Para cambiar de grupos, el botón lleva a pedir entrar en
uno («Comunicaciones → Solicitudes → Pedir algo»).
"""

from django.urls import reverse

from base.contrato import ApartadoDeTarjeta, ResumenDeTarjeta

from .arboles import arboles_de


# Hace el resumen de la tarjeta para una persona. Cuesta de 2 a 5 consultas (las de arboles_de).
#   - usuario: quien mira.
def mis_grupos(usuario):
    arboles = arboles_de(usuario)
    return ResumenDeTarjeta(
        apartados=() if arboles else (ApartadoDeTarjeta(vacio="Aún no estás en ningún grupo."),),
        enlace=reverse("solicitudes:nueva"),
        boton="Pedir entrar en un grupo",
        plantilla="grupos/arboles.html",
        contexto={"arboles": arboles, "leyenda": True},
    )
