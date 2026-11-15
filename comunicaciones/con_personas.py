"""
Conversaciones con personas: de dos en dos, por su alias. Decidido en [A-56] (docs/diseno.md, apartado
17):

- Se puede **empezar** una conversación con quien compartes algún grupo, sin petición previa.
- Cualquiera de las dos personas puede **bloquear** a la otra: desde entonces ninguna puede escribir a la
  otra hasta que quien bloqueó lo quite. Al bloquear, el superadmin recibe un aviso (eventos_sw
  «comunicaciones.bloqueo»), sin poder leer la conversación.
- Solo leen la conversación esas dos personas: ni la administración ni el superadmin (apartado 5.1).
- Una conversación que ya existe sigue aunque dejéis de compartir grupo (para cortarla está el bloqueo).

Lo usan las pantallas de «Comunicaciones → Conversaciones → Con personas» (comunicaciones/views.py).
"""

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from audiencias.cercania import Bloque, Cercania, GrupoCercano, PersonaCercana
from eventos_sw.servicios import emitir
from grupos.acceso import alcance_de, ve_miembros
from grupos.models import Grupo, Pertenencia

from .models import Bloqueo, ConversacionEntrePersonas, MensajeEntrePersonas

# Cuánto se guarda en la caché el número de conversaciones con algo sin leer de cada persona (un día). Se
# borra antes, en cuanto cambia (mensaje nuevo o lectura).
DURACION_EN_CACHE = 60 * 60 * 24


# ── A quién se puede escribir ────────────────────────────────────────────────────────────────────────


# Ids de las personas con las que una persona comparte algún grupo (sin ella misma). Una consulta.
#   - usuario: quién.
def comparten_grupo(usuario):
    return set(
        Pertenencia.objects.filter(grupo__pertenencias__usuario=usuario).exclude(usuario=usuario).values_list("usuario_id", flat=True)
    )


# Ids de las personas con las que hay un bloqueo, en un sentido o en el otro. Una consulta.
#   - usuario: quién.
def bloqueadas_con(usuario):
    ids = set()
    for quien, a_quien in Bloqueo.objects.filter(Q(quien=usuario) | Q(a_quien=usuario)).values_list("quien_id", "a_quien_id"):
        ids.add(a_quien if quien == usuario.pk else quien)
    return ids


# Ids de las personas a las que una persona puede empezar a escribir: las que comparten grupo con ella y
# no tienen un bloqueo de por medio. 2 consultas. Lo usa el selector de personas para comprobar lo elegido.
#   - usuario: quién.
def a_quien_puede_escribir(usuario):
    return comparten_grupo(usuario) - bloqueadas_con(usuario)


# La lista del selector de personas al escribir a alguien: por cada grupo de quien escribe, sus personas
# (sin las bloqueadas). Los grupos cuya lista de miembros no puede ver (su organización la ha cerrado) no
# salen; a esas personas se les puede escribir igual poniendo su alias exacto. Unas 4 consultas.
#   - usuario: quien escribe.
def lista_para_escribir(usuario):
    alcance = alcance_de(usuario)
    bloqueadas = bloqueadas_con(usuario)
    grupos = list(Grupo.objects.en_orden_de_arbol().select_related("organizacion").filter(pertenencias__usuario=usuario))
    visibles = [grupo for grupo in grupos if ve_miembros(usuario, grupo, alcance)]
    por_grupo = {grupo.pk: [] for grupo in visibles}
    filas = (
        Pertenencia.objects.filter(grupo__in=visibles)
        .exclude(usuario=usuario)
        .exclude(usuario__in=bloqueadas)
        .select_related("usuario")
        .order_by("usuario__alias")
    )
    for fila in filas:
        marca = "admin" if fila.rol == Pertenencia.ADMIN_GRUPO else ""
        por_grupo[fila.grupo_id].append(PersonaCercana(alias=str(fila.usuario), marca=marca))
    grupos_cercanos = tuple(
        GrupoCercano(nombre=grupo.nombre, personas=tuple(por_grupo[grupo.pk])) for grupo in visibles if por_grupo[grupo.pk]
    )
    bloque = Bloque(
        titulo="Personas de tus grupos",
        explicacion="Puedes escribir a quien comparte algún grupo contigo.",
        cercania="Cerca",
        nivel=0,
        grupos=grupos_cercanos,
    )
    return Cercania(ve_la_lista=bool(visibles), bloques=(bloque,) if grupos_cercanos else ())


# ── Conversaciones ───────────────────────────────────────────────────────────────────────────────────


# Las conversaciones de una persona, primero las que tienen algo sin leer, con la otra persona cargada y
# la marca «bloqueada» (si hay un bloqueo entre las dos) y «la_bloqueo_yo». 2 consultas.
#   - usuario: quién.
def conversaciones_de(usuario):
    filas = list(
        ConversacionEntrePersonas.objects.filter(Q(primera=usuario) | Q(segunda=usuario)).select_related("primera", "segunda")
    )
    bloqueos = list(Bloqueo.objects.filter(Q(quien=usuario) | Q(a_quien=usuario)).values_list("quien_id", "a_quien_id")) if filas else []
    mios = {a_quien for quien, a_quien in bloqueos if quien == usuario.pk}
    bloqueadas = mios | {quien for quien, a_quien in bloqueos if quien != usuario.pk}
    for conversacion in filas:
        conversacion.otra = conversacion.la_otra(usuario)
        conversacion.pendiente = conversacion.pendiente_para(usuario)
        conversacion.bloqueada = conversacion.otra.pk in bloqueadas
        conversacion.la_bloqueo_yo = conversacion.otra.pk in mios
    filas.sort(key=lambda conversacion: not conversacion.pendiente)
    return filas


# La conversación de una pareja, o None si aún no han hablado. Una consulta.
#   - una, otra: las dos personas.
def conversacion_entre(una, otra):
    primera, segunda = sorted((una.pk, otra.pk))
    return ConversacionEntrePersonas.objects.filter(primera_id=primera, segunda_id=segunda).first()


# Escribe a una persona: el primer mensaje (crea la conversación) o uno más. Para empezar hay que
# compartir grupo; con un bloqueo de por medio no se puede escribir. Devuelve la conversación.
#   - autor: quien escribe.
#   - destinataria: a quién.
#   - texto: el mensaje.
@transaction.atomic
def escribir(autor, destinataria, texto):
    texto = texto.strip()
    if not texto:
        raise ValidationError("El mensaje está vacío.")
    if autor.pk == destinataria.pk:
        raise ValidationError("No puedes escribirte a ti.")
    if hay_bloqueo(autor, destinataria):
        raise ValidationError("Hay un bloqueo entre vosotras dos: no se pueden enviar mensajes.")
    conversacion = conversacion_entre(autor, destinataria)
    if conversacion is None:
        if destinataria.pk not in comparten_grupo(autor):
            raise ValidationError("Solo puedes empezar una conversación con quien comparte algún grupo contigo.")
        primera, segunda = sorted((autor.pk, destinataria.pk))
        conversacion = ConversacionEntrePersonas.objects.create(primera_id=primera, segunda_id=segunda, iniciada_por=autor)
    mensaje = MensajeEntrePersonas.objects.create(conversacion=conversacion, autor=autor, texto=texto)
    # Solo se toca la marca de la otra persona, directamente en la base (como en las conversaciones con
    # la administración: así no se pisa lo que ella haya leído mientras tanto).
    campo = "pendiente_segunda" if conversacion.primera_id == autor.pk else "pendiente_primera"
    ConversacionEntrePersonas.objects.filter(pk=conversacion.pk).update(actualizada=mensaje.creado, **{campo: True})
    _invalidar(destinataria.pk)
    return conversacion


# Apunta que una persona ha leído su conversación. Siempre una consulta (la marca solo cambia si estaba
# puesta), para que la pantalla cueste lo mismo haya o no algo nuevo.
#   - conversacion: la conversación.
#   - usuario: una de las dos personas.
def marcar_leida(conversacion, usuario):
    campo = "pendiente_primera" if conversacion.primera_id == usuario.pk else "pendiente_segunda"
    if ConversacionEntrePersonas.objects.filter(pk=conversacion.pk, **{campo: True}).update(**{campo: False}):
        _invalidar(usuario.pk)
    setattr(conversacion, campo, False)


# Número de conversaciones con algo sin leer, para el menú («Con personas (1)»). Sin consultas si está en
# la caché.
#   - usuario: quién.
def sin_leer(usuario):
    clave = _clave(usuario.pk)
    numero = cache.get(clave)
    if numero is None:
        numero = ConversacionEntrePersonas.objects.filter(
            Q(primera=usuario, pendiente_primera=True) | Q(segunda=usuario, pendiente_segunda=True)
        ).count()
        cache.set(clave, numero, DURACION_EN_CACHE)
    return numero


# ── Bloqueos ─────────────────────────────────────────────────────────────────────────────────────────


# Quiénes han bloqueado, entre dos personas: un conjunto con los ids de quien bloqueó (vacío si no hay
# bloqueo; puede haber dos, si se han bloqueado las dos). Una consulta.
def bloqueos_entre(una, otra):
    return set(
        Bloqueo.objects.filter(Q(quien=una, a_quien=otra) | Q(quien=otra, a_quien=una)).values_list("quien_id", flat=True)
    )


# Dice si hay un bloqueo entre dos personas, en cualquier sentido. Una consulta.
def hay_bloqueo(una, otra):
    return Bloqueo.objects.filter(Q(quien=una, a_quien=otra) | Q(quien=otra, a_quien=una)).exists()


# Bloquea a una persona: desde ahora ninguna de las dos puede escribir a la otra. Avisa al superadmin
# (eventos_sw «comunicaciones.bloqueo»). Si ya estaba bloqueada, no hace nada. Devuelve el bloqueo.
#   - quien: quien bloquea.
#   - a_quien: la persona bloqueada.
@transaction.atomic
def bloquear(quien, a_quien):
    if quien.pk == a_quien.pk:
        raise ValidationError("No puedes bloquearte a ti.")
    bloqueo, nuevo = Bloqueo.objects.get_or_create(quien=quien, a_quien=a_quien)
    if nuevo:
        emitir("comunicaciones.bloqueo", bloqueo_id=bloqueo.pk)
    return bloqueo


# Quita el bloqueo que una persona puso a otra (solo quien bloqueó puede quitarlo). Devuelve si existía.
#   - quien: quien bloqueó.
#   - a_quien: la persona bloqueada.
@transaction.atomic
def desbloquear(quien, a_quien):
    borrados, _detalle = Bloqueo.objects.filter(quien=quien, a_quien=a_quien).delete()
    return bool(borrados)


# ── Caché ────────────────────────────────────────────────────────────────────────────────────────────


# Clave de la caché con el número de conversaciones sin leer de una persona.
def _clave(usuario_id):
    return f"comunicaciones:con_personas:{usuario_id}"


# Borra de la caché el número de una persona cuando termine bien la transacción en curso.
def _invalidar(usuario_id):
    transaction.on_commit(lambda: cache.delete(_clave(usuario_id)))

