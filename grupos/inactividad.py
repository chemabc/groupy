"""
Inactividad: cuándo una persona sale marcada «sin actividad» en la lista de miembros de la administración.

- El día en que cada persona usa la plataforma lo apunta usuarios/middleware.py (ApuntarActividad), una vez
  al día, solo el día. Nadie lo ve: aquí solo se compara con un plazo.
- El plazo va en cascada (LimiteDeInactividad): el superadmin pone el de partida y el mínimo para toda la
  plataforma (de partida, 30 días los dos); el admin de cada organización y el de cada grupo solo pueden
  bajarlo, nunca por debajo del mínimo. En cada grupo vale el más corto de su organización, de él y de los
  grupos que lo contienen.
"""

from django.utils import timezone

from .models import Contencion, Grupo, LimiteDeInactividad

# Días de partida y mínimo si el superadmin no ha puesto nada (un mes).
DIAS_POR_DEFECTO = 30
MINIMO_POR_DEFECTO = 30


# La fila de la plataforma, o None si el superadmin aún no ha puesto nada. Una consulta.
def de_la_plataforma():
    return LimiteDeInactividad.objects.filter(organizacion__isnull=True, grupo__isnull=True).first()


# Días de partida y mínimo de la plataforma: (dias, minimo).
#   - fila: la de la plataforma (o None).
def de_partida(fila):
    if fila is None:
        return DIAS_POR_DEFECTO, MINIMO_POR_DEFECTO
    return fila.dias, fila.minimo or 0


# Los días que valen en cada uno de unos grupos: {id del grupo: días}. Junta la plataforma, sus
# organizaciones, ellos mismos y los grupos que los contienen, y toma el más corto (nunca por debajo del
# mínimo). Dos consultas, sean cuantos sean los grupos.
#   - grupos: lista de Grupo (con organizacion_id).
def dias_por_grupo(grupos):
    if not grupos:
        return {}
    ids = [grupo.pk for grupo in grupos]
    encima = {}
    for descendiente, antecesor in Contencion.objects.filter(descendiente_id__in=ids).values_list("descendiente_id", "antecesor_id"):
        encima.setdefault(descendiente, set()).add(antecesor)
    todos_los_de_encima = set().union(*encima.values()) if encima else set()
    filas = list(
        LimiteDeInactividad.objects.filter(organizacion__isnull=True, grupo__isnull=True)
        | LimiteDeInactividad.objects.filter(organizacion_id__in={grupo.organizacion_id for grupo in grupos})
        | LimiteDeInactividad.objects.filter(grupo_id__in=todos_los_de_encima | set(ids))
    )
    plataforma = next((fila for fila in filas if not fila.organizacion_id and not fila.grupo_id), None)
    dias, minimo = de_partida(plataforma)
    por_organizacion = {fila.organizacion_id: fila.dias for fila in filas if fila.organizacion_id}
    por_grupo = {fila.grupo_id: fila.dias for fila in filas if fila.grupo_id}
    resultado = {}
    for grupo in grupos:
        candidatos = [dias, por_organizacion.get(grupo.organizacion_id, dias)]
        candidatos += [por_grupo[otro] for otro in encima.get(grupo.pk, {grupo.pk}) | {grupo.pk} if otro in por_grupo]
        resultado[grupo.pk] = max(min(candidatos), minimo)
    return resultado


# Dice si una persona lleva más de «dias» sin actividad. Quien nunca ha entrado cuenta desde que se
# activó su cuenta.
#   - usuario: la persona (con ultima_actividad y activado_el).
#   - dias: el plazo que vale.
def sin_actividad(usuario, dias):
    desde = usuario.ultima_actividad or usuario.activado_el
    return desde is not None and (timezone.localdate() - desde).days > dias


# La fila de un nivel para cambiarla: la que hay o una nueva sin guardar.
def fila_de(organizacion_id=None, grupo_id=None):
    filtro = {"organizacion_id": organizacion_id, "grupo_id": grupo_id}
    return LimiteDeInactividad.objects.filter(**filtro).first() or LimiteDeInactividad(**filtro)


# Lista de (id, «ORG › camino») de los grupos dados (None: todos), para los desplegables. Una consulta.
def caminos(ids):
    consulta = Grupo.objects.en_orden_de_arbol().select_related("organizacion")
    if ids is not None:
        consulta = consulta.filter(pk__in=ids)
    return [(grupo.pk, f"{grupo.organizacion.nombre} › {grupo.camino}") for grupo in consulta]
