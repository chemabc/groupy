"""
Operaciones del módulo «proyectos»: crear proyectos y subproyectos (a cualquier profundidad), quién los
ve y quién los gestiona, el árbol de cada proyecto, los cometidos (coordinación, documentación,
comunicación), las tareas (crear, cambiar, moverlas en el kanban, borrar, y las dependencias entre ellas,
que las bloquean y desbloquean solas) y los recursos (con su petición de talentos). Las pantallas
(proyectos/views.py) y el calendario (proyectos/calendario.py) llaman a estas funciones.
"""

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from audiencias.models import Audiencia
from audiencias.selector import audiencia_de
from audiencias.servicios import anadir_personas, crear_privada, filtrar_visibles, puede_ver
from eventos_sw.servicios import emitir
from permisos.models import Cometido
from permisos.servicios import asignar_cometido, exigir, puede, quitar_cometido

from talentos.models import Talento
from talentos.servicios import obtener_o_crear, pedir

from .models import Proyecto, Recurso, Tarea

# Tipo de ancla de los proyectos (para los cometidos, las invitaciones, las salidas…).
ANCLA = "proyectos.proyecto"
# Cometido que da la gestión de un proyecto (y de sus subproyectos).
COORDINACION = "proyectos.coordinacion"


# ── Ver ──────────────────────────────────────────────────────────────────────────────────────────────


# Consulta de los proyectos que ve una persona: los de sus audiencias y los que ha creado (los
# personales solo los ve quien los crea). Sin ejecutar.
def visibles(usuario):
    de_su_audiencia = filtrar_visibles(Proyecto.objects.all(), usuario)
    return Proyecto.objects.filter(Q(pk__in=de_su_audiencia.values("pk")) | Q(creador=usuario))


# Dice si una persona ve un proyecto.
def ve(usuario, proyecto):
    return proyecto.creador_id == usuario.pk or puede_ver(usuario, proyecto.audiencia_id)


# Consulta de las tareas que ve una persona: las de los proyectos que ve, las sueltas y personales de sus
# audiencias, y aquellas de las que es responsable, colaboradora o creadora. Sin ejecutar.
def tareas_visibles(usuario):
    sueltas = filtrar_visibles(Tarea.objects.filter(proyecto__isnull=True, audiencia__isnull=False), usuario)
    suyas = Tarea.objects.filter(Q(responsable=usuario) | Q(colaboradores=usuario) | Q(creador=usuario))
    return Tarea.objects.filter(
        Q(proyecto__in=visibles(usuario).values("pk")) | Q(pk__in=sueltas.values("pk")) | Q(pk__in=suyas.values("pk"))
    )


# ── El árbol de un proyecto ──────────────────────────────────────────────────────────────────────────


@dataclass
class Rama:
    """Un proyecto dentro de un árbol, con su nivel (0 el principal) para sangrarlo al pintarlo."""

    proyecto: Proyecto
    nivel: int


# Ordena una lista de proyectos como árbol: cada uno seguido de sus subproyectos (por título), con su
# nivel. Los que tienen el padre fuera de la lista (porque no se ve) salen como principales.
#   - proyectos: lista de proyectos (sin consultas: se usan padre_id y raiz_id).
def en_arbol(proyectos):
    ids = {proyecto.pk for proyecto in proyectos}
    hijos = {}
    for proyecto in sorted(proyectos, key=lambda p: (p.titulo.lower(), p.pk)):
        padre = proyecto.padre_id if proyecto.padre_id in ids else None
        hijos.setdefault(padre, []).append(proyecto)
    resultado = []

    # Añade un proyecto y, debajo, sus subproyectos, un nivel más adentro.
    def anadir(proyecto, nivel):
        resultado.append(Rama(proyecto, nivel))
        for hijo in hijos.get(proyecto.pk, []):
            anadir(hijo, nivel + 1)

    for principal in hijos.get(None, []):
        anadir(principal, 0)
    return resultado


# Todo el árbol de un proyecto (desde su raíz), como diccionario {id: proyecto}. Una consulta.
def arbol_entero(proyecto):
    return {p.pk: p for p in Proyecto.objects.filter(raiz_id=proyecto.raiz_id).select_related("tipologia", "grupo__organizacion")}


# Los antecesores de un proyecto, del principal al padre (lista de proyectos), con el árbol ya cargado.
def antecesores(proyecto, arbol):
    cadena, actual = [], arbol.get(proyecto.padre_id)
    while actual is not None:
        cadena.append(actual)
        actual = arbol.get(actual.padre_id)
    return list(reversed(cadena))


# Ids de un proyecto y de todos sus subproyectos (a cualquier profundidad), con el árbol ya cargado.
def subarbol(proyecto, arbol):
    ids, pendientes = set(), [proyecto.pk]
    while pendientes:
        actual = pendientes.pop()
        ids.add(actual)
        pendientes += [p.pk for p in arbol.values() if p.padre_id == actual]
    return ids


# ── Gestionar ────────────────────────────────────────────────────────────────────────────────────────


# Dice si una persona gestiona un proyecto (cambiarlo, crear subproyectos, dar cometidos, borrarlo): quien
# lo creó o lo coordina, o creó o coordina uno de sus antecesores; la administración del grupo (con
# «grupos.editar_grupo»); o el superadmin. Un proyecto personal, solo quien lo creó.
#   - arbol: el árbol ya cargado (arbol_entero), para no volver a pedirlo.
def puede_gestionar(usuario, proyecto, arbol=None):
    if proyecto.personal:
        return proyecto.creador_id == usuario.pk
    if usuario.is_superuser or proyecto.creador_id == usuario.pk:
        return True
    if puede(usuario, "grupos.editar_grupo", grupo=proyecto.grupo_id):
        return True
    arbol = arbol if arbol is not None else arbol_entero(proyecto)
    linea = [proyecto] + antecesores(proyecto, arbol)
    if any(p.creador_id == usuario.pk for p in linea):
        return True
    return Cometido.objects.filter(usuario=usuario, codigo=COORDINACION, ancla_tipo=ANCLA, ancla_id__in=[p.pk for p in linea]).exists()


# Audiencia de algo personal (solo una persona; ni el superadmin lo ve).
def _personal(usuario):
    return crear_privada([usuario], personal=True)


# Crea un proyecto (o un subproyecto, con «padre»). Un subproyecto es del mismo grupo que su padre y, si
# el padre es personal, también personal; hace falta gestionar el padre. Un proyecto de grupo necesita
# «proyectos.crear» en el grupo. Devuelve el proyecto.
#   - usuario: quien lo crea.
#   - tipologia: su tipo.
#   - datos: titulo, objetivo_general, objetivos_especificos, alcance, riesgos, inicio, limite.
#   - grupo: el grupo que lo coordina (sin padre y no personal).
#   - visibilidad: la clave del selector («privado», «grupo:0»…). Se ignora en lo personal.
#   - padre: el proyecto padre, si es un subproyecto.
#   - personal: si es «privado e individual».
#   - campos: los de su tipología (en JSON).
@transaction.atomic
def crear_proyecto(usuario, tipologia, datos, grupo=None, visibilidad="privado", padre=None, personal=False, campos=None):
    if padre is not None:
        if not puede_gestionar(usuario, padre):
            raise ValidationError("Solo quien gestiona el proyecto puede crearle subproyectos.")
        grupo, personal = padre.grupo, padre.personal
    if personal:
        grupo, visibilidad, audiencia = None, "privado", _personal(usuario)
    else:
        if grupo is None:
            raise ValidationError("Elige el grupo que lo coordina.")
        exigir(usuario, "proyectos.crear", grupo=grupo)
        audiencia = audiencia_de(visibilidad, grupo, personas=[usuario])
    proyecto = Proyecto(
        tipologia=tipologia, grupo=grupo, creador=usuario, personal=personal, padre=padre, audiencia=audiencia,
        visibilidad=visibilidad, campos=campos or {}, **datos,
    )
    proyecto.full_clean(exclude=["raiz"])
    proyecto.save()
    proyecto.raiz_id = padre.raiz_id if padre is not None else proyecto.pk
    proyecto.save(update_fields=["raiz"])
    return proyecto


# Cambia los datos de un proyecto (y, si se pasa, quién lo ve). Devuelve el proyecto.
@transaction.atomic
def editar_proyecto(usuario, proyecto, datos, visibilidad=None, campos=None):
    if not puede_gestionar(usuario, proyecto):
        raise ValidationError("Solo quien gestiona el proyecto puede cambiarlo.")
    for campo, valor in datos.items():
        setattr(proyecto, campo, valor)
    if campos is not None:
        proyecto.campos = campos
    if visibilidad and visibilidad != proyecto.visibilidad and not proyecto.personal:
        proyecto.audiencia = audiencia_de(visibilidad, proyecto.grupo, personas=[proyecto.creador] if proyecto.creador else [])
        proyecto.visibilidad = visibilidad
    proyecto.full_clean()
    proyecto.save()
    return proyecto


# Borra un proyecto con sus subproyectos y sus tareas.
@transaction.atomic
def borrar_proyecto(usuario, proyecto):
    if not puede_gestionar(usuario, proyecto):
        raise ValidationError("Solo quien gestiona el proyecto puede borrarlo.")
    proyecto.delete()


# ── Cometidos ────────────────────────────────────────────────────────────────────────────────────────


# Cometidos de un proyecto (lista de Cometido con su usuario). Una consulta.
def cometidos(proyecto):
    return list(Cometido.objects.filter(ancla_tipo=ANCLA, ancla_id=proyecto.pk).select_related("usuario").order_by("codigo", "usuario__alias"))


# Da un cometido del proyecto a una persona. La coordinación (que da la gestión) solo la da quien gestiona
# el proyecto; documentación y comunicación, también cada cual a sí misma si ve el proyecto. Si el
# proyecto es privado, la persona pasa a verlo.
#   - quien: quien lo hace.
#   - persona: a quién.
#   - codigo: el código del cometido.
@transaction.atomic
def apuntar(quien, proyecto, persona, codigo):
    if proyecto.personal:
        raise ValidationError("Un proyecto personal no tiene cometidos.")
    gestiona = puede_gestionar(quien, proyecto)
    if not gestiona and (quien.pk != persona.pk or codigo == COORDINACION or not ve(quien, proyecto)):
        raise ValidationError("Solo quien gestiona el proyecto puede dar la coordinación o apuntar a otras personas.")
    if Cometido.objects.filter(usuario=persona, codigo=codigo, ancla_tipo=ANCLA, ancla_id=proyecto.pk).exists():
        return
    asignar_cometido(persona, codigo, ANCLA, proyecto.pk, grupo=proyecto.grupo)
    if proyecto.audiencia.tipo == Audiencia.PRIVADA:
        anadir_personas(proyecto.audiencia, [persona])


# Quita un cometido (cada cual el suyo, o quien gestiona el proyecto el de otra persona).
@transaction.atomic
def desapuntar(quien, proyecto, persona, codigo):
    if quien.pk != persona.pk and not puede_gestionar(quien, proyecto):
        raise ValidationError("Solo quien gestiona el proyecto puede quitar a otras personas.")
    quitar_cometido(persona, codigo, ANCLA, proyecto.pk)


# ── Tareas ───────────────────────────────────────────────────────────────────────────────────────────


# Comprueba que las personas de una tarea de un proyecto lo ven; si el proyecto es privado (no
# personal), las añade a quienes lo ven.
def _que_vean(proyecto, personas):
    if proyecto.audiencia.tipo == Audiencia.PRIVADA and not proyecto.audiencia.personal:
        anadir_personas(proyecto.audiencia, personas)
        return
    for persona in personas:
        if not ve(persona, proyecto):
            raise ValidationError(f"{persona} no ve el proyecto: no puede encargarse de la tarea.")


# Crea una tarea en un proyecto, suelta en un grupo o personal. Avisa a la persona responsable si no es
# quien la crea. Devuelve la tarea.
#   - usuario: quien la crea. En un proyecto: quien lo ve y puede crear en su grupo (o lo gestiona). Suelta:
#     con «proyectos.crear» en el grupo. Personal: cualquiera (y la responsable es ella misma).
#   - datos: titulo, descripcion, limite, responsable.
#   - colaboradores: lista de personas.
#   - proyecto, grupo, personal: dónde está (uno de los tres).
#   - visibilidad: la de una tarea suelta.
@transaction.atomic
def crear_tarea(usuario, datos, colaboradores=(), proyecto=None, grupo=None, personal=False, visibilidad="grupo:0", espera_a=()):
    datos = dict(datos)
    audiencia = None
    if proyecto is not None:
        if not ve(usuario, proyecto):
            raise ValidationError("No ves ese proyecto.")
        if proyecto.personal:
            if proyecto.creador_id != usuario.pk:
                raise ValidationError("Es un proyecto personal.")
            datos["responsable"], colaboradores = usuario, ()
        elif not (puede_gestionar(usuario, proyecto) or puede(usuario, "proyectos.crear", grupo=proyecto.grupo_id)):
            raise ValidationError("Para crear tareas en este proyecto tienes que estar en su grupo.")
        else:
            _que_vean(proyecto, [datos["responsable"], *colaboradores])
        grupo, personal, visibilidad = proyecto.grupo, proyecto.personal, proyecto.visibilidad
    elif personal:
        datos["responsable"], colaboradores, grupo, visibilidad = usuario, (), None, "privado"
        audiencia = _personal(usuario)
    else:
        if grupo is None:
            raise ValidationError("Elige el grupo de la tarea.")
        exigir(usuario, "proyectos.crear", grupo=grupo)
        audiencia = audiencia_de(visibilidad, grupo, personas=[usuario, datos["responsable"], *colaboradores])
    tarea = Tarea(proyecto=proyecto, grupo=grupo, personal=personal, creador=usuario, audiencia=audiencia, visibilidad=visibilidad, **datos)
    tarea.orden = Tarea.objects.filter(proyecto=proyecto, estado=tarea.estado).count()
    tarea.full_clean()
    tarea.save()
    tarea.colaboradores.set(colaboradores)
    if espera_a:
        _poner_dependencias(tarea, espera_a)
    if tarea.responsable_id != usuario.pk:
        emitir("proyectos.tarea_asignada", tarea_id=tarea.pk)
    return tarea


# Dice si una persona puede cambiar una tarea: su responsable, quien colabora, quien la creó, quien
# gestiona su proyecto o la administración del grupo (y el superadmin, si no es personal).
def puede_cambiar(usuario, tarea, colaboradores=None):
    if tarea.personal:
        return tarea.creador_id == usuario.pk
    if usuario.pk in (tarea.responsable_id, tarea.creador_id) or usuario.is_superuser:
        return True
    ids = colaboradores if colaboradores is not None else set(tarea.colaboradores.values_list("pk", flat=True))
    if usuario.pk in ids:
        return True
    if tarea.proyecto_id:
        return puede_gestionar(usuario, tarea.proyecto)
    return puede(usuario, "grupos.editar_grupo", grupo=tarea.grupo_id)


# Cambia los datos de una tarea. Si cambia la responsable, se le avisa. Devuelve la tarea.
#   - colaboradores: la lista nueva, o None para no tocarla.
#   - espera_a: las tareas a las que espera (lista nueva), o None para no tocarlas.
@transaction.atomic
def editar_tarea(usuario, tarea, datos, colaboradores=None, espera_a=None):
    if not puede_cambiar(usuario, tarea):
        raise ValidationError("Solo quien se encarga de la tarea, quien colabora o quien gestiona el proyecto pueden cambiarla.")
    responsable_antes, estado_antes = tarea.responsable_id, tarea.estado
    if espera_a is not None:
        _poner_dependencias(tarea, espera_a, al_dia=False)
    if datos.get("estado", estado_antes) != estado_antes:
        _comprobar_que_no_espera(tarea)
    if tarea.personal:
        datos = {campo: valor for campo, valor in datos.items() if campo != "responsable"}
        colaboradores = None
    for campo, valor in datos.items():
        setattr(tarea, campo, valor)
    if tarea.proyecto_id and not tarea.personal:
        _que_vean(tarea.proyecto, [tarea.responsable, *(colaboradores or ())])
    if tarea.estado != estado_antes:
        tarea.bloqueo_automatico = False
    tarea.full_clean()
    tarea.save()
    if colaboradores is not None:
        tarea.colaboradores.set(colaboradores)
    poner_al_dia([tarea])
    if tarea.estado != estado_antes:
        poner_al_dia(list(tarea.desbloquea.all()))
    if tarea.responsable_id != responsable_antes and tarea.responsable_id != usuario.pk:
        emitir("proyectos.tarea_asignada", tarea_id=tarea.pk)
    return tarea


# Mueve una tarea en el kanban: la pasa a otra columna (estado) y guarda el orden de esa columna.
#   - estado: la columna de destino.
#   - orden: ids de las tareas de esa columna, de arriba abajo, tal como han quedado (se ignoran las que
#     no estén en esa columna).
# Devuelve cuántas tareas más han cambiado de columna solas (las que esperaban a esta).
@transaction.atomic
def mover_tarea(usuario, tarea, estado, orden=()):
    if estado not in dict(Tarea.ESTADOS):
        raise ValidationError("Columna desconocida.")
    if not puede_cambiar(usuario, tarea):
        raise ValidationError("No puedes mover esta tarea.")
    cambia = estado != tarea.estado
    if cambia:
        _comprobar_que_no_espera(tarea)
        tarea.bloqueo_automatico = False
    tarea.estado = estado
    tarea.save(update_fields=["estado", "bloqueo_automatico", "actualizada"])
    columna = {t.pk: t for t in Tarea.objects.filter(pk__in=list(orden), estado=estado)}
    cambiadas = []
    for posicion, pk in enumerate(orden):
        if pk in columna and columna[pk].orden != posicion:
            columna[pk].orden = posicion
            cambiadas.append(columna[pk])
    Tarea.objects.bulk_update(cambiadas, ["orden"])
    return len(poner_al_dia(list(tarea.desbloquea.all()))) if cambia else 0


# Borra una tarea. Las que la esperaban se ponen al día (quizá ya no esperan a nada).
@transaction.atomic
def borrar_tarea(usuario, tarea):
    if not puede_cambiar(usuario, tarea):
        raise ValidationError("No puedes borrar esta tarea.")
    esperaban = list(tarea.desbloquea.all())
    tarea.delete()
    poner_al_dia(esperaban)


# ── Dependencias ─────────────────────────────────────────────────────────────────────────────────────


# Las tareas a las que espera una tarea y aún no están hechas. Una consulta.
def pendientes_de(tarea):
    return list(tarea.espera_a.exclude(estado=Tarea.HECHA).order_by("titulo"))


# No deja sacar de «Bloqueada» (ni empezar ni terminar) una tarea que espera a otras sin hacer.
def _comprobar_que_no_espera(tarea):
    pendientes = pendientes_de(tarea)
    if pendientes:
        nombres = ", ".join(f"«{otra.titulo}»" for otra in pendientes)
        raise ValidationError(f"«{tarea.titulo}» espera a {nombres}: hasta que estén hechas, sigue bloqueada.")


# Cambia las tareas a las que espera una tarea y la pone al día (la bloquea si alguna no está hecha).
# Solo puede esperar a tareas de su mismo árbol de proyectos, y sin formar un círculo (A espera a B y B
# a A).
#   - espera_a: lista de tareas.
#   - al_dia: si se pone al día ya (False si quien llama lo hace después de guardar la tarea).
def _poner_dependencias(tarea, espera_a, al_dia=True):
    espera_a = list(espera_a)
    if espera_a and not tarea.proyecto_id:
        raise ValidationError("Solo las tareas de un proyecto pueden esperar a otras.")
    raiz = tarea.proyecto.raiz_id if tarea.proyecto_id else None
    for otra in espera_a:
        if otra.pk == tarea.pk:
            raise ValidationError("Una tarea no puede esperarse a sí misma.")
        if otra.proyecto_id is None or otra.proyecto.raiz_id != raiz:
            raise ValidationError(f"«{otra.titulo}» no es de este proyecto ni de sus subproyectos.")
    if _hace_circulo(tarea, espera_a, raiz):
        raise ValidationError("Así se formaría un círculo: alguna de esas tareas ya espera (directa o indirectamente) a esta.")
    tarea.espera_a.set(espera_a)
    if al_dia:
        poner_al_dia([tarea])


# Dice si hacer que una tarea espere a otras formaría un círculo: si desde alguna de ellas, siguiendo a
# qué espera cada una, se llega a la tarea. Una consulta (todas las esperas del árbol).
def _hace_circulo(tarea, espera_a, raiz):
    if not espera_a:
        return False
    enlaces = Tarea.espera_a.through.objects.filter(from_tarea__proyecto__raiz_id=raiz).values_list("from_tarea_id", "to_tarea_id")
    siguientes = {}
    for desde, hasta in enlaces:
        siguientes.setdefault(desde, set()).add(hasta)
    por_mirar, vistas = [otra.pk for otra in espera_a], set()
    while por_mirar:
        actual = por_mirar.pop()
        if actual == tarea.pk:
            return True
        if actual not in vistas:
            vistas.add(actual)
            por_mirar.extend(siguientes.get(actual, ()))
    return False


# Pone al día unas tareas según a qué esperan: si alguna de sus esperas no está hecha, pasa a
# «Bloqueada» (marcada como bloqueo automático); si ya están todas hechas y la bloqueó la aplicación,
# vuelve a «Pendiente» y se avisa a su responsable. Las hechas no se tocan. Devuelve las que cambian.
#   - tareas: lista de tareas.
def poner_al_dia(tareas):
    cambiadas = []
    for tarea in tareas:
        if tarea.estado == Tarea.HECHA:
            continue
        espera = tarea.espera_a.exclude(estado=Tarea.HECHA).exists()
        if espera and tarea.estado != Tarea.BLOQUEADA:
            tarea.estado, tarea.bloqueo_automatico = Tarea.BLOQUEADA, True
        elif not espera and tarea.estado == Tarea.BLOQUEADA and tarea.bloqueo_automatico:
            tarea.estado, tarea.bloqueo_automatico = Tarea.PENDIENTE, False
            emitir("proyectos.tarea_desbloqueada", tarea_id=tarea.pk)
        else:
            continue
        tarea.save(update_fields=["estado", "bloqueo_automatico", "actualizada"])
        cambiadas.append(tarea)
    return cambiadas


# ── Recursos ─────────────────────────────────────────────────────────────────────────────────────────


# Apunta un recurso que le hace falta a un proyecto. Solo quien lo gestiona. Devuelve el recurso.
#   - datos: nombre, cantidad y origen.
def anadir_recurso(usuario, proyecto, datos):
    if not puede_gestionar(usuario, proyecto):
        raise ValidationError("Solo quien gestiona el proyecto puede apuntar recursos.")
    recurso = Recurso(proyecto=proyecto, **datos)
    recurso.full_clean()
    recurso.save()
    return recurso


# Marca un recurso como conseguido, o lo vuelve a poner como pendiente.
def marcar_recurso(usuario, recurso, conseguido):
    if not puede_gestionar(usuario, recurso.proyecto):
        raise ValidationError("Solo quien gestiona el proyecto puede cambiar sus recursos.")
    recurso.conseguido = conseguido
    recurso.save(update_fields=["conseguido"])


# Borra un recurso (la petición de talentos, si la hay, sigue).
def borrar_recurso(usuario, recurso):
    if not puede_gestionar(usuario, recurso.proyecto):
        raise ValidationError("Solo quien gestiona el proyecto puede borrar sus recursos.")
    recurso.delete()


# Dice si una persona puede pedir los recursos de un proyecto con una petición de talentos: lo gestiona,
# es de un grupo (no personal) y puede pedir talentos a ese grupo («talentos.pedir»).
def puede_pedir_recursos(usuario, proyecto, gestiona=None):
    gestiona = puede_gestionar(usuario, proyecto) if gestiona is None else gestiona
    return gestiona and not proyecto.personal and proyecto.grupo_id is not None and puede(usuario, "talentos.pedir", grupo=proyecto.grupo_id)


# Pide un recurso al grupo del proyecto con una petición de talentos (el recurso entra en el catálogo
# como «recurso» si no estaba). Llega a quienes lo comparten con el grupo. Devuelve la petición.
def pedir_recurso(usuario, recurso):
    proyecto = recurso.proyecto
    if not puede_pedir_recursos(usuario, proyecto):
        raise ValidationError("Para pedirlo hay que gestionar el proyecto y poder pedir talentos a su grupo.")
    if recurso.peticion_id:
        raise ValidationError("Este recurso ya se ha pedido.")
    cantidad = int(recurso.cantidad) if recurso.cantidad.strip().isdigit() else 1
    descripcion = f"Para el proyecto «{proyecto.titulo}»." + (f" De dónde sale: {recurso.origen}." if recurso.origen else "")
    peticion = pedir(
        usuario, proyecto.grupo, f"{proyecto.titulo}: {recurso.nombre}"[:120], descripcion,
        [(obtener_o_crear(recurso.nombre, Talento.RECURSO, usuario), max(1, min(cantidad, 999)))],
        ancla_tipo=ANCLA, ancla_id=proyecto.pk,
    )
    recurso.peticion = peticion
    recurso.save(update_fields=["peticion"])
    return peticion
