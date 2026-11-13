"""
Invalidación de la caché de audiencias cuando cambia algo de lo que depende qué ve cada persona. Con
señales de Django, para cubrir también la trastienda. Se conectan en AudienciasConfig.ready().
"""

from django.db.models.signals import post_delete, post_save

from grupos.models import Grupo, Pertenencia

from .models import Audiencia, GrupoDeAudiencia, PersonaDeAudiencia
from .servicios import invalidar_todos, invalidar_usuario


# Receptor para lo que afecta a una persona: sus pertenencias y su presencia en audiencias privadas.
def _invalidar_a_su_usuario(sender, instance, **resto):
    invalidar_usuario(instance.usuario_id)


# Receptor para lo que afecta a todo el mundo: mover grupos y crear o cambiar audiencias de grupos.
def _invalidar_a_todos(sender, **resto):
    invalidar_todos()


# Receptor para las audiencias: una nueva de toda la organización o pública cambia lo que ve todo el
# mundo; una privada, no (sus personas se invalidan una a una).
def _invalidar_si_no_es_privada(sender, instance, **resto):
    if instance.tipo != Audiencia.PRIVADA:
        invalidar_todos()


# Conecta los receptores. La llama AudienciasConfig.ready().
def conectar():
    for modelo in (Pertenencia, PersonaDeAudiencia):
        post_save.connect(_invalidar_a_su_usuario, sender=modelo, dispatch_uid=f"audiencias.{modelo.__name__}.guardar")
        post_delete.connect(_invalidar_a_su_usuario, sender=modelo, dispatch_uid=f"audiencias.{modelo.__name__}.borrar")
    for modelo in (Grupo, GrupoDeAudiencia):
        post_save.connect(_invalidar_a_todos, sender=modelo, dispatch_uid=f"audiencias.{modelo.__name__}.guardar")
        post_delete.connect(_invalidar_a_todos, sender=modelo, dispatch_uid=f"audiencias.{modelo.__name__}.borrar")
    post_save.connect(_invalidar_si_no_es_privada, sender=Audiencia, dispatch_uid="audiencias.Audiencia.guardar")
    post_delete.connect(_invalidar_si_no_es_privada, sender=Audiencia, dispatch_uid="audiencias.Audiencia.borrar")
