"""
Debate de ejemplo: «¿Dónde hacemos el huerto?», de Lince en la asamblea base de Nutria (GRU Henares), ya
abierto, con tres opciones, unos argumentos (uno con respuesta), votos y una opción propuesta esperando
apoyos. Lo crea y borra la orden «python manage.py ejemplos».
"""

from django.contrib.auth import get_user_model

from grupos.ejemplos import organizaciones_de_ejemplo
from grupos.models import Pertenencia
from solicitudes.models import Solicitud

from . import servicios
from .models import Debate, Voto

# Pregunta del debate de ejemplo (sirve para saber si ya está).
PREGUNTA = "¿Dónde hacemos el huerto?"


# Crea el debate de ejemplo, si no está ya y existen Lince, Nutria (con su asamblea base) y Garza.
def crear():
    personas = {u.alias: u for u in get_user_model().objects.filter(alias__in=["Lince", "Nutria", "Garza"])}
    base = Pertenencia.objects.filter(usuario=personas.get("Nutria"), es_base=True).select_related("grupo").first() if "Nutria" in personas else None
    if base is None or len(personas) < 3 or Debate.objects.filter(pregunta=PREGUNTA).exists():
        return
    lince, nutria, garza = personas["Lince"], personas["Nutria"], personas["Garza"]
    debate = servicios.proponer(
        lince, PREGUNTA, "Tenemos tres sitios posibles. Hay que decidir antes de **marzo** para plantar a tiempo.",
        ["En el solar de la calle Mayor", "En la azotea del centro social", "En el parque"], grupo=base.grupo, justificacion="Hay que decidirlo ya.",
    )
    solicitud = Solicitud.objects.filter(tipo="debates.abrir", datos__debate_id=debate.pk).first()
    servicios.abrir(solicitud)
    Solicitud.objects.filter(pk=solicitud.pk).update(estado=Solicitud.ACEPTADA)
    debate.refresh_from_db()
    solar, azotea, parque = debate.opciones.all()
    agua = servicios.argumentar(nutria, solar, "Tiene una toma de agua al lado.")
    servicios.argumentar(garza, solar, "Pero el dueño puede pedirlo en cualquier momento.", a_favor=False, padre=agua)
    servicios.argumentar(lince, azotea, "Es nuestra y nadie nos la quita.")
    servicios.argumentar(garza, parque, "Haría falta permiso del ayuntamiento.", a_favor=False)
    servicios.votar(nutria, debate, Voto.MUY_IMPORTANTE, opcion=solar, justificacion="El agua es lo que más cuesta.")
    servicios.votar(garza, debate, Voto.APOYO, opcion=azotea)
    servicios.votar(lince, debate, Voto.APOYO, argumento=agua)
    servicios.proponer_opcion(garza, debate, "Repartirlo entre la azotea y el solar", de_consenso=True)


# Borra los debates de las organizaciones de ejemplo (con sus opciones, argumentos y votos).
def borrar():
    Debate.objects.filter(grupo__organizacion__in=organizaciones_de_ejemplo()).update(elegida=None)
    Debate.objects.filter(grupo__organizacion__in=organizaciones_de_ejemplo()).delete()
