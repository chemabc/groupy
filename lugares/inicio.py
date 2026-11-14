"""
Tarjeta «Mi lugar» de «Inicio → Mis datos» (declarada en lugares/apps.py; dónde sale lo decide
config/inicio.py): el lugar que has elegido como tuyo (dónde trabajas), que es privado. El botón
«Editar» va a «Configuración de mi cuenta → Mis datos → Lugar».
"""

from django.urls import reverse

from base.contrato import ApartadoDeTarjeta, FilaDeResumen, ResumenDeTarjeta

from .models import LugarDePersona


# Hace el resumen de la tarjeta para una persona. Cuesta 1 consulta.
#   - usuario: quien mira.
def mi_lugar(usuario):
    eleccion = LugarDePersona.objects.select_related("lugar").filter(usuario=usuario).first()
    filas = ()
    if eleccion:
        filas = (FilaDeResumen(eleccion.lugar.nombre, detalle=eleccion.lugar.direccion or "privado: solo lo ves tú"),)
    return ResumenDeTarjeta(
        apartados=(ApartadoDeTarjeta(filas=filas, vacio="Aún no has elegido tu lugar."),),
        enlace=reverse("lugares:mi_lugar"),
        boton="Editar",
    )
