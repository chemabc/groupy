"""
Consulta de ejemplo: «¿Qué día hacemos la asamblea?», de Lince (admin de GRU Henares) a su grupo, abierta una
semana, con una pregunta de respuesta única y otra abierta; Garza ya ha votado. La crea y borra la orden
«python manage.py ejemplos».
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from grupos.ejemplos import organizaciones_de_ejemplo
from grupos.models import Pertenencia

from . import servicios
from .models import Consulta, Pregunta

# Título de la consulta de ejemplo (sirve para saber si ya está).
TITULO = "¿Qué día hacemos la asamblea?"


# Crea la consulta de ejemplo, si no está ya y existen Lince (admin de un grupo) y Garza.
def crear():
    personas = {u.alias: u for u in get_user_model().objects.filter(alias__in=["Lince", "Garza"])}
    admin = Pertenencia.objects.filter(usuario=personas.get("Lince"), rol=Pertenencia.ADMIN_GRUPO).select_related("grupo").first() if "Lince" in personas else None
    if admin is None or "Garza" not in personas or Consulta.objects.filter(titulo=TITULO).exists():
        return
    ahora = timezone.now()
    datos = {"titulo": TITULO, "descripcion": "Para el curso que viene.", "abre": ahora + timedelta(minutes=1), "cierra": ahora + timedelta(days=7),
             "resultados": Consulta.AL_CERRAR, "publicar_el": None, "cambiar_voto": True}
    consulta = servicios.crear(personas["Lince"], admin.grupo, datos, "grupo:0", "grupo:0")
    dia = servicios.anadir_pregunta(personas["Lince"], consulta, "¿Qué día?", Pregunta.UNICA, respuestas=["Martes", "Jueves", "Sábado por la mañana"])
    servicios.anadir_pregunta(personas["Lince"], consulta, "¿Algo más?", Pregunta.ABIERTA)
    Consulta.objects.filter(pk=consulta.pk).update(abre=ahora - timedelta(minutes=1))
    consulta.refresh_from_db()
    if servicios.puede_ver(personas["Garza"], consulta.audiencia_id):
        servicios.votar(personas["Garza"], consulta, {str(dia.pk): [dia.respuestas.all()[1].pk]})


# Borra las consultas de las organizaciones de ejemplo (con sus preguntas, participaciones y papeletas).
def borrar():
    Consulta.objects.filter(grupo__organizacion__in=organizaciones_de_ejemplo()).delete()
