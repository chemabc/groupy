"""
Operaciones del módulo «limpieza» (ver docs/diseno.md, apartado 14.3). Cada módulo declara en su contrato
qué se puede limpiar (Limpiable) y cómo saber qué está terminado; aquí se decide qué toca cada día:

1. Lo terminado hace más de «archivar_a» días se archiva: su módulo lo saca de las listas (lo dice su
   campo «archivado») y aquí se apunta en la tabla Archivado. Se avisa a quienes lo ven.
2. Quince días antes de que se cumplan los «borrar_a» días desde que se archivó, se avisa a quienes lo
   ven, que pueden pulsar «Conservar» para que no se borre.
3. Pasado el plazo (y como pronto quince días después del aviso), se borra y se apunta en el registro
   de borrados.
4. Lo que se borra sin archivar (las notificaciones viejas) lo borra su propio módulo.

Todo lo hace la tarea diaria limpiar(), que ejecuta el trabajador una vez al día. Las pantallas
(limpieza/views.py) usan el resto: plazos, archivo, borrados, conservar y podar.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.module_loading import import_string

from audiencias.servicios import filtrar_visibles, puede_ver
from base.contrato import Limpiable
from base.registro import registro
from eventos_sw.servicios import emitir

from .models import Archivado, Borrado, Plazo

# Días que pasan como mínimo entre el aviso de que algo se va a borrar y su borrado.
AVISO_PREVIO = 15
# Cuántos elementos de cada tipo se archivan o se borran como mucho en una vuelta (lo que quede, al día
# siguiente). Así una primera limpieza con mucho atrasado no bloquea el trabajador.
LOTE = 2000


# ── Plazos ───────────────────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PlazoEfectivo:
    """Los plazos que valen ahora para un tipo de elemento: los del superadmin o, si no hay, los de partida."""

    # El tipo de elemento, tal como lo declara su módulo.
    limpiable: Limpiable
    # Si se limpia.
    activo: bool
    # Días desde que terminó hasta archivarlo.
    archivar_a: int
    # Días desde que se archivó hasta borrarlo (o desde que terminó, si se borra sin archivar).
    borrar_a: int
    # Si el superadmin los ha cambiado.
    cambiado: bool

    # Si se archiva antes de borrar (o se borra directamente, como las notificaciones).
    @property
    def con_archivo(self):
        return bool(self.limpiable.terminados)


# Los plazos de todos los tipos de elemento, por código, en el orden del registro. Una consulta.
def plazos():
    guardados = {plazo.tipo: plazo for plazo in Plazo.objects.all()}
    resultado = {}
    for codigo, limpiable in registro.limpiables.items():
        propio = guardados.get(codigo)
        if propio:
            resultado[codigo] = PlazoEfectivo(limpiable, propio.activo, propio.archivar_a, propio.borrar_a, True)
        else:
            resultado[codigo] = PlazoEfectivo(limpiable, True, limpiable.archivar_a, limpiable.borrar_a, False)
    return resultado


# Guarda los plazos que elige el superadmin para un tipo de elemento.
#   - tipo: código del tipo (debe existir en el registro).
#   - activo, archivar_a, borrar_a: lo elegido.
def guardar_plazo(tipo, activo, archivar_a, borrar_a):
    if tipo not in registro.limpiables:
        raise ValidationError("Ese tipo de elemento no existe.")
    Plazo.objects.update_or_create(tipo=tipo, defaults={"activo": activo, "archivar_a": archivar_a, "borrar_a": borrar_a})


# Vuelve a los plazos de partida de un tipo de elemento (borra lo que eligió el superadmin).
def plazo_de_partida(tipo):
    Plazo.objects.filter(tipo=tipo).delete()


# Qué día se borrará un elemento archivado, o None si no se borrará solo (está conservado o su tipo no
# se limpia).
#   - archivado: la fila de Archivado.
#   - plazo: el PlazoEfectivo de su tipo.
#   - ahora: el momento desde el que se mira.
def se_borra_el(archivado, plazo, ahora):
    if archivado.conservado_el or plazo is None or not plazo.activo:
        return None
    cumplido = archivado.archivado_el + timedelta(days=plazo.borrar_a)
    # Sin aviso todavía: como pronto, quince días después de avisar (hoy, en el peor caso).
    avisado = archivado.avisado_el or max(ahora, cumplido - timedelta(days=AVISO_PREVIO))
    return max(cumplido, avisado + timedelta(days=AVISO_PREVIO))


# ── La tarea diaria ──────────────────────────────────────────────────────────────────────────────────


# Tarea diaria «limpieza.limpiar»: quita del archivo lo que se ha reabierto, archiva lo terminado, avisa
# de lo que se borrará pronto, borra lo vencido y lo que se borra sin archivar. Devuelve un resumen
# {«archivados», «avisados», «borrados», «sin_archivo»} con cuántos de cada.
#   - ahora: el momento que se toma como «ahora» (las pruebas lo cambian).
def limpiar(ahora=None):
    ahora = ahora or timezone.now()
    vigentes = plazos()
    quitar_lo_reabierto(vigentes)
    return {
        "archivados": len(archivar(vigentes, ahora)),
        "avisados": len(avisar_de_borrado(vigentes, ahora)),
        "borrados": borrar_lo_vencido(vigentes, ahora),
        "sin_archivo": borrar_sin_archivar(vigentes, ahora),
    }


# Saca del archivo lo que su módulo ha reabierto (ya no tiene fecha de archivo) o ya no existe (lo ha
# borrado alguien). Devuelve cuántos ha quitado.
#   - vigentes: los plazos (de plazos()).
def quitar_lo_reabierto(vigentes):
    quitados = 0
    for codigo, plazo in vigentes.items():
        if not plazo.con_archivo:
            continue
        siguen = apps.get_model(plazo.limpiable.modelo).objects.filter(archivado__isnull=False).values("pk")
        quitados += Archivado.objects.filter(tipo=codigo).exclude(objeto_id__in=siguen).delete()[0]
    return quitados


# Archiva lo que terminó hace más de «archivar_a» días: le pone la fecha en su campo «archivado» y lo
# apunta en Archivado. Avisa a quienes lo ven (una notificación por persona, con cuántos). Devuelve los
# ids de las filas de Archivado nuevas.
#   - vigentes: los plazos (de plazos()).
#   - ahora: el momento de hoy.
@transaction.atomic
def archivar(vigentes, ahora):
    nuevos = []
    for codigo, plazo in vigentes.items():
        if not (plazo.activo and plazo.con_archivo):
            continue
        limpiable = plazo.limpiable
        terminados = import_string(limpiable.terminados)(ahora - timedelta(days=plazo.archivar_a))
        filas = list(terminados.values_list("pk", "titulo", "audiencia_id")[:LOTE])
        if not filas:
            continue
        ids = [pk for pk, _titulo, _audiencia in filas]
        apps.get_model(limpiable.modelo).objects.filter(pk__in=ids).update(archivado=ahora)
        nuevos += Archivado.objects.bulk_create(
            Archivado(
                tipo=codigo, objeto_id=pk, titulo=titulo[:200], enlace=reverse(limpiable.ficha, args=[pk]),
                audiencia_id=audiencia, archivado_el=ahora,
            )
            for pk, titulo, audiencia in filas
        )
    if nuevos:
        emitir("limpieza.archivados", archivados=[fila.pk for fila in nuevos])
    return [fila.pk for fila in nuevos]


# Avisa de lo que se va a borrar dentro de AVISO_PREVIO días (lo archivado, sin conservar y sin avisar
# aún, a quince días o menos de cumplir su plazo). Devuelve los ids de las filas de Archivado avisadas.
#   - vigentes: los plazos (de plazos()).
#   - ahora: el momento de hoy.
@transaction.atomic
def avisar_de_borrado(vigentes, ahora):
    avisados = []
    for codigo, plazo in vigentes.items():
        if not (plazo.activo and plazo.con_archivo):
            continue
        desde = ahora - timedelta(days=max(plazo.borrar_a - AVISO_PREVIO, 0))
        avisados += Archivado.objects.filter(
            tipo=codigo, avisado_el__isnull=True, conservado_el__isnull=True, archivado_el__lte=desde
        ).values_list("pk", flat=True)[:LOTE]
    if avisados:
        Archivado.objects.filter(pk__in=avisados).update(avisado_el=ahora)
        emitir("limpieza.se_borraran", archivados=avisados)
    return avisados


# Borra lo archivado que ha cumplido su plazo, sin conservar y avisado hace al menos AVISO_PREVIO días.
# Devuelve cuántos ha borrado.
#   - vigentes: los plazos (de plazos()).
#   - ahora: el momento de hoy.
def borrar_lo_vencido(vigentes, ahora):
    borrados = 0
    for codigo, plazo in vigentes.items():
        if not (plazo.activo and plazo.con_archivo):
            continue
        vencidos = Archivado.objects.filter(
            tipo=codigo, conservado_el__isnull=True,
            avisado_el__lte=ahora - timedelta(days=AVISO_PREVIO), archivado_el__lte=ahora - timedelta(days=plazo.borrar_a),
        )
        borrados += _borrar(list(vencidos[:LOTE]), Borrado.PLAZO)
    return borrados


# Llama al borrado propio de los tipos que se borran sin archivar (las notificaciones viejas). Devuelve
# cuántos se han borrado en total.
#   - vigentes: los plazos (de plazos()).
#   - ahora: el momento de hoy.
def borrar_sin_archivar(vigentes, ahora):
    total = 0
    for plazo in vigentes.values():
        if plazo.activo and not plazo.con_archivo:
            total += import_string(plazo.limpiable.borrar)(ahora - timedelta(days=plazo.borrar_a))
    return total


# Borra unos elementos archivados de su tabla (con lo que cuelga de ellos, como los subproyectos y las
# tareas de un proyecto), los apunta en el registro de borrados y los quita del archivo. Solo borra lo
# que sigue archivado en su módulo (si alguien lo ha reabierto, no). Devuelve cuántos ha borrado.
#   - archivados: filas de Archivado.
#   - motivo: Borrado.PLAZO o Borrado.A_MANO.
#   - quien: quién poda a mano, o None.
@transaction.atomic
def _borrar(archivados, motivo, quien=None):
    por_tipo = defaultdict(list)
    for archivado in archivados:
        por_tipo[archivado.tipo].append(archivado)
    registros = []
    for codigo, filas in por_tipo.items():
        limpiable = registro.limpiables.get(codigo)
        if limpiable is None:
            continue  # Su módulo ya no existe: se deja tal cual.
        modelo = apps.get_model(limpiable.modelo)
        siguen = modelo.objects.filter(pk__in=[fila.objeto_id for fila in filas], archivado__isnull=False)
        existentes = set(siguen.values_list("pk", flat=True))
        siguen.delete()
        registros += [
            Borrado(
                tipo=codigo, objeto_id=fila.objeto_id, titulo=fila.titulo, audiencia_id=fila.audiencia_id,
                archivado_el=fila.archivado_el, motivo=motivo, quien=quien,
            )
            for fila in filas
            if fila.objeto_id in existentes
        ]
    Borrado.objects.bulk_create(registros)
    Archivado.objects.filter(pk__in=[archivado.pk for archivado in archivados]).delete()
    return len(registros)


# ── Archivo y borrados ───────────────────────────────────────────────────────────────────────────────


# Consulta de lo archivado que ve una persona (lo mismo que veía el elemento). Sin ejecutar.
def archivados_visibles(usuario):
    return filtrar_visibles(Archivado.objects.all(), usuario)


# Consulta del registro de borrados que ve una persona (lo que veía cuando existía). Sin ejecutar.
def borrados_visibles(usuario):
    return filtrar_visibles(Borrado.objects.all(), usuario)


# «Conservar»: lo archivado ya no se borra solo (sigue archivado). Lo puede pulsar quien lo ve.
#   - usuario: quien lo pulsa.
#   - archivado: la fila de Archivado.
def conservar(usuario, archivado):
    if archivado.audiencia_id is None or not puede_ver(usuario, archivado.audiencia_id):
        raise ValidationError("Solo quien lo ve puede conservarlo.")
    if archivado.conservado_el is None:
        archivado.conservado_por = usuario
        archivado.conservado_el = timezone.now()
        archivado.save(update_fields=["conservado_por", "conservado_el"])


# «Dejar de conservar» (solo el superadmin): vuelve a contar el plazo, con un aviso nuevo antes de borrar.
def dejar_de_conservar(usuario, archivado):
    if not usuario.is_superuser:
        raise ValidationError("Solo el superadmin puede dejar de conservar algo.")
    archivado.conservado_por = None
    archivado.conservado_el = None
    archivado.avisado_el = None
    archivado.save(update_fields=["conservado_por", "conservado_el", "avisado_el"])


# «Borrar ya» (solo el superadmin, para liberar espacio): borra un elemento archivado sin esperar al
# plazo, también si está conservado. Queda en el registro de borrados como poda a mano.
def podar(usuario, archivado):
    if not usuario.is_superuser:
        raise ValidationError("Solo el superadmin puede borrar a mano.")
    _borrar([archivado], Borrado.A_MANO, quien=usuario)
