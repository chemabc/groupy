"""
Conversaciones de ejemplo: unos mensajes en la sala de los grupos de Nutria y una conversación entre Nutria
y otra persona que comparte grupo con ella. Las crea y borra la orden «python manage.py ejemplos».
"""

from django.db.models import Q

from grupos.ejemplos import organizaciones_de_ejemplo
from grupos.models import Grupo, Pertenencia
from usuarios.ejemplos import usuarios_de_ejemplo

from . import con_grupos, con_personas
from .models import ConversacionEntrePersonas, MensajeDeGrupo

# Lo que se dice en cada sala de ejemplo, por turnos entre las personas del grupo.
FRASES_DE_SALA = [
    "¿Quién se encarga de abrir el local el sábado?",
    "Yo tengo las llaves, me encargo.",
    "Perfecto. Llevo la furgoneta para el material.",
    "Recordad que el acta de la última asamblea está en Documentos.",
]

# La conversación de ejemplo entre dos personas: (quién habla: 0 Nutria, 1 la otra; texto).
FRASES_ENTRE_PERSONAS = [
    (0, "¡Hola! ¿Te viene bien que preparemos juntas la propuesta del debate?"),
    (1, "Sí, claro. ¿Quedamos el jueves por la tarde?"),
    (0, "Hecho. Te escribo el miércoles para confirmar."),
]


# Escribe los mensajes de ejemplo en las salas de los dos primeros grupos de Nutria y la conversación con
# la primera persona que comparte grupo con ella. Si Nutria no existe (no hay usuarios de ejemplo), nada.
def crear():
    nutria = usuarios_de_ejemplo().filter(alias="Nutria").first()
    if nutria is None:
        return
    for grupo in Grupo.objects.filter(pertenencias__usuario=nutria).order_by("pk")[:2]:
        personas = [p.usuario for p in Pertenencia.objects.filter(grupo=grupo).select_related("usuario").order_by("usuario__alias")[:4]]
        for numero, frase in enumerate(FRASES_DE_SALA):
            con_grupos.escribir(grupo, personas[numero % len(personas)], frase)
    otra = usuarios_de_ejemplo().filter(pk__in=con_personas.comparten_grupo(nutria)).order_by("alias").first()
    if otra is not None:
        for quien, frase in FRASES_ENTRE_PERSONAS:
            con_personas.escribir(nutria if quien == 0 else otra, otra if quien == 0 else nutria, frase)


# Borra los mensajes de las salas de los grupos de ejemplo y las conversaciones entre usuarios de ejemplo.
def borrar():
    MensajeDeGrupo.objects.filter(grupo__organizacion__in=organizaciones_de_ejemplo()).delete()
    ejemplo = usuarios_de_ejemplo()
    ConversacionEntrePersonas.objects.filter(Q(primera__in=ejemplo) | Q(segunda__in=ejemplo)).delete()
