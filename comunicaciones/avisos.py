"""
Notificaciones del propio módulo «comunicaciones» (las reparte él mismo, como las de los demás; ver su
contrato en comunicaciones/apps.py). Se preparan unos segundos después del cambio, así que releen los datos.
"""

from django.contrib.auth import get_user_model

from base.contrato import AvisoPreparado

from .models import Bloqueo


# «Nutria ha bloqueado a Lince en las conversaciones entre personas.» A todos los superadmin (decidido en
# [A-56]: el bloqueo avisa al superadmin, para que pueda actuar si hay acoso). No cuenta nada de la
# conversación, que el superadmin no puede leer. Si ya se ha quitado el bloqueo, no avisa.
#   - bloqueo_id: el bloqueo.
def bloqueo(bloqueo_id, **resto):
    bloqueo = Bloqueo.objects.select_related("quien", "a_quien").filter(pk=bloqueo_id).first()
    if bloqueo is None:
        return []
    superadmins = tuple(get_user_model().objects.filter(es_superadmin=True, activo=True).values_list("pk", flat=True))
    texto = f"{bloqueo.quien} ha bloqueado a {bloqueo.a_quien} en las conversaciones entre personas."
    return [AvisoPreparado(usuarios=superadmins, texto=texto)]
