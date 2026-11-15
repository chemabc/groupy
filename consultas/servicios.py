"""
Operaciones del módulo «consultas»: crearla (quién vota, fechas, cuándo y quién ve los resultados),
prepararle las preguntas antes de abrirse, votar (una persona, un voto, secreto), ver los resultados y
cerrarla (el resultado pasa al registro de decisiones con un eventos_sw).
"""

import hashlib
import hmac
import secrets
from collections import Counter

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from audiencias.selector import audiencia_de
from audiencias.servicios import filtrar_visibles, puede_ver
from base.contrato import ApartadoDeTarjeta, FechaDeCalendario, FilaDeResumen, ResumenDeTarjeta
from eventos_sw.servicios import emitir
from grupos.models import Pertenencia
from permisos.servicios import exigir

from .models import Consulta, Papeleta, Participacion, Pregunta, Respuesta

# Tipo de ancla de las consultas.
ANCLA = "consultas.consulta"
# Votos a partir de los cuales se enseña el desglose por grupos (con menos se podría adivinar quién votó qué).
MINIMO_PARA_DESGLOSE = 10


# ── Crear y preparar ─────────────────────────────────────────────────────────────────────────────────


# Crea una consulta (sin preguntas: se le ponen después, antes de que se abra). Devuelve la consulta.
#   - usuario: quien la crea (necesita «consultas.crear» en el grupo).
#   - datos: titulo, descripcion, abre, cierra, resultados, publicar_el, cambiar_voto.
#   - visibilidad: quién vota (clave del selector).
#   - visibilidad_resultados: quién ve los resultados.
#   - ancla: (tipo, número) de aquello de lo que cuelga, o (None, None).
@transaction.atomic
def crear(usuario, grupo, datos, visibilidad, visibilidad_resultados, ancla=(None, None)):
    exigir(usuario, "consultas.crear", grupo=grupo)
    if datos["cierra"] <= datos["abre"]:
        raise ValidationError("Se tiene que cerrar después de abrirse.")
    if datos["resultados"] == Consulta.EN_UNA_FECHA and (not datos.get("publicar_el") or datos["publicar_el"] < datos["cierra"]):
        raise ValidationError("La fecha de publicación de los resultados tiene que ser después del cierre.")
    consulta = Consulta(
        grupo=grupo, creador=usuario, visibilidad=visibilidad, visibilidad_resultados=visibilidad_resultados,
        audiencia=audiencia_de(visibilidad, grupo, personas=[usuario]), audiencia_resultados=audiencia_de(visibilidad_resultados, grupo, personas=[usuario]),
        ancla_tipo=ancla[0] or "", ancla_id=ancla[1], **datos,
    )
    consulta.full_clean()
    consulta.save()
    return consulta


# Dice si la consulta aún se prepara (no ha llegado su apertura): entonces se le cambian las preguntas.
def en_preparacion(consulta):
    return timezone.now() < consulta.abre


# Dice si se puede votar ahora.
def abierta(consulta):
    return consulta.abre <= timezone.now() < consulta.cierra and consulta.cerrada_el is None


# Añade una pregunta, con sus respuestas posibles (una por línea; las abiertas no llevan). Solo quien la
# creó y antes de que se abra.
#   - texto, tipo, documentacion: la pregunta (Pregunta.TIPOS).
#   - respuestas: lista de textos.
@transaction.atomic
def anadir_pregunta(usuario, consulta, texto, tipo, documentacion="", respuestas=()):
    if consulta.creador_id != usuario.pk or not en_preparacion(consulta):
        raise ValidationError("Las preguntas las pone quien crea la consulta, antes de que se abra.")
    textos = [r.strip() for r in respuestas if r.strip()]
    if tipo != Pregunta.ABIERTA and len(textos) < 2:
        raise ValidationError("Una pregunta de respuesta única o múltiple necesita al menos dos respuestas.")
    pregunta = Pregunta.objects.create(consulta=consulta, texto=texto, tipo=tipo, documentacion=documentacion, orden=consulta.preguntas.count())
    if tipo != Pregunta.ABIERTA:
        Respuesta.objects.bulk_create(Respuesta(pregunta=pregunta, texto=t, orden=n) for n, t in enumerate(textos))
    return pregunta


# Quita una pregunta (solo quien la creó y antes de que se abra).
@transaction.atomic
def quitar_pregunta(usuario, consulta, pregunta):
    if consulta.creador_id != usuario.pk or not en_preparacion(consulta) or pregunta.consulta_id != consulta.pk:
        raise ValidationError("Las preguntas las cambia quien crea la consulta, antes de que se abra.")
    pregunta.delete()


# ── Ver y votar ──────────────────────────────────────────────────────────────────────────────────────


# Dice si una persona ve la consulta: vota en ella, ve sus resultados o la creó.
def ve(usuario, consulta):
    return consulta.creador_id == usuario.pk or puede_ver(usuario, consulta.audiencia_id) or puede_ver(usuario, consulta.audiencia_resultados_id)


# Consulta (sin ejecutar) de las consultas que ve una persona.
def visibles(usuario):
    por_voto = filtrar_visibles(Consulta.objects.all(), usuario).values("pk")
    por_resultados = filtrar_visibles(Consulta.objects.all(), usuario, campo="audiencia_resultados").values("pk")
    return Consulta.objects.filter(Q(pk__in=por_voto) | Q(pk__in=por_resultados) | Q(creador=usuario))


# Clave de la papeleta de una persona en una consulta en la que se puede cambiar el voto: un resumen
# (HMAC) del par consulta-persona con un secreto del servidor. Con la base de datos sola no se puede saber
# de quién es; con el secreto, sí: por eso es provisional (la bóveda real, fase 8, lo resolverá).
def clave_de_papeleta(consulta, usuario):
    secreto = (settings.SECRET_KEY + ":consultas").encode()
    return hmac.new(secreto, f"{consulta.pk}:{usuario.pk}".encode(), hashlib.sha256).hexdigest()


# Comprueba las respuestas de un formulario y las deja como se guardan: {número de pregunta (texto):
# [números de respuesta] o "texto"}. Las preguntas sin responder no se guardan.
#   - preguntas: las de la consulta, con sus respuestas cargadas.
#   - datos: lo enviado (QueryDict): «p<número>» por pregunta.
def leer_respuestas(preguntas, datos):
    respuestas = {}
    for pregunta in preguntas:
        clave = f"p{pregunta.pk}"
        if pregunta.tipo == Pregunta.ABIERTA:
            texto = datos.get(clave, "").strip()[:2000]
            if texto:
                respuestas[str(pregunta.pk)] = texto
            continue
        validas = {r.pk for r in pregunta.respuestas.all()}
        elegidas = [int(v) for v in datos.getlist(clave) if v.isdigit() and int(v) in validas]
        if pregunta.tipo == Pregunta.UNICA and len(elegidas) > 1:
            raise ValidationError(f"«{pregunta.texto}» admite una sola respuesta.")
        if elegidas:
            respuestas[str(pregunta.pk)] = elegidas
    if not respuestas:
        raise ValidationError("No has respondido nada.")
    return respuestas


# Vota (una persona, un voto). Si la consulta deja cambiarlo y ya había votado, la papeleta nueva sustituye
# a la anterior; si no, un segundo voto no se acepta.
#   - respuestas: lo que devuelve leer_respuestas().
@transaction.atomic
def votar(usuario, consulta, respuestas):
    if not abierta(consulta):
        raise ValidationError("La consulta no está abierta.")
    if not puede_ver(usuario, consulta.audiencia_id):
        raise ValidationError("No votas en esta consulta.")
    ya, _nueva = Participacion.objects.get_or_create(consulta=consulta, usuario=usuario)
    if not _nueva and not consulta.cambiar_voto:
        raise ValidationError("Ya has votado y en esta consulta no se puede cambiar el voto.")
    base = Pertenencia.objects.filter(usuario=usuario, es_base=True).values_list("grupo_id", flat=True).first()
    if consulta.cambiar_voto:
        Papeleta.objects.update_or_create(clave=clave_de_papeleta(consulta, usuario), defaults={"consulta": consulta, "grupo_id": base, "respuestas": respuestas})
    else:
        Papeleta.objects.create(consulta=consulta, clave=secrets.token_hex(32), grupo_id=base, respuestas=respuestas)


# Dice si una persona ya ha votado.
def ha_votado(usuario, consulta):
    return Participacion.objects.filter(consulta=consulta, usuario=usuario).exists()


# ── Resultados y cierre ──────────────────────────────────────────────────────────────────────────────


# Dice si una persona ve ya los resultados: según cuándo se publican (al cerrar, en una fecha o en tiempo
# real) y si está entre quienes los ven (o la creó).
def ve_resultados(usuario, consulta):
    if not (consulta.creador_id == usuario.pk or puede_ver(usuario, consulta.audiencia_resultados_id)):
        return False
    ahora = timezone.now()
    if consulta.resultados == Consulta.EN_TIEMPO_REAL:
        return ahora >= consulta.abre
    if consulta.resultados == Consulta.EN_UNA_FECHA:
        return consulta.publicar_el is not None and ahora >= consulta.publicar_el
    return ahora >= consulta.cierra


# Los resultados de una consulta: por pregunta, cuántos votos tiene cada respuesta (con su porcentaje) o
# los textos de las abiertas, y el desglose por grupos si hay votos suficientes. Dos consultas, recorriendo
# las papeletas en memoria.
#   - preguntas: las de la consulta, con sus respuestas cargadas.
def resultados(consulta, preguntas):
    papeletas = list(consulta.papeletas.select_related("grupo"))
    total = len(papeletas)
    con_desglose = total >= MINIMO_PARA_DESGLOSE
    salida = []
    for pregunta in preguntas:
        clave = str(pregunta.pk)
        if pregunta.tipo == Pregunta.ABIERTA:
            salida.append({"pregunta": pregunta, "textos": [p.respuestas[clave] for p in papeletas if clave in p.respuestas], "total": total})
            continue
        cuentas, por_grupo = Counter(), {}
        for papeleta in papeletas:
            for elegida in papeleta.respuestas.get(clave, []):
                cuentas[elegida] += 1
                if con_desglose:
                    nombre = papeleta.grupo.nombre if papeleta.grupo else "Sin asamblea base"
                    por_grupo.setdefault(nombre, Counter())[elegida] += 1
        filas = [
            {"respuesta": r, "votos": cuentas[r.pk], "porcentaje": round(100 * cuentas[r.pk] / total) if total else 0}
            for r in pregunta.respuestas.all()
        ]
        desglose = [(nombre, [cuenta[r.pk] for r in pregunta.respuestas.all()]) for nombre, cuenta in sorted(por_grupo.items())]
        salida.append({"pregunta": pregunta, "filas": filas, "total": total, "desglose": desglose})
    return {"total": total, "preguntas": salida, "con_desglose": con_desglose}


# Da por cerrada una consulta cuya fecha de cierre ha pasado: anuncia el resultado con «consultas.cerrada»
# (lo recoge el registro de decisiones). No hace nada si aún no ha llegado su cierre o ya se cerró.
@transaction.atomic
def cerrar(consulta):
    consulta = Consulta.objects.select_for_update().get(pk=consulta.pk)
    if consulta.cerrada_el is not None or timezone.now() < consulta.cierra:
        return
    consulta.cerrada_el = timezone.now()
    consulta.save(update_fields=["cerrada_el"])
    preguntas = list(consulta.preguntas.prefetch_related("respuestas"))
    datos = resultados(consulta, preguntas)
    resumen = []
    for parte in datos["preguntas"]:
        if parte.get("filas"):
            ganadora = max(parte["filas"], key=lambda f: f["votos"])
            resumen.append(f"{parte['pregunta'].texto}: «{ganadora['respuesta'].texto}» ({ganadora['votos']} de {parte['total']})")
    emitir(
        "consultas.cerrada", texto=(f"{consulta.titulo}. " + "; ".join(resumen)) if resumen else consulta.titulo, forma="consulta",
        detalle=f"{datos['total']} votos", grupo_id=consulta.grupo_id, audiencia_id=consulta.audiencia_id, origen_tipo=ANCLA,
        origen_id=consulta.pk, enlace=reverse("consultas:consulta", args=[consulta.pk]), tomada=consulta.cierra.isoformat(),
    )


# Cierra todas las consultas cuya fecha de cierre ha pasado (tarea diaria del trabajador; ver
# consultas/apps.py). También se cierran solas al abrir su ficha.
def cerrar_vencidas():
    for consulta in Consulta.objects.filter(cerrada_el__isnull=True, cierra__lte=timezone.now()):
        cerrar(consulta)


# ── Calendario, Inicio y lo que cuelga ───────────────────────────────────────────────────────────────


# El cierre de cada consulta que ve una persona, para el calendario común (ver FuenteDeCalendario en
# consultas/apps.py). Una consulta.
def fechas(usuario, desde, hasta):
    lista = visibles(usuario).filter(cierra__gte=desde, cierra__lte=hasta)
    return [
        FechaDeCalendario(id=c.pk, titulo=f"Cierra: {c.titulo}", inicio=c.cierra, enlace=reverse("consultas:consulta", args=[c.pk]), categoria="consultas.cierres")
        for c in lista
    ]


# Tarjeta «Consultas por votar» de «Inicio → Panel»: las abiertas en las que vota y aún no ha votado.
# Dos consultas.
def por_votar(usuario):
    ahora = timezone.now()
    consulta = (
        filtrar_visibles(Consulta.objects.filter(abre__lte=ahora, cierra__gt=ahora, cerrada_el__isnull=True), usuario)
        .exclude(participaciones__usuario=usuario)
        .order_by("cierra")
    )
    filas = tuple(
        FilaDeResumen(c.titulo, reverse("consultas:consulta", args=[c.pk]), f"cierra el {timezone.localtime(c.cierra):%d/%m %H:%M}", destacada=True)
        for c in consulta[:5]
    )
    apartado = ApartadoDeTarjeta(filas=filas, total=consulta.count(), enlace=reverse("consultas:lista"), vacio="No tienes ninguna pendiente.")
    return ResumenDeTarjeta(apartados=(apartado,), enlace=reverse("consultas:lista"), boton="Ir a consultas")


# Las consultas que cuelgan de algo y ve una persona, para el recuadro «Cuelga de aquí». Una consulta.
def colgantes(usuario, ancla_tipo, ancla_id):
    lista = visibles(usuario).filter(ancla_tipo=ancla_tipo, ancla_id=ancla_id).order_by("cierra")
    return [FilaDeResumen(c.titulo, reverse("consultas:consulta", args=[c.pk]), f"cierra el {timezone.localtime(c.cierra):%d/%m/%Y}") for c in lista]
