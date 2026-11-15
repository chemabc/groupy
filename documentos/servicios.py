"""
Operaciones del módulo «documentos»: crear (suelto, colgado de algo o el acta a partir de su orden del
día), quién lo escribe, guardar con la autoría de cada párrafo y el registro de cambios, comentar y
aprobar (al aprobar un acta, sus acuerdos pasan al registro de decisiones con un eventos_sw).
"""

import difflib
import re
from datetime import datetime, timedelta
from datetime import timezone as zona

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from audiencias.selector import audiencia_de
from audiencias.servicios import filtrar_visibles, puede_ver
from base import editor
from base.anclas import buscar_ancla
from base.limites import mas_estricto
from base.contrato import FilaDeResumen
from eventos_sw.servicios import emitir
from grupos.models import Contencion
from permisos.models import Cometido
from permisos.servicios import asignar_cometido, exigir, puede

from .models import CambioDeDocumento, Comentario, ComentarioEnElTexto, Documento, LimitesDeDocumento, VersionDeDocumento

# Tipo de ancla de los documentos.
ANCLA = "documentos.documento"
# Cometido propio de quien escribe un documento.
REDACCION = "documentos.redaccion"
# Cometido de una reunión que también da permiso para escribir sus documentos (lo declara «eventos»; se
# nombra por su código, sin importar el módulo).
TOMA_DE_ACTA = "eventos.toma_de_acta"
# Minutos sin escribir tras los que el siguiente cambio empieza una versión nueva (ver VersionDeDocumento).
VERSION_CADA = 10
# Límites de partida, si el superadmin no ha puesto los de la plataforma: cuántas personas escriben (tienen
# la redacción) y cuántas comentan a la vez en el editor en tiempo real (None: sin límite).
POR_DEFECTO = {"max_escritores": 10, "max_comentaristas": None}
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
#   - formato: «markdown» (de partida) o «typst».
@transaction.atomic
def crear(usuario, tipo, titulo, grupo=None, visibilidad="privado", ancla=(None, None), texto=None, formato=Documento.MARKDOWN):
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
        texto = _en_formato(ODD_INICIAL if tipo == Documento.ODD else FINAL_DEL_ACTA.lstrip() if tipo == Documento.ACTA else "", formato)
    documento = Documento(
        tipo=tipo, titulo=titulo, grupo=grupo, audiencia=audiencia, ancla_tipo=ancla_tipo or "", ancla_id=ancla_id, creador=usuario, texto="",
        formato=formato,
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
    acta = crear(usuario, Documento.ACTA, titulo, ancla=(odd.ancla_tipo or None, odd.ancla_id), grupo=odd.grupo, texto=odd.texto.rstrip() + _en_formato(FINAL_DEL_ACTA, odd.formato), formato=odd.formato)
    if not odd.ancla_tipo:
        acta.audiencia = odd.audiencia
    acta.origen = odd
    acta.save(update_fields=["audiencia", "origen"])
    return acta


# Pasa un texto de partida (con títulos de Markdown, «## …») a Typst («== …»), para los documentos que se
# escriben en Typst. El resto de lo que llevan (listas con «- », «[consenso]») vale igual en los dos.
def _en_formato(texto, formato):
    return re.sub(r"^## ", "== ", texto, flags=re.M) if formato == Documento.TYPST else texto


# ── Límites ──────────────────────────────────────────────────────────────────────────────────────────


# Los límites que valen en un documento (o en un grupo, si aún no hay documento): de cada uno, el más
# estricto entre la plataforma (o los de partida), la organización, el grupo y sus antecesores y el propio
# documento. Devuelve {"max_escritores", "max_comentaristas"}. Dos consultas.
def limites_de(grupo, documento=None):
    antecesores = Contencion.objects.filter(descendiente_id=grupo.pk).values("antecesor_id")
    niveles = Q(organizacion__isnull=True, grupo__isnull=True, documento__isnull=True) | Q(organizacion_id=grupo.organizacion_id) | Q(grupo_id=grupo.pk) | Q(grupo_id__in=antecesores)
    if documento is not None and documento.pk:
        niveles |= Q(documento_id=documento.pk)
    filas = list(LimitesDeDocumento.objects.filter(niveles))
    plataforma = next((f for f in filas if not (f.organizacion_id or f.grupo_id or f.documento_id)), None)
    return mas_estricto(filas, POR_DEFECTO, plataforma)


# La fila de límites de un nivel (para cambiarla): la que hay o una nueva sin guardar.
def fila_de_limites(organizacion_id=None, grupo_id=None, documento_id=None):
    filtro = {"organizacion_id": organizacion_id, "grupo_id": grupo_id, "documento_id": documento_id}
    return LimitesDeDocumento.objects.filter(**filtro).first() or LimitesDeDocumento(**filtro)


# Dice si una persona puede cambiar las opciones de un documento (sus límites propios): la administración
# de su grupo o de su organización.
def puede_cambiar_opciones(usuario, documento):
    return puede(usuario, "documentos.limitar", grupo=documento.grupo_id)


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


# Da la redacción a otra persona que ve el documento (como mucho las que digan sus límites; de partida, 10). Lo hace quien ya redacta o
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
    maximo = limites_de(documento.grupo, documento)["max_escritores"]
    if maximo is not None and len(actuales) >= maximo:
        raise ValidationError(f"Ya hay {maximo} personas con la redacción (el máximo): quita a una antes.")
    asignar_cometido(persona, REDACCION, ANCLA, documento.pk, grupo=documento.grupo)


# Quita la redacción a una persona (ella misma, quien redacta o la administración). Siempre queda alguien.
@transaction.atomic
def quitar_redaccion(quien, documento, persona):
    if quien.pk != persona.pk and not (_redacta(quien, documento) or puede(quien, "grupos.editar_grupo", grupo=documento.grupo_id)):
        raise ValidationError("No puedes quitar la redacción a otra persona.")
    if len(redaccion(documento)) <= 1:
        raise ValidationError("Siempre tiene que haber alguien con la redacción.")
    Cometido.objects.filter(usuario=persona, codigo=REDACCION, ancla_tipo=ANCLA, ancla_id=documento.pk).delete()
    # En el editor en tiempo real, se cierra la sala: al volver, cada persona entra con su permiso de ahora.
    transaction.on_commit(lambda: editor.cerrar_sala(ANCLA, documento.pk))


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
#   - alias: quien cambia, o la lista de quienes han cambiado a la vez (en el editor en tiempo real).
def calcular_autorias(antes, despues, autorias, alias):
    quienes = list(alias) if isinstance(alias, (list, tuple)) else [alias]
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
            lista = [nombre for nombre in dict.fromkeys(previos) if nombre not in quienes] + quienes
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
#   - quien: el usuario que guarda, o la lista de alias que han escrito (desde el editor en tiempo real).
def _guardar_texto(documento, quien, texto, resumen=None):
    alias = quien if isinstance(quien, list) else str(quien)
    nuevas, calculado = calcular_autorias(parrafos(documento.texto), parrafos(texto), documento.autorias, alias)
    documento.texto, documento.autorias = texto, nuevas
    documento.version += 1
    documento.save()
    firma = ", ".join(alias) if isinstance(alias, list) else alias
    CambioDeDocumento.objects.create(documento=documento, alias=firma[:30], resumen=(resumen or calculado)[:200])
    _apuntar_version(documento, alias if isinstance(alias, list) else [alias], resumen or "")


# Apunta el texto actual en las versiones (función interna). Mientras se sigue escribiendo (menos de
# VERSION_CADA minutos desde el último cambio de una versión de edición), se pone al día la última; si no,
# o si hay un motivo («creado», «aprobado», «vuelta a la versión 3»), empieza una nueva.
#   - autores: los alias de quien escribe.
def _apuntar_version(documento, autores, motivo=""):
    ultima = documento.versiones.first()
    seguida = ultima is not None and not motivo and not ultima.motivo and timezone.now() - ultima.cerrada < timedelta(minutes=VERSION_CADA)
    if seguida:
        ultima.texto = documento.texto
        ultima.autores = list(dict.fromkeys(ultima.autores + autores))
        ultima.save(update_fields=["texto", "autores", "cerrada"])
        return
    VersionDeDocumento.objects.create(
        documento=documento, numero=(ultima.numero + 1) if ultima else 1, texto=documento.texto, autores=autores, motivo=motivo[:80],
    )


# Vuelve al texto de una versión anterior (queda como una versión nueva: no se pierde nada). Solo quien
# tiene la redacción y si es borrador. Cierra la sala del editor en tiempo real, que al volver toma este
# texto. Devuelve el documento.
#   - numero: el número de la versión.
@transaction.atomic
def volver_a_version(usuario, documento, numero):
    documento = Documento.objects.select_for_update().get(pk=documento.pk)
    if not puede_escribir(usuario, documento):
        raise ValidationError("Solo quien tiene la redacción vuelve a otra versión (y no si ya está aprobado).")
    version = documento.versiones.filter(numero=numero).first()
    if version is None:
        raise ValidationError("Esa versión no existe.")
    _guardar_texto(documento, usuario, version.texto, f"vuelta a la versión {numero}")
    transaction.on_commit(lambda: editor.cerrar_sala(ANCLA, documento.pk))
    return documento


# Guarda los comentarios hechos en el editor en tiempo real (los manda el editor, todos los de la sala,
# cada vez que cambian; ver TextoEditable en documentos/apps.py). Se ponen al día por su clave y no se
# borra ninguno: quedan registrados.
#   - comentarios: lista de {id, alias, texto, cuando (milisegundos), resuelto, cita, respuestas}.
@transaction.atomic
def guardar_comentarios_del_editor(numero, comentarios):
    documento = Documento.objects.get(pk=numero)
    for dato in comentarios:
        if not isinstance(dato, dict) or not dato.get("id") or not dato.get("texto"):
            continue
        ComentarioEnElTexto.objects.update_or_create(
            documento=documento, clave=str(dato["id"])[:40],
            defaults={
                "alias": str(dato.get("alias", ""))[:30], "texto": str(dato["texto"])[:5000], "cita": str(dato.get("cita", ""))[:2000],
                "cuando": datetime.fromtimestamp(int(dato.get("cuando") or 0) / 1000, tz=zona.utc), "resuelto": bool(dato.get("resuelto")),
                "respuestas": [
                    {"alias": str(r.get("alias", ""))[:30], "texto": str(r.get("texto", ""))[:5000], "cuando": int(r.get("cuando") or 0)}
                    for r in dato.get("respuestas", []) if isinstance(r, dict)
                ][:200],
            },
        )


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


# Cambia solo el título (desde la pantalla del editor en tiempo real, donde el texto se guarda solo).
@transaction.atomic
def cambiar_titulo(usuario, documento, titulo):
    if not puede_escribir(usuario, documento):
        raise ValidationError("Solo quien tiene la redacción puede cambiarlo (y no si ya está aprobado).")
    if titulo.strip() and titulo.strip() != documento.titulo:
        documento.titulo = titulo.strip()[:200]
        documento.save(update_fields=["titulo"])


# ── Editor en tiempo real (ver TextoEditable en documentos/apps.py y base/editor.py) ─────────────────


# Qué puede hacer una persona en la sala de un documento: «escribir» si tiene la redacción y es borrador;
# «comentar» si lo ve y es borrador; «leer» si lo ve; "" si no lo ve.
def permiso_en_editor(usuario, numero):
    documento = Documento.objects.filter(pk=numero).first()
    if documento is None or not ve(usuario, documento):
        return ""
    if puede_escribir(usuario, documento):
        return "escribir"
    return "comentar" if documento.estado == Documento.BORRADOR else "leer"


# Lo que el editor necesita saber además del permiso: el formato, el título (para el PDF) y cuántas personas
# pueden escribir y comentar a la vez.
def opciones_para_editor(numero):
    documento = Documento.objects.select_related("grupo").get(pk=numero)
    return {"formato": documento.formato, "titulo": documento.titulo, **limites_de(documento.grupo, documento)}


# El texto con el que empieza la sala de un documento y su versión.
def texto_para_editor(numero):
    documento = Documento.objects.get(pk=numero)
    return documento.texto, documento.version


# Guarda lo escrito en el editor en tiempo real, con quién ha escrito (las autorías se reparten entre
# ellas). Si el documento ya está aprobado, no lo acepta. Devuelve la versión nueva.
#   - alias: los alias que han escrito desde el último guardado.
#   - version: la que tenía el editor (no se compara: mientras hay sala, manda el editor).
@transaction.atomic
def guardar_desde_editor(numero, texto, alias, version=None):
    documento = Documento.objects.select_for_update().get(pk=numero)
    if documento.estado != Documento.BORRADOR:
        raise ValidationError("El documento ya está aprobado: no admite cambios.")
    if texto != documento.texto:
        _guardar_texto(documento, [str(a)[:30] for a in alias] or ["(sin alias)"], texto)
    return documento.version


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
        if linea.startswith(("## ", "== ")):
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
    _apuntar_version(documento, [str(usuario)], "aprobado")
    # Quien está en la sala del editor en tiempo real sale y, al volver, ya solo puede leer.
    transaction.on_commit(lambda: editor.cerrar_sala(ANCLA, documento.pk))
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
