"""
Proyectos de ejemplo: «Huerto comunitario» de la asamblea base de Nutria, con un subproyecto («Riego»)
que tiene el suyo («Bomba solar»), unas tareas repartidas en las columnas del kanban, las etiquetas «Huerto» y «Barrio» («Elegir el panel»
espera al presupuesto de tuberías, así que está bloqueada sola) y unos recursos. Los crea y borra la orden
«python manage.py ejemplos».
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from grupos.models import Pertenencia
from tipologias.models import Tipologia

from .models import Proyecto, Tarea
from .servicios import anadir_recurso, crear_proyecto, crear_tarea

# Título del proyecto principal de ejemplo (sirve para saber si ya está y para borrarlo).
PRINCIPAL = "Huerto comunitario"


# Crea el árbol de ejemplo, si no está ya y existen Nutria (con asamblea base) y la tipología «Genérico».
def crear():
    nutria = get_user_model().objects.filter(alias="Nutria").first()
    base = Pertenencia.objects.filter(usuario=nutria, es_base=True).select_related("grupo__organizacion").first() if nutria else None
    generico = Tipologia.objects.filter(familia=Tipologia.PROYECTO, nombre="Genérico", organizacion__isnull=True).first()
    if base is None or generico is None or Proyecto.objects.filter(titulo=PRINCIPAL).exists():
        return
    hoy = timezone.localdate()
    huerto = crear_proyecto(
        nutria, generico, {"titulo": PRINCIPAL, "objetivo_general": "Un huerto para el barrio.", "limite": hoy + timedelta(days=120)},
        grupo=base.grupo, visibilidad="grupo:0", etiquetas=["Huerto", "Barrio"],
    )
    riego = crear_proyecto(nutria, generico, {"titulo": "Riego", "limite": hoy + timedelta(days=60)}, padre=huerto)
    bomba = crear_proyecto(nutria, generico, {"titulo": "Bomba solar"}, padre=riego)
    tareas = {}
    for titulo, proyecto, estado, dias in [
        ("Pedir permiso al distrito", huerto, Tarea.EN_CURSO, 10),
        ("Comprar semillas", huerto, Tarea.PENDIENTE, 20),
        ("Medir la parcela", huerto, Tarea.HECHA, None),
        ("Presupuesto de tuberías", riego, Tarea.PENDIENTE, 15),
    ]:
        limite = hoy + timedelta(days=dias) if dias else None
        tareas[titulo] = crear_tarea(nutria, {"titulo": titulo, "responsable": nutria, "estado": estado, "limite": limite}, proyecto=proyecto)
    crear_tarea(nutria, {"titulo": "Elegir el panel", "responsable": nutria}, proyecto=bomba, espera_a=[tareas["Presupuesto de tuberías"]])
    for nombre, cantidad, origen, conseguido in [
        ("Mangueras", "4", "Ferretería del barrio", False),
        ("Herramientas de cavar", "6", "Las trae la gente", True),
        ("Dinero para semillas", "80 €", "Bote de la asamblea", False),
    ]:
        recurso = anadir_recurso(nutria, huerto, {"nombre": nombre, "cantidad": cantidad, "origen": origen})
        if conseguido:
            recurso.conseguido = True
            recurso.save(update_fields=["conseguido"])


# Borra el árbol de ejemplo (con sus subproyectos y tareas).
def borrar():
    Proyecto.objects.filter(titulo=PRINCIPAL, padre__isnull=True).delete()
