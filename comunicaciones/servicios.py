"""
Operaciones del módulo «comunicaciones»: repartir los avisos que declaran los módulos, marcarlos como
vistos, borrarlos y guardar las preferencias de cada persona. Las pantallas (comunicaciones/views.py)
llaman a estas funciones.
"""

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from base.registro import registro

from .models import Notificacion, PreferenciaDeAviso

# Cuánto se guarda en la caché el número de notificaciones sin ver de cada persona (un día). Se borra
# antes, en cuanto cambia (repartir, marcar, borrar).
DURACION_EN_CACHE = 60 * 60 * 24


# ── Repartir ─────────────────────────────────────────────────────────────────────────────────────────


# Reparte un aviso: llama a la función «preparar» de su tipo con los datos del eventos_sw y crea una
# notificación para cada persona que no lo haya desactivado. La llama la bandeja de eventos_sw (es la
# escucha asíncrona que el registro añade por cada tipo de aviso; ver base/registro.py). Devuelve
# cuántas notificaciones ha creado.
#   - aviso: código del tipo de aviso.
#   - datos: los del eventos_sw que lo ha disparado.
@transaction.atomic
def repartir(aviso, **datos):
    tipo = registro.avisos[aviso]
    preparados = import_string(tipo.preparar)(**datos)
    destinatarios = {usuario for preparado in preparados for usuario in preparado.usuarios}
    apagados = set(
        PreferenciaDeAviso.objects.filter(tipo=aviso, web=False, usuario_id__in=destinatarios).values_list("usuario_id", flat=True)
    )
    nuevas, avisados = [], set()
    for preparado in preparados:
        for usuario in preparado.usuarios:
            # Cada persona recibe el aviso una sola vez, aunque salga en varios grupos de destinatarios.
            if usuario in apagados or usuario in avisados:
                continue
            avisados.add(usuario)
            nuevas.append(Notificacion(usuario_id=usuario, tipo=aviso, origen=tipo.origen, texto=preparado.texto, enlace=preparado.enlace))
    Notificacion.objects.bulk_create(nuevas)
    _invalidar(avisados)
    return len(nuevas)


# ── Leer y borrar ────────────────────────────────────────────────────────────────────────────────────


# Número de notificaciones sin ver de una persona, para el menú («Notificaciones (3)»). Sin consultas si
# está en la caché.
#   - usuario: quién.
def sin_ver(usuario):
    clave = _clave(usuario.pk)
    numero = cache.get(clave)
    if numero is None:
        numero = Notificacion.objects.filter(usuario=usuario, vista_el__isnull=True).count()
        cache.set(clave, numero, DURACION_EN_CACHE)
    return numero


# Marca como vistas notificaciones de una persona (las indicadas o, sin indicar, todas). Devuelve
# cuántas ha marcado.
#   - usuario: de quién (solo se tocan las suyas).
#   - ids: números de las notificaciones, o None para todas.
@transaction.atomic
def marcar_vistas(usuario, ids=None):
    consulta = Notificacion.objects.filter(usuario=usuario, vista_el__isnull=True)
    if ids is not None:
        consulta = consulta.filter(pk__in=ids)
    marcadas = consulta.update(vista_el=timezone.now())
    _invalidar({usuario.pk})
    return marcadas


# Borra una notificación de una persona (la papelera de cada notificación). Devuelve si existía.
#   - usuario: de quién (solo puede borrar las suyas).
#   - pk: número de la notificación.
@transaction.atomic
def borrar(usuario, pk):
    borradas, _detalle = Notificacion.objects.filter(usuario=usuario, pk=pk).delete()
    _invalidar({usuario.pk})
    return bool(borradas)


# Borra todas las notificaciones ya vistas de una persona (botón «Limpiar las vistas»). Las que no ha
# visto se quedan. Devuelve cuántas ha borrado.
#   - usuario: de quién.
@transaction.atomic
def limpiar_vistas(usuario):
    borradas, _detalle = Notificacion.objects.filter(usuario=usuario, vista_el__isnull=False).delete()
    return borradas


# ── Preferencias ─────────────────────────────────────────────────────────────────────────────────────


# Deja activados para una persona exactamente los tipos de aviso indicados (en la web); los demás quedan
# desactivados. Solo se guardan filas para los desactivados: sin fila, el aviso está activado, así que
# los que se vuelven a activar se borran.
#   - usuario: de quién.
#   - activados: códigos de los tipos de aviso que quiere recibir.
@transaction.atomic
def poner_preferencias(usuario, activados):
    activados = set(activados) & set(registro.avisos)
    apagados = set(registro.avisos) - activados
    PreferenciaDeAviso.objects.filter(usuario=usuario, tipo__in=activados).delete()
    ya = set(PreferenciaDeAviso.objects.filter(usuario=usuario, tipo__in=apagados).values_list("tipo", flat=True))
    PreferenciaDeAviso.objects.bulk_create([PreferenciaDeAviso(usuario=usuario, tipo=tipo, web=False) for tipo in sorted(apagados - ya)])
    PreferenciaDeAviso.objects.filter(usuario=usuario, tipo__in=apagados).update(web=False)


# Códigos de los tipos de aviso que una persona ha desactivado. Una consulta.
def desactivados(usuario):
    return set(PreferenciaDeAviso.objects.filter(usuario=usuario, web=False).values_list("tipo", flat=True))


# ── Caché ────────────────────────────────────────────────────────────────────────────────────────────


# Clave de la caché con el número sin ver de una persona.
def _clave(usuario_id):
    return f"comunicaciones:sin_ver:{usuario_id}"


# Borra de la caché el número sin ver de unas personas, cuando termine bien la transacción en curso (si
# se borrara antes, otra petición podría volver a guardar el número viejo).
#   - usuarios: ids de las personas.
def _invalidar(usuarios):
    claves = [_clave(usuario) for usuario in usuarios]
    if claves:
        transaction.on_commit(lambda: cache.delete_many(claves))
