"""
Operaciones del módulo «debates»: proponer (con su solicitud de apoyos), abrir al aceptarse, opciones
nuevas (se abren con apoyos), argumentos (con los límites), votos, facilitación, ampliar a más gente y
cerrar (la conclusión pasa al registro de decisiones con un eventos_sw).
"""

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from audiencias.selector import audiencia_de
from audiencias.servicios import filtrar_visibles, puede_ver
from base.anclas import buscar_ancla
from base.contrato import FilaDeResumen
from eventos_sw.servicios import emitir
from permisos.models import Cometido
from permisos.servicios import asignar_cometido, exigir, puede
from solicitudes.servicios import pedir

from .models import Argumento, Debate, LimitesDeDebate, Opcion, Voto

# Tipo de ancla de los debates.
ANCLA = "debates.debate"
# Cometido de quien facilita un debate.
FACILITACION = "debates.facilitacion"
# Votos de una opción que cuentan a favor y en contra (para la clasificación).
A_FAVOR = (Voto.MUY_IMPORTANTE, Voto.APOYO)
EN_CONTRA = (Voto.CONTRA, Voto.OPOSICION)
# Votos que se pueden dar a cada cosa.
VOTOS_DE_OPCION = (Voto.MUY_IMPORTANTE, Voto.APOYO, Voto.CONTRA, Voto.OPOSICION)
VOTOS_DE_ARGUMENTO = VOTOS_DE_OPCION + (Voto.REPETITIVO, Voto.NO_TIENE_QUE_VER)
# Votos que piden una justificación breve.
CON_JUSTIFICACION = (Voto.MUY_IMPORTANTE, Voto.OPOSICION)
# Límites de partida si nadie los ha puesto.
POR_DEFECTO = {"palabras_blando": 250, "palabras_duro": 400, "intervenciones_blando": 15, "intervenciones_duro": 20, "opciones_por_persona": 2, "apoyos_para_opcion": 2}
# Orden de amplitud de las visibilidades, para ampliar un debate (nunca reducirlo).
AMPLITUD = ["privado", "grupo:0", "grupo:1", "grupo:2", "grupo:3", "grupo:4", "grupo:5", "organizacion", "publico"]


# ── Límites ──────────────────────────────────────────────────────────────────────────────────────────


@dataclass
class Limites:
    """Los límites que valen en un debate: el más estricto de cada uno entre la plataforma y la organización."""

    palabras_blando: int | None
    palabras_duro: int | None
    intervenciones_blando: int | None
    intervenciones_duro: int | None
    opciones_por_persona: int | None
    apoyos_para_opcion: int
    fin_obligatorio: bool


# Los límites de una organización: los de la plataforma (o los de partida) y los suyos, el más estricto de
# cada uno. Una consulta.
#   - organizacion_id: la organización del grupo que debate.
def limites_de(organizacion_id):
    filas = {fila.organizacion_id: fila for fila in LimitesDeDebate.objects.filter(Q(organizacion__isnull=True) | Q(organizacion_id=organizacion_id))}
    valores = {}
    for campo, defecto in POR_DEFECTO.items():
        candidatos = [getattr(fila, campo) for fila in filas.values() if getattr(fila, campo) is not None]
        if None not in filas:
            candidatos.append(defecto)
        valores[campo] = min(candidatos) if candidatos else None
    valores["apoyos_para_opcion"] = valores["apoyos_para_opcion"] or POR_DEFECTO["apoyos_para_opcion"]
    valores["fin_obligatorio"] = any(fila.fin_obligatorio for fila in filas.values())
    return Limites(**valores)


# ── Proponer y abrir ─────────────────────────────────────────────────────────────────────────────────


# Propone un debate: queda «esperando apoyos» (solo lo ve quien lo propone) y se pide al grupo una
# solicitud con apoyos; al aceptarse, se abre solo. Si cuelga de algo, toma su grupo y su audiencia.
# Devuelve el debate.
#   - usuario: quien lo propone (necesita «debates.abrir» en el grupo).
#   - pregunta, descripcion: de qué va.
#   - opciones: textos de las opciones de partida (al menos dos).
#   - grupo, visibilidad: el grupo y quién participa, si no cuelga de nada.
#   - ancla: (tipo, número) de aquello de lo que cuelga, o (None, None).
#   - cierra: cuándo termina, o None.
#   - justificacion: para la solicitud.
@transaction.atomic
def proponer(usuario, pregunta, descripcion, opciones, grupo=None, visibilidad="grupo:0", ancla=(None, None), cierra=None, justificacion=""):
    textos = [texto.strip() for texto in opciones if texto.strip()]
    if len(textos) < 2:
        raise ValidationError("Un debate necesita al menos dos opciones.")
    elemento = buscar_ancla(*ancla) if ancla[0] else None
    if ancla[0] and elemento is None:
        raise ValidationError("Aquello de lo que iba a colgar ya no existe.")
    if elemento is not None and getattr(elemento, "grupo_id", None):
        grupo = elemento.grupo
        if getattr(elemento, "audiencia_id", None):
            visibilidad = "heredada"
    exigir(usuario, "debates.abrir", grupo=grupo)
    if limites_de(grupo.organizacion_id).fin_obligatorio and cierra is None:
        raise ValidationError("Tu organización pide que cada debate diga cuándo se cierra.")
    debate = Debate.objects.create(
        pregunta=pregunta, descripcion=descripcion, grupo=grupo, visibilidad=visibilidad, creador=usuario, cierra=cierra,
        audiencia=audiencia_de("privado", grupo, personas=[usuario]), ancla_tipo=ancla[0] or "", ancla_id=ancla[1],
    )
    Opcion.objects.bulk_create(Opcion(debate=debate, texto=texto, autor=usuario, de_partida=True) for texto in textos)
    asignar_cometido(usuario, FACILITACION, ANCLA, debate.pk, grupo=grupo)
    pedir(usuario, "debates.abrir", grupo, f"Abrir el debate «{pregunta}»", justificacion, datos={"debate_id": debate.pk})
    return debate


# Abre el debate cuando su solicitud consigue los apoyos (la llama «solicitudes»; ver el TipoDeSolicitud
# «debates.abrir»). Le pone su audiencia: la de aquello de lo que cuelga o la elegida. Devuelve su ancla.
#   - solicitud: la solicitud aceptada (sus datos llevan «debate_id»).
def abrir(solicitud):
    debate = Debate.objects.select_related("grupo").get(pk=solicitud.datos["debate_id"])
    elemento = buscar_ancla(debate.ancla_tipo, debate.ancla_id) if debate.visibilidad == "heredada" else None
    if elemento is not None:
        debate.audiencia_id = elemento.audiencia_id
    else:
        debate.audiencia = audiencia_de(debate.visibilidad if debate.visibilidad != "heredada" else "grupo:0", debate.grupo, personas=[debate.creador] if debate.creador else [])
    debate.estado = Debate.ABIERTO
    debate.save(update_fields=["audiencia", "estado"])
    return (ANCLA, debate.pk)


# ── Ver y facilitación ───────────────────────────────────────────────────────────────────────────────


# Dice si una persona ve (y puede participar en) un debate: por su audiencia, o porque lo propuso.
def ve(usuario, debate):
    return debate.creador_id == usuario.pk or (debate.estado != Debate.PENDIENTE and puede_ver(usuario, debate.audiencia_id))


# Consulta (sin ejecutar) de los debates que ve una persona.
def visibles(usuario):
    abiertos = filtrar_visibles(Debate.objects.exclude(estado=Debate.PENDIENTE), usuario)
    return Debate.objects.filter(Q(pk__in=abiertos.values("pk")) | Q(creador=usuario))


# Quién facilita un debate: lista de Cometido (con su usuario). Una consulta.
def facilitacion(debate):
    return list(Cometido.objects.filter(codigo=FACILITACION, ancla_tipo=ANCLA, ancla_id=debate.pk).select_related("usuario"))


# Dice si una persona facilita el debate (o administra su grupo, que también puede).
#   - de_facilitacion: la lista de facilitacion() ya cargada.
def facilita(usuario, debate, de_facilitacion):
    return any(c.usuario_id == usuario.pk for c in de_facilitacion) or puede(usuario, "grupos.editar_grupo", grupo=debate.grupo_id)


# Da la facilitación a otra persona que ve el debate (lo hace quien facilita o la administración).
@transaction.atomic
def dar_facilitacion(quien, debate, persona):
    if not facilita(quien, debate, facilitacion(debate)):
        raise ValidationError("Solo quien facilita o la administración del grupo dan la facilitación.")
    if not ve(persona, debate):
        raise ValidationError("No ve este debate nadie con ese alias.")
    if not Cometido.objects.filter(usuario=persona, codigo=FACILITACION, ancla_tipo=ANCLA, ancla_id=debate.pk).exists():
        asignar_cometido(persona, FACILITACION, ANCLA, debate.pk, grupo=debate.grupo)


# Amplía el debate a más gente (otra visibilidad más amplia: el grupo padre, la organización…). Nunca se
# reduce: quien ya participaba seguiría viendo lo escrito.
#   - visibilidad: la clave nueva del selector.
@transaction.atomic
def ampliar(usuario, debate, visibilidad):
    if not facilita(usuario, debate, facilitacion(debate)):
        raise ValidationError("Solo quien facilita lo amplía.")
    actual = debate.visibilidad if debate.visibilidad in AMPLITUD else "grupo:0"
    if visibilidad not in AMPLITUD or AMPLITUD.index(visibilidad) <= AMPLITUD.index(actual):
        raise ValidationError("Un debate solo se amplía a más gente, nunca a menos.")
    debate.audiencia = audiencia_de(visibilidad, debate.grupo, personas=[debate.creador] if debate.creador else [])
    debate.visibilidad = visibilidad
    debate.save(update_fields=["audiencia", "visibilidad"])


# ── Participar ───────────────────────────────────────────────────────────────────────────────────────


# Comprueba que se puede participar: el debate está abierto (y no ha pasado su fecha de cierre) y la
# persona lo ve.
def _exigir_abierto(usuario, debate):
    if debate.estado != Debate.ABIERTO or (debate.cierra and debate.cierra <= timezone.now()):
        raise ValidationError("El debate no está abierto.")
    if not ve(usuario, debate):
        raise ValidationError("No participas en este debate.")


# Propone una opción nueva: nace «propuesta» y se abre cuando la apoyan las personas que piden los límites
# (2 de partida). Si es de consenso, esos apoyos tienen que venir de personas que habían apoyado opciones
# distintas (ver apoyos_de_consenso). Devuelve la opción.
#   - de_consenso: si se propone como síntesis de varias.
@transaction.atomic
def proponer_opcion(usuario, debate, texto, de_consenso=False):
    _exigir_abierto(usuario, debate)
    if not texto.strip():
        raise ValidationError("La opción está vacía.")
    limites = limites_de(debate.grupo.organizacion_id)
    suyas = Opcion.objects.filter(debate=debate, autor=usuario, de_partida=False).count()
    if limites.opciones_por_persona is not None and suyas >= limites.opciones_por_persona:
        raise ValidationError(f"Ya has propuesto {limites.opciones_por_persona} opciones en este debate.")
    return Opcion.objects.create(debate=debate, texto=texto.strip(), autor=usuario, de_consenso=de_consenso, estado=Opcion.PROPUESTA)


# Escribe un argumento a favor o en contra de una opción (o una respuesta a otro), con los límites: pasado
# el blando, se publica marcado; al llegar al duro, no se publica. Devuelve el argumento.
#   - opcion: la opción.
#   - texto: el argumento.
#   - a_favor: si es a favor (si no, en contra).
#   - padre: el argumento al que responde, o None.
@transaction.atomic
def argumentar(usuario, opcion, texto, a_favor=True, padre=None):
    debate = opcion.debate
    _exigir_abierto(usuario, debate)
    texto = texto.strip()
    if not texto:
        raise ValidationError("El argumento está vacío.")
    if opcion.estado != Opcion.ABIERTA:
        raise ValidationError("Esa opción aún no está abierta: necesita apoyos.")
    if padre is not None and padre.opcion_id != opcion.pk:
        raise ValidationError("La respuesta tiene que ser en la misma opción.")
    limites = limites_de(debate.grupo.organizacion_id)
    palabras = len(texto.split())
    if limites.palabras_duro is not None and palabras > limites.palabras_duro:
        raise ValidationError(f"Tiene {palabras} palabras y el límite es {limites.palabras_duro}. Acórtalo.")
    # Desde la última opción de consenso confirmada, se cuenta de cero para todo el mundo.
    hechas = Argumento.objects.filter(opcion__debate=debate, autor=usuario)
    if debate.intervenciones_desde:
        hechas = hechas.filter(creado__gte=debate.intervenciones_desde)
    hechas = hechas.count()
    if limites.intervenciones_duro is not None and hechas >= limites.intervenciones_duro:
        raise ValidationError(f"Ya has intervenido {hechas} veces en este debate: es el máximo.")
    # Al llegar al límite blando se permite una intervención más (marcada); después, ya no.
    if limites.intervenciones_blando is not None and hechas > limites.intervenciones_blando:
        raise ValidationError("Ya usaste tu intervención de más (la marcada). No puedes escribir más en este debate.")
    pasado = (limites.palabras_blando is not None and palabras > limites.palabras_blando) or (
        limites.intervenciones_blando is not None and hechas >= limites.intervenciones_blando
    )
    return Argumento.objects.create(opcion=opcion, padre=padre, autor=usuario, texto=texto, a_favor=a_favor, pasado=pasado)


# Vota una opción, un argumento o el debate entero («todas me valen»). Votar lo mismo otra vez lo quita;
# votar otra cosa lo cambia. ⭐ y ⛔ piden una justificación breve. Si una opción propuesta llega a los
# apoyos necesarios, se abre.
#   - opcion, argumento: lo que se vota (los dos None: el debate entero).
#   - tipo: Voto.TIPOS.
#   - justificacion: para ⭐ y ⛔.
@transaction.atomic
def votar(usuario, debate, tipo, opcion=None, argumento=None, justificacion=""):
    _exigir_abierto(usuario, debate)
    validos = VOTOS_DE_ARGUMENTO if argumento else VOTOS_DE_OPCION if opcion else (Voto.TODAS_ME_VALEN,)
    if tipo not in validos:
        raise ValidationError("Ese voto no vale aquí.")
    if tipo in CON_JUSTIFICACION and not justificacion.strip():
        raise ValidationError("⭐ y ⛔ piden una justificación breve (sale sin tu nombre).")
    if opcion is not None and opcion.estado == Opcion.PROPUESTA and tipo != Voto.APOYO:
        raise ValidationError("Una opción propuesta solo se apoya (👍); cuando se abra, ya se puede votar todo.")
    anterior = Voto.objects.filter(usuario=usuario, debate=debate, opcion=opcion, argumento=argumento).first()
    if anterior and anterior.tipo == tipo:
        anterior.delete()
        return None
    voto, _ = Voto.objects.update_or_create(
        usuario=usuario, debate=debate, opcion=opcion, argumento=argumento, defaults={"tipo": tipo, "justificacion": justificacion.strip()[:300]}
    )
    if opcion is not None and opcion.estado == Opcion.PROPUESTA:
        if opcion.de_consenso:
            apoyos = apoyos_de_consenso(opcion)
        else:
            apoyos = Voto.objects.filter(opcion=opcion, tipo=Voto.APOYO).exclude(usuario_id=opcion.autor_id).count()
        if apoyos >= limites_de(debate.grupo.organizacion_id).apoyos_para_opcion:
            opcion.estado = Opcion.ABIERTA
            opcion.save(update_fields=["estado"])
            if opcion.de_consenso:
                debate.intervenciones_desde = timezone.now()
                debate.save(update_fields=["intervenciones_desde"])
    return voto


# Cuántos apoyos válidos tiene una opción de consenso: cuántas de las personas que la apoyan (👍, sin contar
# a quien la propuso) habían apoyado (⭐ o 👍) opciones distintas del debate, cada una con una opción
# diferente. Por ejemplo, si Lince y Nutria apoyaban las dos «A» y Garza la «B», valen dos (una de A y una
# de B). Se calcula emparejando cada persona con una opción sin repetir. Dos consultas.
def apoyos_de_consenso(opcion):
    quienes = list(Voto.objects.filter(opcion=opcion, tipo=Voto.APOYO).exclude(usuario_id=opcion.autor_id).values_list("usuario_id", flat=True))
    antes = {}
    votos = Voto.objects.filter(debate_id=opcion.debate_id, usuario_id__in=quienes, argumento__isnull=True, tipo__in=A_FAVOR).exclude(opcion=opcion).exclude(opcion__isnull=True)
    for usuario_id, opcion_id in votos.values_list("usuario_id", "opcion_id"):
        antes.setdefault(usuario_id, set()).add(opcion_id)
    # Emparejamiento: cada persona busca una opción libre o se la quita a otra que pueda cambiar a otra libre.
    pareja_de_opcion = {}

    def emparejar(usuario_id, vistas):
        for opcion_id in antes.get(usuario_id, ()):
            if opcion_id in vistas:
                continue
            vistas.add(opcion_id)
            if opcion_id not in pareja_de_opcion or emparejar(pareja_de_opcion[opcion_id], vistas):
                pareja_de_opcion[opcion_id] = usuario_id
                return True
        return False

    return sum(1 for usuario_id in antes if emparejar(usuario_id, set()))


# ── Recuentos ────────────────────────────────────────────────────────────────────────────────────────


# Recuentos de un debate, sin nombres: por opción y por argumento, cuántos votos de cada tipo; las
# justificaciones de ⭐ y ⛔ de cada opción; cuántas personas dicen «todas me valen»; y los votos de quien
# mira (para marcar sus botones). Tres consultas.
#   - usuario: quien mira.
def recuentos(debate, usuario):
    por_opcion, por_argumento, todas = {}, {}, 0
    for opcion_id, argumento_id, tipo, numero in debate.votos.values_list("opcion_id", "argumento_id", "tipo").annotate(n=Count("pk")):
        if argumento_id:
            por_argumento.setdefault(argumento_id, {})[tipo] = numero
        elif opcion_id:
            por_opcion.setdefault(opcion_id, {})[tipo] = numero
        else:
            todas = numero
    justificaciones = {}
    for opcion_id, tipo, texto in debate.votos.filter(argumento__isnull=True, opcion__isnull=False, tipo__in=CON_JUSTIFICACION).exclude(justificacion="").values_list("opcion_id", "tipo", "justificacion"):
        justificaciones.setdefault(opcion_id, []).append((tipo, texto))
    mios = {(v.opcion_id, v.argumento_id): v.tipo for v in debate.votos.filter(usuario=usuario)}
    return por_opcion, por_argumento, justificaciones, todas, mios


# Cuántos votos a favor y en contra tiene algo, a partir de su diccionario de recuentos.
def balance(cuentas):
    a_favor = sum(cuentas.get(tipo, 0) for tipo in A_FAVOR)
    return a_favor, a_favor - sum(cuentas.get(tipo, 0) for tipo in EN_CONTRA)


# ── Cerrar ───────────────────────────────────────────────────────────────────────────────────────────


# Cierra el debate con una conclusión (y, si se elige, la opción ganadora). La conclusión se anuncia con
# «debates.cerrado» y pasa al registro de decisiones.
#   - usuario: quien facilita (o la administración del grupo).
#   - conclusion: lo que se decide, en una o dos frases.
#   - elegida: la Opcion elegida, o None.
@transaction.atomic
def cerrar(usuario, debate, conclusion, elegida=None):
    if debate.estado != Debate.ABIERTO:
        raise ValidationError("Solo se cierra un debate abierto.")
    if not facilita(usuario, debate, facilitacion(debate)):
        raise ValidationError("Solo quien facilita lo cierra.")
    if not conclusion.strip():
        raise ValidationError("Escribe la conclusión: es lo que pasa al registro de decisiones.")
    if elegida is not None and elegida.debate_id != debate.pk:
        raise ValidationError("Esa opción no es de este debate.")
    debate.estado, debate.cerrado_el, debate.conclusion, debate.elegida = Debate.CERRADO, timezone.now(), conclusion.strip(), elegida
    debate.save(update_fields=["estado", "cerrado_el", "conclusion", "elegida"])
    detalle = ""
    if elegida is not None:
        cuentas = dict(elegida.votos.filter(argumento__isnull=True).values_list("tipo").annotate(n=Count("pk")))
        a_favor, neto = balance(cuentas)
        detalle = f"Opción «{elegida.texto[:80]}»: {a_favor} a favor, neto {neto}"
    emitir(
        "debates.cerrado", texto=debate.conclusion, forma="debate", detalle=detalle, grupo_id=debate.grupo_id, audiencia_id=debate.audiencia_id,
        origen_tipo=ANCLA, origen_id=debate.pk, enlace=reverse("debates:debate", args=[debate.pk]), tomada=debate.cerrado_el.isoformat(),
    )


# ── Lo que cuelga de otra cosa ───────────────────────────────────────────────────────────────────────


# Los debates que cuelgan de algo y ve una persona, para el recuadro «Cuelga de aquí» (ver Colgante en
# debates/apps.py). Una consulta.
def colgantes(usuario, ancla_tipo, ancla_id):
    lista = visibles(usuario).filter(ancla_tipo=ancla_tipo, ancla_id=ancla_id).order_by("creado")
    return [FilaDeResumen(d.pregunta, reverse("debates:debate", args=[d.pk]), d.get_estado_display().lower()) for d in lista]
