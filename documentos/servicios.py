"""
Operaciones del módulo «documentos»: crear (suelto, colgado de algo o el acta a partir de su orden del
día), quién lo escribe, guardar con la autoría de cada párrafo y el registro de cambios, comentar y
aprobar (al aprobar un acta, sus acuerdos pasan al registro de decisiones con un eventos_sw).
"""

import difflib
import re

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from audiencias.selector import audiencia_de
from audiencias.servicios import filtrar_visibles, puede_ver
from base.anclas import buscar_ancla
from base.contrato import FilaDeResumen
from eventos_sw.servicios import emitir
from permisos.models import Cometido
from permisos.servicios import asignar_cometido, exigir, puede

from .models import CambioDeDocumento, Comentario, Documento

# Tipo de ancla de los documentos.
ANCLA = "documentos.documento"
# Cometido propio de quien escribe un documento.
REDACCION = "documentos.redaccion"
# Cometido de una reunión que también da permiso para escribir sus documentos (lo declara «eventos»; se
# nombra por su código, sin importar el módulo).
TOMA_DE_ACTA = "eventos.toma_de_acta"
# Cuántas personas, como mucho, tienen la redacción de un documento a la vez (docs/diseno.md, apartado 13).
MAXIMO_DE_REDACCION = 2
# Títulos fijos del final de un acta.
ACUERDOS = "Acuerdos alcanzados"
TEMAS = "Temas a discutir en la próxima reunión"

# Texto con el que empieza un orden del día nuevo.
ODD_INICIAL = """## Puntos

1. Lectura y aprobación del acta anterior
2. 
3. Ruegos y preguntas
"""
# Lo que se añade al final al crear un acta.
FINAL_DEL_ACTA = f"""

## Asistentes



## {ACUERDOS}

- [consenso] 

## {TEMAS}

- 
"""


# ── Crear ────────────────────────────────────────────────────────────────────────────────────────────


# Crea un documento. Si cuelga de algo (una reunión, un proyecto…), toma su grupo y su audiencia; si no,
# los que se eligen. Quien lo crea queda con la redacción. Devuelve el documento.
#   - usuario: quien lo crea (necesita «documentos.crear» en el grupo).
#   - tipo, titulo: Documento.TIPOS y su título.
#   - grupo, visibilidad: el grupo y la clave del selector («grupo:0»…), si no cuelga de nada.
#   - ancla: (tipo, número) de aquello de lo que cuelga, o (None, None).
#   - texto: el texto inicial (si no, el de su tipo).
@transaction.atomic
def crear(usuario, tipo, titulo, grupo=None, visibilidad="privado", ancla=(None, None), texto=None):
    ancla_tipo, ancla_id = ancla
    elemento = buscar_ancla(ancla_tipo, ancla_id) if ancla_tipo else None
    if ancla_tipo and elemento is None:
        raise ValidationError("Aquello de lo que iba a colgar ya no existe.")
    if elemento is not None and getattr(elemento, "audiencia_id", None) and getattr(elemento, "grupo_id", None):
        grupo, audiencia = elemento.grupo, elemento.audiencia
        if not (puede_ver(usuario, audiencia) or getattr(elemento, "convocante_id", None) == usuario.pk or getattr(elemento, "creador_id", None) == usuario.pk):
            raise ValidationError("No puedes colgar documentos de algo que no ves.")
    else:
        audiencia = audiencia_de(visibilidad, grupo, personas=[usuario])
    exigir(usuario, "documentos.crear", grupo=grupo)
    if texto is None:
        texto = ODD_INICIAL if tipo == Documento.ODD else FINAL_DEL_ACTA.lstrip() if tipo == Documento.ACTA else ""
    documento = Documento(
        tipo=tipo, titulo=titulo, grupo=grupo, audiencia=audiencia, ancla_tipo=ancla_tipo or "", ancla_id=ancla_id, creador=usuario, texto="",
    )
    documento.full_clean()
    documento.save()
    asignar_cometido(usuario, REDACCION, ANCLA, documento.pk, grupo=grupo)
    _guardar_texto(documento, usuario, texto, "creado")
    return documento


# Crea el acta de una reunión a partir de su orden del día: copia sus puntos y le añade los apartados
# fijos (asistentes, acuerdos alcanzados y temas para la próxima reunión). Devuelve el acta.
#   - usuario: quien la crea (debe poder escribir el orden del día).
#   - odd: el orden del día.
@transaction.atomic
def acta_desde(usuario, odd):
    if odd.tipo != Documento.ODD or not puede_escribir(usuario, odd, aunque_aprobado=True):
        raise ValidationError("Solo quien redacta el orden del día crea el acta a partir de él.")
    titulo = odd.titulo.replace("Orden del día", "Acta", 1) if odd.titulo.startswith("Orden del día") else f"Acta: {odd.titulo}"
    acta = crear(usuario, Documento.ACTA, titulo, ancla=(odd.ancla_tipo or None, odd.ancla_id), grupo=odd.grupo, texto=odd.texto.rstrip() + FINAL_DEL_ACTA)
    if not odd.ancla_tipo:
        acta.audiencia = odd.audiencia
    acta.origen = odd
    acta.save(update_fields=["audiencia", "origen"])
    return acta


# ── Quién escribe ────────────────────────────────────────────────────────────────────────────────────


# Dice si una persona ve un documento: por su audiencia, o porque lo creó o lo redacta.
def ve(usuario, documento):
    return documento.creador_id == usuario.pk or puede_ver(usuario, documento.audiencia_id) or _redacta(usuario, documento)


# Consulta (sin ejecutar) de los documentos que ve una persona.
def visibles(usuario):
    propios = Cometido.objects.filter(usuario=usuario, codigo=REDACCION, ancla_tipo=ANCLA).values("ancla_id")
    return Documento.objects.filter(Q(pk__in=filtrar_visibles(Documento.objects.all(), usuario).values("pk")) | Q(creador=usuario) | Q(pk__in=propios))


# Dice si una persona tiene la redacción del documento (o la toma de acta de la reunión de la que cuelga).
def _redacta(usuario, documento):
    cometidos = Cometido.objects.filter(usuario=usuario)
    condicion = Q(codigo=REDACCION, ancla_tipo=ANCLA, ancla_id=documento.pk)
    if documento.ancla_tipo == "eventos.evento":
        condicion |= Q(codigo=TOMA_DE_ACTA, ancla_tipo=documento.ancla_tipo, ancla_id=documento.ancla_id)
    return cometidos.filter(condicion).exists()


# Dice si una persona puede escribir el documento: quien tiene su redacción (o la toma de acta de su
# reunión), mientras no esté aprobado.
#   - aunque_aprobado: para lo que se puede hacer también con un documento ya aprobado (crear el acta).
def puede_escribir(usuario, documento, aunque_aprobado=False):
    if documento.estado == Documento.APROBADO and not aunque_aprobado:
        return False
    return _redacta(usuario, documento)


# Dice si una persona puede aprobarlo: quien lo redacta o la administración del grupo.
def puede_aprobar(usuario, documento):
    return documento.estado == Documento.BORRADOR and (_redacta(usuario, documento) or puede(usuario, "grupos.editar_grupo", grupo=documento.grupo_id))


# Personas con la redacción del documento: lista de Cometido (con su usuario). Una consulta.
def redaccion(documento):
    return list(Cometido.objects.filter(codigo=REDACCION, ancla_tipo=ANCLA, ancla_id=documento.pk).select_related("usuario"))


# Da la redacción a otra persona que ve el documento (como mucho dos a la vez). Lo hace quien ya redacta o
# la administración del grupo.
#   - quien: quien lo hace.
#   - persona: a quién se le da.
@transaction.atomic
def dar_redaccion(quien, documento, persona):
    if not (_redacta(quien, documento) or puede(quien, "grupos.editar_grupo", grupo=documento.grupo_id)):
        raise ValidationError("Solo quien redacta o la administración del grupo dan la redacción.")
    if not ve(persona, documento):
        raise ValidationError("No ve este documento nadie con ese alias.")
    actuales = redaccion(documento)
    if any(c.usuario_id == persona.pk for c in actuales):
        return
    if len(actuales) >= MAXIMO_DE_REDACCION:
        raise ValidationError(f"Ya hay {MAXIMO_DE_REDACCION} personas con la redacción: quita a una antes.")
    asignar_cometido(persona, REDACCION, ANCLA, documento.pk, grupo=documento.grupo)


# Quita la redacción a una persona (ella misma, quien redacta o la administración). Siempre queda alguien.
@transaction.atomic
def quitar_redaccion(quien, documento, persona):
    if quien.pk != persona.pk and not (_redacta(quien, documento) or puede(quien, "grupos.editar_grupo", grupo=documento.grupo_id)):
        raise ValidationError("No puedes quitar la redacción a otra persona.")
    if len(redaccion(documento)) <= 1:
        raise ValidationError("Siempre tiene que haber alguien con la redacción.")
    Cometido.objects.filter(usuario=persona, codigo=REDACCION, ancla_tipo=ANCLA, ancla_id=documento.pk).delete()


# ── Guardar, autoría y registro ──────────────────────────────────────────────────────────────────────


# Parte un texto en párrafos (bloques separados por una línea en blanco), sin los vacíos. Un título solo
# («## Acuerdos») va junto con el bloque que le sigue, para que la autoría salga detrás del contenido y no
# detrás de cada título.
def parrafos(texto):
    resultado, titulo = [], ""
    for bloque in (b.strip() for b in re.split(r"\n\s*\n", texto or "")):
        if not bloque:
            continue
        if bloque.startswith("#") and "\n" not in bloque:
            titulo = f"{titulo}\n\n{bloque}" if titulo else bloque
            continue
        resultado.append(f"{titulo}\n\n{bloque}" if titulo else bloque)
        titulo = ""
    if titulo:
        resultado.append(titulo)
    return resultado


# Calcula quién ha contribuido a cada párrafo después de un cambio: los que no cambian conservan sus
# alias; los cambiados juntan los de los párrafos que reemplazan y ponen al final a quien cambia; los
# nuevos, solo a quien escribe. Devuelve (autorías nuevas, resumen del cambio).
#   - antes, despues: los párrafos de antes y de después.
#   - autorias: la lista de alias de cada párrafo de antes.
#   - alias: quien cambia.
def calcular_autorias(antes, despues, autorias, alias):
    autorias = list(autorias) + [[] for _ in range(len(antes) - len(autorias))]
    nuevas, cambiados, anadidos, quitados = [], 0, 0, 0
    for operacion, i1, i2, j1, j2 in difflib.SequenceMatcher(None, antes, despues, autojunk=False).get_opcodes():
        if operacion == "equal":
            nuevas.extend(list(autorias[i]) for i in range(i1, i2))
            continue
        if operacion == "delete":
            quitados += i2 - i1
            continue
        previos = [nombre for i in range(i1, i2) for nombre in autorias[i]]
        for _ in range(j1, j2):
            lista = [nombre for nombre in dict.fromkeys(previos) if nombre != alias] + [alias]
            nuevas.append(lista)
        if operacion == "replace":
            cambiados += min(i2 - i1, j2 - j1)
            anadidos += max(0, (j2 - j1) - (i2 - i1))
            quitados += max(0, (i2 - i1) - (j2 - j1))
        else:
            anadidos += j2 - j1
    partes = [f"{n} {texto}" for n, texto in ((cambiados, "cambiado(s)"), (anadidos, "nuevo(s)"), (quitados, "quitado(s)")) if n]
    return nuevas, ("párrafos: " + ", ".join(partes)) if partes else "sin cambios en el texto"


# Guarda el texto nuevo con su autoría y apunta el cambio en el registro (función interna).
def _guardar_texto(documento, usuario, texto, resumen=None):
    alias = str(usuario)
    nuevas, calculado = calcular_autorias(parrafos(documento.texto), parrafos(texto), documento.autorias, alias)
    documento.texto, documento.autorias = texto, nuevas
    documento.version += 1
    documento.save()
    CambioDeDocumento.objects.create(documento=documento, alias=alias, resumen=(resumen or calculado)[:200])


# Guarda los cambios de quien redacta. Si otra persona ha guardado desde que se abrió (la versión no
# coincide), no se guarda y se avisa, para no pisar su trabajo.
#   - usuario: quien guarda.
#   - titulo, texto: lo nuevo.
#   - version: la versión que tenía al abrirlo.
@transaction.atomic
def guardar(usuario, documento, titulo, texto, version):
    documento = Documento.objects.select_for_update().get(pk=documento.pk)
    if not puede_escribir(usuario, documento):
        raise ValidationError("Solo quien tiene la redacción puede escribirlo (y no si ya está aprobado).")
    if int(version) != documento.version:
        raise ValidationError("Otra persona ha guardado cambios mientras escribías. Copia tu texto, recarga la página y vuelve a ponerlo.")
    documento.titulo = titulo
    _guardar_texto(documento, usuario, texto)
    return documento


# Apunta un comentario de alguien que ve el documento (mientras es borrador).
@transaction.atomic
def comentar(usuario, documento, texto):
    if documento.estado != Documento.BORRADOR or not ve(usuario, documento):
        raise ValidationError("Solo se comenta un borrador que puedes ver.")
    if not texto.strip():
        raise ValidationError("El comentario está vacío.")
    return Comentario.objects.create(documento=documento, usuario=usuario, texto=texto.strip())


# ── Aprobar y acuerdos ───────────────────────────────────────────────────────────────────────────────


# Lee las líneas de lista de un apartado («## Título») de un texto: lista de textos, sin el guion.
#   - titulo: el título del apartado.
def _lineas_del_apartado(texto, titulo):
    dentro, lineas = False, []
    for linea in (texto or "").splitlines():
        if linea.startswith("## "):
            dentro = linea[3:].strip().lower() == titulo.lower()
            continue
        if dentro and re.match(r"^\s*[-*]\s+", linea):
            contenido = re.sub(r"^\s*[-*]\s+", "", linea).strip()
            if contenido:
                lineas.append(contenido)
    return lineas


# Los acuerdos de un acta: lista de (texto, forma, detalle). Cada línea de «Acuerdos alcanzados» puede
# empezar con «[consenso]» o «[votación 12-3-1]» (a favor, en contra, abstenciones); sin marca, consenso.
def acuerdos(documento):
    resultado = []
    for linea in _lineas_del_apartado(documento.texto, ACUERDOS):
        marca = re.match(r"^\[(consenso|votaci[oó]n)\s*([^\]]*)\]\s*(.*)$", linea, re.IGNORECASE)
        if marca:
            forma = "consenso" if marca.group(1).lower() == "consenso" else "votacion"
            detalle, texto = marca.group(2).strip(), marca.group(3).strip()
        else:
            forma, detalle, texto = "consenso", "", linea
        if texto:
            resultado.append((texto, forma, detalle))
    return resultado


# Los temas que quedan para la próxima reunión (líneas de su apartado).
def temas(documento):
    return _lineas_del_apartado(documento.texto, TEMAS)


# Aprueba un documento: ya no se puede cambiar. Si es un acta, cada acuerdo se anuncia con
# «documentos.acuerdo_tomado» (lo recoge el registro de decisiones).
#   - usuario: quien lo aprueba (quien redacta o la administración del grupo).
@transaction.atomic
def aprobar(usuario, documento):
    if not puede_aprobar(usuario, documento):
        raise ValidationError("Solo quien redacta o la administración del grupo lo aprueban, y solo si es un borrador.")
    documento.estado, documento.aprobado_el = Documento.APROBADO, timezone.now()
    documento.save(update_fields=["estado", "aprobado_el"])
    CambioDeDocumento.objects.create(documento=documento, alias=str(usuario), resumen="aprobado")
    if documento.tipo == Documento.ACTA:
        for texto, forma, detalle in acuerdos(documento):
            emitir(
                "documentos.acuerdo_tomado", texto=texto, forma=forma, detalle=detalle, grupo_id=documento.grupo_id,
                audiencia_id=documento.audiencia_id, origen_tipo=ANCLA, origen_id=documento.pk,
                enlace=reverse("documentos:documento", args=[documento.pk]), tomada=documento.aprobado_el.isoformat(),
            )


# ── Lo que cuelga de otra cosa ───────────────────────────────────────────────────────────────────────


# Los documentos que cuelgan de algo y ve una persona, para el recuadro «Cuelga de aquí» de su ficha (ver
# Colgante en documentos/apps.py). Una consulta.
def colgantes(usuario, ancla_tipo, ancla_id):
    lista = visibles(usuario).filter(ancla_tipo=ancla_tipo, ancla_id=ancla_id).order_by("creado")
    return [FilaDeResumen(d.titulo, reverse("documentos:documento", args=[d.pk]), f"{d.get_tipo_display()} · {d.get_estado_display().lower()}") for d in lista]
