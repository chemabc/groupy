"""
Notificaciones del módulo «talentos» (las reparte «comunicaciones»; ver talentos/apps.py).
"""

from django.urls import reverse

from base.contrato import AvisoPreparado
from grupos.models import Pertenencia

from .models import Ofrecimiento, PeticionDeTalentos
from .servicios import quienes_comparten


# «Admin de GRU Henares pide talentos para «Mudanza del local»: 2 × Furgoneta…» A quienes comparten
# alguno de los talentos pedidos con el grupo (o un subgrupo), menos a quien la hizo.
def peticion(peticion_id, **resto):
    peticion = PeticionDeTalentos.objects.select_related("grupo__organizacion").filter(pk=peticion_id).first()
    if peticion is None or peticion.estado != PeticionDeTalentos.ABIERTA:
        return []
    necesidades = list(peticion.necesidades.select_related("talento"))
    personas = set().union(*(quienes_comparten(necesidad.talento_id, peticion.grupo) for necesidad in necesidades))
    personas.discard(peticion.autor_id)
    lista = ", ".join(f"{necesidad.cantidad} × {necesidad.talento}" for necesidad in necesidades)
    texto = f"Admin de {peticion.grupo} pide talentos para «{peticion.asunto}»: {lista}. Tú compartes alguno con el grupo."
    return [AvisoPreparado(tuple(sorted(personas)), texto, reverse("talentos:peticion", args=[peticion.pk]))]


# «Nutria ofrece Furgoneta para «Mudanza del local».» A quien hizo la petición y a los admins del grupo.
def ofrecimiento(ofrecimiento_id, **resto):
    ofrecimiento = Ofrecimiento.objects.select_related("usuario", "necesidad__talento", "necesidad__peticion").filter(pk=ofrecimiento_id).first()
    if ofrecimiento is None:
        return []
    peticion = ofrecimiento.necesidad.peticion
    personas = set(Pertenencia.objects.filter(grupo_id=peticion.grupo_id, rol=Pertenencia.ADMIN_GRUPO).values_list("usuario_id", flat=True))
    if peticion.autor_id:
        personas.add(peticion.autor_id)
    personas.discard(ofrecimiento.usuario_id)
    texto = f"{ofrecimiento.usuario} ofrece {ofrecimiento.necesidad.talento} para «{peticion.asunto}»."
    return [AvisoPreparado(tuple(sorted(personas)), texto, reverse("talentos:peticion", args=[peticion.pk]))]
