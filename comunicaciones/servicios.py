"""
Operaciones del módulo «comunicaciones»: repartir los avisos que declaran los módulos, marcarlos como
vistos, borrarlos y guardar las preferencias de cada persona. Las pantallas (comunicaciones/views.py)
llaman a estas funciones.
"""

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.module_loading import import_string

from base.registro import registro
from grupos.models import Contencion, Pertenencia

from .administraciones import filtro_de_lo_que_atiende, grupos_que_alcanza
from .models import AvisoDeAdministracion, Conversacion, Mensaje, Notificacion, PreferenciaDeAviso

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


# ── Avisos de la administración ──────────────────────────────────────────────────────────────────────


# Envía un aviso de una administración a grupos (con todos sus subgrupos) y a personas sueltas, dentro
# de lo que alcanza esa administración. Cada persona recibe una notificación (una sola, aunque esté en
# varios de los grupos), con el color del nivel. No se puede desactivar en las preferencias: es de la
# administración. Devuelve el aviso.
#   - autor: el admin que lo escribe (debe atender esa administración; lo comprueba la vista).
#   - buzon: la administración en cuyo nombre se avisa (comunicaciones.administraciones.Buzon).
#   - nivel: el NivelDeAviso.
#   - asunto, texto: el aviso.
#   - grupos: grupos destinatarios.
#   - personas: usuarios destinatarios.
#   - permite_responder: si se puede abrir una conversación con la administración desde el aviso.
@transaction.atomic
def enviar_aviso(autor, buzon, nivel, asunto, texto, grupos=(), personas=(), permite_responder=False):
    alcance = grupos_que_alcanza(buzon)
    fuera = [grupo for grupo in grupos if grupo.pk not in alcance]
    if fuera:
        raise ValidationError(f"{buzon.nombre} no alcanza a {', '.join(str(g) for g in fuera)}.")
    if buzon.grupo or buzon.organizacion:
        dentro = set(Pertenencia.objects.filter(grupo_id__in=alcance, usuario__in=personas).values_list("usuario_id", flat=True))
        ajenas = [persona for persona in personas if persona.pk not in dentro]
        if ajenas:
            raise ValidationError(f"{', '.join(str(p) for p in ajenas)} no está en lo que alcanza {buzon.nombre}.")
    if not grupos and not personas:
        raise ValidationError("Elige al menos un grupo o una persona.")
    subarbol = Contencion.objects.filter(antecesor__in=grupos).values("descendiente_id")
    destinatarios = set(Pertenencia.objects.filter(grupo_id__in=subarbol).values_list("usuario_id", flat=True))
    destinatarios |= {persona.pk for persona in personas}
    destinatarios.discard(autor.pk)
    partes = [f"{grupo} y sus subgrupos" for grupo in grupos] + [str(persona) for persona in personas]
    aviso = AvisoDeAdministracion.objects.create(
        grupo=buzon.grupo, organizacion=buzon.organizacion, autor=autor, nivel=nivel, asunto=asunto, texto=texto,
        permite_responder=permite_responder, destinatarios="; ".join(partes), numero_de_personas=len(destinatarios),
    )
    origen = "superadmin" if not (buzon.grupo or buzon.organizacion) else "admins"
    enlace = reverse("comunicaciones:aviso", args=[aviso.pk])
    Notificacion.objects.bulk_create(
        Notificacion(
            usuario_id=usuario, tipo="comunicaciones.aviso_de_administracion", origen=origen,
            texto=f"{buzon.nombre}: {asunto}", enlace=enlace, aviso=aviso,
        )
        for usuario in sorted(destinatarios)
    )
    _invalidar(destinatarios)
    return aviso


# ── Conversaciones con la administración ─────────────────────────────────────────────────────────────


# Empieza una conversación de una persona con una administración, con su primer mensaje. Devuelve la
# conversación.
#   - persona: quien escribe.
#   - buzon: la administración (comunicaciones.administraciones.Buzon).
#   - asunto, texto: de qué trata y el primer mensaje.
#   - aviso: el aviso al que responde, si es el caso.
@transaction.atomic
def abrir_conversacion(persona, buzon, asunto, texto, aviso=None):
    conversacion = Conversacion.objects.create(
        persona=persona, grupo=buzon.grupo, organizacion=buzon.organizacion, asunto=asunto, aviso=aviso
    )
    escribir(conversacion, persona, texto, como_admin=False)
    return conversacion


# Añade un mensaje a una conversación. Si lo escribe un admin, firma con la administración y su alias
# («Admin de GRU Henares (Lince)») y la conversación queda pendiente de leer para la persona; si lo
# escribe la persona, para los admins. Devuelve el mensaje.
#   - conversacion: la conversación (con su grupo u organización cargados).
#   - autor: quien escribe.
#   - texto: el mensaje.
#   - como_admin: si escribe en nombre de la administración (lo decide la vista: quien la atiende).
@transaction.atomic
def escribir(conversacion, autor, texto, como_admin):
    texto = texto.strip()
    if not texto:
        raise ValidationError("El mensaje está vacío.")
    firma = f"{conversacion.nombre_de_la_administracion} ({autor})" if como_admin else str(autor)
    mensaje = Mensaje.objects.create(conversacion=conversacion, autor=autor, de_la_administracion=como_admin, firma=firma, texto=texto)
    # Solo se toca el campo de la otra parte, directamente en la base: si se guardaran los dos desde el
    # objeto en memoria, podría volver a marcarse como sin leer lo que otra persona ya había leído.
    campo = "pendiente_persona" if como_admin else "pendiente_admins"
    Conversacion.objects.filter(pk=conversacion.pk).update(actualizada=mensaje.creado, **{campo: True})
    conversacion.actualizada = mensaje.creado
    setattr(conversacion, campo, True)
    _invalidar_conversaciones()
    return mensaje


# Apunta que se ha leído una conversación: por la persona, o por la administración (cualquiera de sus
# admins).
#   - conversacion: la conversación.
#   - como_admin: si la lee un admin que la atiende.
@transaction.atomic
def marcar_leida(conversacion, como_admin):
    campo = "pendiente_admins" if como_admin else "pendiente_persona"
    if getattr(conversacion, campo):
        setattr(conversacion, campo, False)
        conversacion.save(update_fields=[campo])
        _invalidar_conversaciones()


# Cambia el estado de una conversación (abierta, en proceso, solucionada). Solo los admins (lo comprueba
# la vista).
@transaction.atomic
def cambiar_estado(conversacion, estado):
    if estado not in dict(Conversacion.ESTADOS):
        raise ValidationError(f"Estado desconocido: «{estado}».")
    conversacion.estado = estado
    conversacion.save(update_fields=["estado"])


# Número de conversaciones con algo sin leer para una persona: las suyas con respuesta de la
# administración y las de las administraciones que atiende con mensajes de la persona. Para el menú
# («Conversaciones (2)»). Sin consultas si está en la caché.
#   - usuario: quién.
def conversaciones_sin_leer(usuario):
    clave = f"comunicaciones:conversaciones:v{_version_de_conversaciones()}:{usuario.pk}"
    numero = cache.get(clave)
    if numero is None:
        filtro = filtro_de_lo_que_atiende(usuario)
        suyas = Q(persona=usuario, pendiente_persona=True)
        que_atiende = Q(pendiente_admins=True) & (filtro if filtro is not None else Q())
        numero = Conversacion.objects.filter(suyas | que_atiende).count()
        cache.set(clave, numero, DURACION_EN_CACHE)
    return numero


# Versión de los recuentos de conversaciones: sube con cada mensaje, lectura o conversación nueva, así
# que los números guardados en la caché dejan de usarse solos.
def _version_de_conversaciones():
    cache.add("comunicaciones:conversaciones:version", 1, None)
    return cache.get("comunicaciones:conversaciones:version", 1)


# Sube la versión de los recuentos de conversaciones cuando termine bien la transacción en curso.
def _invalidar_conversaciones():
    # Función interna: sube el número (o lo crea si la caché estaba vacía).
    def subir():
        try:
            cache.incr("comunicaciones:conversaciones:version")
        except ValueError:
            cache.set("comunicaciones:conversaciones:version", 2, None)

    transaction.on_commit(subir)


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
