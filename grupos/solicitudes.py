"""
Lo que el módulo «grupos» aporta a «solicitudes»: el tipo «Entrar en un grupo» (declarado en
grupos/apps.py). Aquí están las funciones que comprueban si se puede pedir y que hacen entrar a la
persona cuando la solicitud se acepta.
"""

from django.core.exceptions import ValidationError

from .models import Pertenencia
from .servicios import admitir, grupos_de


# Comprueba que una persona puede pedir entrar en un grupo: no está ya en él (ni en uno de sus
# subgrupos, que la haría miembro). Lanza ValidationError si no.
#   - usuario: quien lo pide.
#   - grupo: el grupo.
def puede_pedir_entrar(usuario, grupo):
    if grupo.pk in grupos_de(usuario):
        raise ValidationError(f"Ya eres miembro de {grupo}.")


# Hace entrar a quien pidió entrar, como usuario normal. Si aún no tiene asamblea base, este grupo pasa a
# serlo. Devuelve None (no crea nada que se pueda anclar).
#   - solicitud: la solicitud aceptada.
def entrar(solicitud):
    sin_base = not Pertenencia.objects.filter(usuario_id=solicitud.solicitante_id, es_base=True).exists()
    if not Pertenencia.objects.filter(usuario_id=solicitud.solicitante_id, grupo_id=solicitud.grupo_id).exists():
        admitir(solicitud.solicitante, solicitud.grupo, es_base=sin_base)
    return None
