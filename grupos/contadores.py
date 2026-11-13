"""
Números que el módulo «grupos» pone en el menú (ver EntradaDeMenu.contador en base/contrato.py).

Se piden en cada página, así que se guardan en la caché. La clave lleva un número de versión que sube
cada vez que cambia cualquier invitación (grupos/senales.py), así que nunca se ve un número viejo.
"""

import hashlib

from django.core.cache import cache
from django.db import transaction

from permisos.servicios import permisos_de

from .models import InvitacionDeGrupo

# Clave de la caché con la versión de los recuentos de invitaciones.
CLAVE_DE_VERSION = "grupos:invitaciones:version"
# Cuánto se guarda cada recuento, en segundos (un día). Normalmente se invalida antes.
DURACION_EN_CACHE = 60 * 60 * 24


# «Invitaciones (N)»: cuántas invitaciones pendientes puede responder la persona, es decir, las que han
# llegado a grupos donde tiene «grupos.responder_invitacion». El superadmin, todas las pendientes. Sin
# consultas si está en la caché, y 0 sin consultas si no puede responder ninguna.
#   - usuario: quien mira.
def invitaciones_pendientes(usuario):
    if usuario.is_superuser:
        grupos = None
    else:
        grupos = sorted(g for g, codigos in permisos_de(usuario).grupos.items() if "grupos.responder_invitacion" in codigos)
        if not grupos:
            return 0
    # La clave depende de los grupos (no de la persona): quienes responden por los mismos grupos
    # comparten el recuento.
    huella = "todas" if grupos is None else hashlib.sha1(",".join(map(str, grupos)).encode()).hexdigest()
    clave = f"grupos:invitaciones:v{_version()}:{huella}"
    numero = cache.get(clave)
    if numero is None:
        pendientes = InvitacionDeGrupo.objects.filter(estado=InvitacionDeGrupo.PENDIENTE)
        if grupos is not None:
            pendientes = pendientes.filter(grupo_invitado_id__in=grupos)
        numero = pendientes.count()
        cache.set(clave, numero, DURACION_EN_CACHE)
    return numero


# Número de versión actual de los recuentos (lo crea si no existe).
def _version():
    cache.add(CLAVE_DE_VERSION, 1, None)
    return cache.get(CLAVE_DE_VERSION, 1)


# Invalida todos los recuentos de invitaciones cuando termine bien la transacción en curso. La llaman
# las señales de grupos/senales.py al guardar o borrar una invitación (también desde la trastienda).
def invalidar_invitaciones():
    transaction.on_commit(_subir_version)


# Sube en uno la versión de los recuentos.
def _subir_version():
    try:
        cache.incr(CLAVE_DE_VERSION)
    except ValueError:  # La clave no existía (caché vacía): con crearla basta.
        cache.set(CLAVE_DE_VERSION, 2, None)
