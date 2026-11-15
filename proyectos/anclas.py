"""
Lo que «proyectos» dice en su contrato sobre sus anclas (ver Ancla en base/contrato.py): de qué grupo es y
quién ve lo que cuelga de una tarea, y qué tareas hay «dentro» de un proyecto (para que su ficha enseñe
también los documentos de sus tareas). Lo usan otros módulos a través del registro, sin importar este.
"""

from .models import Tarea


# El grupo y quién ve lo que cuelga de una tarea: los de su proyecto si está en uno; los suyos si es
# suelta; None si es personal (de una tarea personal no se cuelga nada) o ya no existe. Una consulta.
#   - tarea_id: el número de la tarea.
def contexto_de_tarea(tarea_id):
    tarea = Tarea.objects.select_related("proyecto__grupo", "proyecto__audiencia", "grupo", "audiencia").filter(pk=tarea_id).first()
    if tarea is None or tarea.personal:
        return None
    if tarea.proyecto_id:
        return tarea.proyecto.grupo, tarea.proyecto.audiencia
    if tarea.grupo_id and tarea.audiencia_id:
        return tarea.grupo, tarea.audiencia
    return None


# Las tareas de un proyecto, como anclas «de dentro»: lista de («proyectos.tarea», número, título). Una
# consulta.
#   - proyecto_id: el número del proyecto.
def tareas_del_proyecto(proyecto_id):
    return [("proyectos.tarea", pk, titulo) for pk, titulo in Tarea.objects.filter(proyecto_id=proyecto_id).values_list("pk", "titulo")]
