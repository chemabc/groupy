"""
Operaciones del módulo «consultas»: crearla (quién vota, fechas, cuándo y quién ve los resultados),
prepararle las preguntas antes de abrirse, pedir apoyos si la propone un miembro, votar (una persona, un voto, secreto), ver los resultados y
cerrarla (el resultado pasa al registro de decisiones con un eventos_sw).
"""

import hashlib
import hmac
import secrets
from collections import Counter
from types import SimpleNamespace

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
from grupos.models import Grupo, Pertenencia
from permisos.servicios import exigir, puede
from solicitudes.servicios import pedir

from . import urna
from .models import Consulta, Papeleta, Participacion, Pregunta, Respuesta

# Tipo de ancla de las consultas.
ANCLA = "consultas.consulta"
# Votos a partir de los cuales se enseña el desglose por grupos (con menos se podría adivinar quién votó qué).
MINIMO_PARA_DESGLOSE = 10


# ── Crear y preparar ─────────────────────────────────────────────────────────────────────────────────


# Crea una consulta (sin preguntas: se le ponen después, antes de que se abra). Devuelve la consulta. Si
# quien la crea administra el grupo («consultas.crear»), nace aceptada; si no, nace propuesta: solo la ve
# quien la propone, que le pone las preguntas y después pide apoyos (pedir_apoyos).
#   - usuario: quien la crea (necesita «consultas.crear» o «consultas.proponer» en el grupo).
#   - datos: titulo, descripcion, abre, cierra, resultados, publicar_el, cambiar_voto.
#   - visibilidad: quién vota (clave del selector).
#   - visibilidad_resultados: quién ve los resultados.
#   - ancla: (tipo, número) de aquello de lo que cuelga, o (None, None).
@transaction.atomic
def crear(usuario, grupo, datos, visibilidad, visibilidad_resultados, ancla=(None, None)):
    if puede(usuario, "consultas.crear", grupo=grupo):
        estado = Consulta.ACEPTADA
    else:
        exigir(usuario, "consultas.proponer", grupo=grupo)
        estado = Consulta.PROPUESTA
    if datos["cierra"] <= datos["abre"]:
        raise ValidationError("Se tiene que cerrar después de abrirse.")
    if datos["resultados"] == Consulta.EN_UNA_FECHA and (not datos.get("publicar_el") or datos["publicar_el"] < datos["cierra"]):
        raise ValidationError("La fecha de publicación de los resultados tiene que ser después del cierre.")
    consulta = Consulta(
        grupo=grupo, creador=usuario, visibilidad=visibilidad, visibilidad_resultados=visibilidad_resultados,
        audiencia=audiencia_de(visibilidad, grupo, personas=[usuario]), audiencia_resultados=audiencia_de(visibilidad_resultados, grupo, personas=[usuario]),
        ancla_tipo=ancla[0] or "", ancla_id=ancla[1], estado=estado, **datos,
    )
    consulta.full_clean()
    consulta.save()
    return consulta


# Dice si a la consulta aún se le cambian las preguntas: no ha llegado su apertura y no está esperando
# apoyos (quien apoya tiene que ver lo mismo que se votará).
def en_preparacion(consulta):
    if consulta.estado == Consulta.ESPERANDO:
        return False
    return consulta.estado == Consulta.PROPUESTA or timezone.now() < consulta.abre


# Dice si se puede votar ahora: está aceptada y entre su apertura y su cierre.
def abierta(consulta):
    return consulta.estado == Consulta.ACEPTADA and consulta.abre <= timezone.now() < consulta.cierra and consulta.cerrada_el is None


# De unas consultas, las que congelan lo que cuelga de ellas (sus documentos de contexto): las que ya se
# han abierto (también después de cerrarse), para que todo el mundo vote sobre lo mismo. La pregunta el
# módulo «documentos» a través del contrato (Ancla.congela). Una consulta, sean cuantas sean.
#   - consultas: los números de las consultas.
def congela(consultas):
    return set(Consulta.objects.filter(pk__in=list(consultas), estado=Consulta.ACEPTADA, abre__lte=timezone.now()).values_list("pk", flat=True))


# Pide al grupo los apoyos para abrir una consulta propuesta por un miembro. Desde entonces las preguntas ya
# no cambian; la solicitud las lleva escritas para que se sepa qué se apoya.
@transaction.atomic
def pedir_apoyos(usuario, consulta, justificacion=""):
    if consulta.creador_id != usuario.pk or consulta.estado != Consulta.PROPUESTA:
        raise ValidationError("Los apoyos los pide quien propone la consulta, una vez.")
    preguntas = list(consulta.preguntas.prefetch_related("respuestas"))
    if not preguntas:
        raise ValidationError("Ponle al menos una pregunta antes de pedir apoyos.")
    lineas = [f"Abrir la consulta «{consulta.titulo}» ({'voto secreto' if consulta.secreta else 'voto público: se verá qué vota cada persona'}):"]
    for pregunta in preguntas:
        respuestas = " / ".join(r.texto for r in pregunta.respuestas.all())
        lineas.append(f"- {pregunta.texto}" + (f" ({respuestas})" if respuestas else " (respuesta abierta)"))
    pedir(usuario, "consultas.abrir", consulta.grupo, "\n".join(lineas), justificacion, datos={"consulta_id": consulta.pk})
    consulta.estado = Consulta.ESPERANDO
    consulta.save(update_fields=["estado"])


# Acepta una consulta cuando su solicitud consigue los apoyos (la llama «solicitudes»; ver el
# TipoDeSolicitud «consultas.abrir»). Si su apertura ya pasó mientras esperaba, se abre ahora y se corren el
# cierre y la publicación para que dure lo mismo que se pensó. Devuelve su ancla.
#   - solicitud: la solicitud aceptada (sus datos llevan «consulta_id»).
def aceptar(solicitud):
    consulta = Consulta.objects.get(pk=solicitud.datos["consulta_id"])
    ahora = timezone.now()
    campos = ["estado"]
    if consulta.abre < ahora:
        retraso = ahora - consulta.abre
        consulta.abre, consulta.cierra = ahora, consulta.cierra + retraso
        if consulta.publicar_el:
            consulta.publicar_el += retraso
        campos += ["abre", "cierra", "publicar_el"]
    consulta.estado = Consulta.ACEPTADA
    consulta.save(update_fields=campos)
    return (ANCLA, consulta.pk)


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


# Dice si una persona ve la consulta: la creó, o está aceptada y vota en ella o ve sus resultados.
def ve(usuario, consulta):
    if consulta.creador_id == usuario.pk:
        return True
    return consulta.estado == Consulta.ACEPTADA and (puede_ver(usuario, consulta.audiencia_id) or puede_ver(usuario, consulta.audiencia_resultados_id))


# Consulta (sin ejecutar) de las consultas que ve una persona (las propuestas sin aceptar, solo quien las propone).
def visibles(usuario):
    aceptadas = Consulta.objects.filter(estado=Consulta.ACEPTADA)
    por_voto = filtrar_visibles(aceptadas, usuario).values("pk")
    por_resultados = filtrar_visibles(aceptadas, usuario, campo="audiencia_resultados").values("pk")
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


# Vota (una persona, un voto). Si la consulta deja cambiar el voto y ya había votado, la papeleta nueva
# sustituye a la anterior; si no, un segundo voto no se acepta.
# En una consulta secreta, la papeleta no se guarda aún: va a la urna (consultas/urna.py) y se guarda en
# tandas desordenadas, para que no se pueda emparejar con la fila de quién ha votado. En una pública, se
# guarda ya, con quién la vota.
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
    if not consulta.secreta:
        Papeleta.objects.update_or_create(consulta=consulta, usuario=usuario, defaults={"clave": f"{consulta.pk}:{usuario.pk}", "grupo_id": base, "respuestas": respuestas})
        return
    clave = clave_de_papeleta(consulta, usuario) if consulta.cambiar_voto else secrets.token_hex(32)
    # Lo último antes de terminar: si Redis fallara, no quedaría apuntado que ha votado.
    if urna.meter(consulta.pk, {"clave": clave, "grupo_id": base, "respuestas": respuestas}) >= urna.TANDA:
        vaciar_urna(consulta)


# Guarda en la base las papeletas que esperan en la urna de una consulta secreta, desordenadas. Se llama al
# juntarse una tanda y al cerrar la consulta (entonces, aunque sean menos).
def vaciar_urna(consulta):
    for papeleta in urna.sacar(consulta.pk):
        Papeleta.objects.update_or_create(
            clave=papeleta["clave"], defaults={"consulta": consulta, "grupo_id": papeleta["grupo_id"], "respuestas": papeleta["respuestas"]},
        )


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
# los textos de las abiertas, y el desglose por grupos si hay votos suficientes. En una consulta pública,
# también quién ha votado cada respuesta. Cuentan también las papeletas que esperan en la urna (sin
# guardarlas). Tres consultas, recorriendo las papeletas en memoria.
#   - preguntas: las de la consulta, con sus respuestas cargadas.
def resultados(consulta, preguntas):
    papeletas = list(consulta.papeletas.select_related("grupo", "usuario"))
    en_la_urna = urna.mirar(consulta.pk) if consulta.secreta else []
    if en_la_urna:
        grupos = Grupo.objects.in_bulk({p["grupo_id"] for p in en_la_urna if p["grupo_id"]})
        papeletas += [SimpleNamespace(respuestas=p["respuestas"], grupo=grupos.get(p["grupo_id"]), usuario=None) for p in en_la_urna]
    total = len(papeletas)
    con_desglose = total >= MINIMO_PARA_DESGLOSE
    salida = []
    for pregunta in preguntas:
        clave = str(pregunta.pk)
        if pregunta.tipo == Pregunta.ABIERTA:
            salida.append({"pregunta": pregunta, "textos": [p.respuestas[clave] for p in papeletas if clave in p.respuestas], "total": total})
            continue
        cuentas, por_grupo, quienes = Counter(), {}, {}
        for papeleta in papeletas:
            for elegida in papeleta.respuestas.get(clave, []):
                cuentas[elegida] += 1
                if papeleta.usuario is not None:
                    quienes.setdefault(elegida, []).append(papeleta.usuario.alias)
                if con_desglose:
                    nombre = papeleta.grupo.nombre if papeleta.grupo else "Sin asamblea base"
                    por_grupo.setdefault(nombre, Counter())[elegida] += 1
        filas = [
            {"respuesta": r, "votos": cuentas[r.pk], "porcentaje": round(100 * cuentas[r.pk] / total) if total else 0, "quienes": sorted(quienes.get(r.pk, []))}
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
    if consulta.estado != Consulta.ACEPTADA or consulta.cerrada_el is not None or timezone.now() < consulta.cierra:
        return
    consulta.cerrada_el = timezone.now()
    consulta.save(update_fields=["cerrada_el"])
    vaciar_urna(consulta)
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
    for consulta in Consulta.objects.filter(estado=Consulta.ACEPTADA, cerrada_el__isnull=True, cierra__lte=timezone.now()):
        cerrar(consulta)


# ── Calendario, Inicio y lo que cuelga ───────────────────────────────────────────────────────────────


# El cierre de cada consulta que ve una persona, para el calendario común (ver FuenteDeCalendario en
# consultas/apps.py). Una consulta.
def fechas(usuario, desde, hasta):
    lista = visibles(usuario).filter(estado=Consulta.ACEPTADA, cierra__gte=desde, cierra__lte=hasta)
    return [
        FechaDeCalendario(id=c.pk, titulo=f"Cierra: {c.titulo}", inicio=c.cierra, enlace=reverse("consultas:consulta", args=[c.pk]), categoria="consultas.cierres")
        for c in lista
    ]


# Tarjeta «Consultas por votar» de «Inicio → Panel»: las abiertas en las que vota y aún no ha votado.
# Dos consultas.
def por_votar(usuario):
    ahora = timezone.now()
    consulta = (
        filtrar_visibles(Consulta.objects.filter(estado=Consulta.ACEPTADA, abre__lte=ahora, cierra__gt=ahora, cerrada_el__isnull=True), usuario)
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
