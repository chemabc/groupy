"""
Conversaciones con grupos: la sala de cada grupo, un solo hilo donde escriben todos sus miembros (como el
chat del grupo). Decidido en [A-56] (docs/diseno.md, apartado 17): una sala por grupo y solo para sus
miembros; más adelante quizá hilos o temas, como en Telegram.

Solo entra quien está en el grupo (una pertenencia directa): nadie de fuera, tampoco el superadmin ni
los admins de la organización si no son miembros. Lo usan las pantallas de «Comunicaciones →
Conversaciones → Con grupos» (comunicaciones/views.py).
"""

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Exists, F, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce, Greatest

from grupos.models import Grupo, Pertenencia

from .models import LecturaDeSala, MensajeDeGrupo

# Cuánto se guarda en la caché el número de salas con mensajes nuevos de cada persona (un día). Deja de
# usarse antes: con cada mensaje sube la versión, y al leer se borra el de quien lee.
DURACION_EN_CACHE = 60 * 60 * 24


# Dice si una persona está en un grupo (y, por tanto, puede leer y escribir en su sala). Una consulta.
#   - usuario: quién.
#   - grupo_id: el grupo.
def es_miembro(usuario, grupo_id):
    return Pertenencia.objects.filter(usuario=usuario, grupo_id=grupo_id).exists()


# Las salas de una persona: sus grupos, en orden de árbol, cada uno con cuántos mensajes nuevos tiene
# para ella («nuevos») y su último mensaje («ultimo», o None). 2 consultas, tenga los grupos que tenga.
#   - usuario: quién.
def salas_de(usuario):
    leido = Subquery(LecturaDeSala.objects.filter(usuario=usuario, grupo=OuterRef("pk")).values("ultimo_leido")[:1])
    nuevos = Subquery(
        MensajeDeGrupo.objects.filter(grupo=OuterRef("pk"), pk__gt=OuterRef("leido"))
        .exclude(autor=usuario)
        .order_by()
        .values("grupo")
        .annotate(n=Count("pk"))
        .values("n")[:1]
    )
    ultimo = Subquery(MensajeDeGrupo.objects.filter(grupo=OuterRef("pk")).order_by("-pk").values("pk")[:1])
    grupos = list(
        Grupo.objects.en_orden_de_arbol()
        .select_related("organizacion")
        .filter(pertenencias__usuario=usuario)
        .annotate(leido=Coalesce(leido, Value(0)))
        .annotate(nuevos=Coalesce(nuevos, Value(0)), id_ultimo=ultimo)
    )
    ultimos = MensajeDeGrupo.objects.in_bulk([grupo.id_ultimo for grupo in grupos if grupo.id_ultimo])
    for grupo in grupos:
        grupo.ultimo = ultimos.get(grupo.id_ultimo)
    return grupos


# Los últimos mensajes de la sala de un grupo, del más antiguo al más nuevo. Una consulta.
#   - grupo: el grupo.
#   - cuantos: cuántos, como mucho.
def mensajes(grupo, cuantos=100):
    ultimos = list(MensajeDeGrupo.objects.filter(grupo=grupo).order_by("-pk")[:cuantos])
    return list(reversed(ultimos))


# Escribe un mensaje en la sala de un grupo. Quien escribe debe estar en el grupo (lo comprueba aquí,
# además de la vista). Devuelve el mensaje.
#   - grupo: el grupo.
#   - autor: quien escribe.
#   - texto: el mensaje.
@transaction.atomic
def escribir(grupo, autor, texto):
    texto = texto.strip()
    if not texto:
        raise ValidationError("El mensaje está vacío.")
    if not es_miembro(autor, grupo.pk):
        raise ValidationError("Solo escriben en la sala las personas del grupo.")
    mensaje = MensajeDeGrupo.objects.create(grupo=grupo, autor=autor, firma=str(autor), texto=texto)
    # Lo propio cuenta como leído; los números de los demás dejan de valer (sube la versión).
    _apuntar_lectura(autor, grupo, mensaje.pk)
    transaction.on_commit(_subir_version)
    return mensaje


# Apunta que una persona ha leído la sala hasta un mensaje (si es más nuevo que lo que tenía). Lo llama la
# pantalla de la sala al abrirla y cada vez que pide los mensajes nuevos. Una consulta (dos la primera vez).
# El número del menú se borra de la caché siempre: es barato recalcularlo y así no hace falta otra
# consulta para saber si ha cambiado.
#   - usuario: quién.
#   - grupo: el grupo.
#   - hasta: número del último mensaje que ha visto.
def marcar_leida(usuario, grupo, hasta):
    if hasta:
        _apuntar_lectura(usuario, grupo, hasta)
        transaction.on_commit(lambda: cache.delete(_clave(usuario.pk)))


# Guarda la lectura sin bajarla nunca (se queda con el mayor de los dos números). Devuelve si ha cambiado
# algo. Una consulta si la persona ya tenía su fila (lo normal), dos la primera vez.
def _apuntar_lectura(usuario, grupo, hasta):
    filas = LecturaDeSala.objects.filter(usuario=usuario, grupo=grupo)
    if filas.update(ultimo_leido=Greatest(F("ultimo_leido"), Value(hasta))):
        return True
    _lectura, nueva = LecturaDeSala.objects.get_or_create(usuario=usuario, grupo=grupo, defaults={"ultimo_leido": hasta})
    return nueva


# Número de salas con mensajes nuevos de otras personas, para el menú («Con grupos (2)»). Sin consultas si
# está en la caché.
#   - usuario: quién.
def salas_sin_leer(usuario):
    clave = _clave(usuario.pk)
    numero = cache.get(clave)
    if numero is None:
        leido = Subquery(LecturaDeSala.objects.filter(usuario=usuario, grupo=OuterRef("grupo")).values("ultimo_leido")[:1])
        hay_nuevos = Exists(
            MensajeDeGrupo.objects.filter(grupo=OuterRef("grupo"), pk__gt=OuterRef("leido")).exclude(autor=usuario)
        )
        numero = (
            Pertenencia.objects.filter(usuario=usuario)
            .annotate(leido=Coalesce(leido, Value(0)))
            .filter(hay_nuevos)
            .count()
        )
        cache.set(clave, numero, DURACION_EN_CACHE)
    return numero


# Clave de la caché con el número de salas sin leer de una persona (con la versión de las salas).
def _clave(usuario_id):
    cache.add("comunicaciones:salas:version", 1, None)
    return f"comunicaciones:salas:v{cache.get('comunicaciones:salas:version', 1)}:{usuario_id}"


# Sube la versión de los números de salas sin leer: todos dejan de usarse y se recalculan al pedirlos.
def _subir_version():
    try:
        cache.incr("comunicaciones:salas:version")
    except ValueError:
        cache.set("comunicaciones:salas:version", 2, None)
