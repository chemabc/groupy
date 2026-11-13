"""
Lo que el módulo «limpieza» necesita de «proyectos» (ver proyectos/apps.py, apartado «limpiables»): qué
proyectos y tareas están terminados desde antes de un momento. Lo que va dentro de un proyecto (sus
subproyectos y sus tareas) no se archiva por separado: sigue al proyecto principal.
"""

from .models import Proyecto, Tarea


# Proyectos principales (sin padre), finalizados antes de «antes» y sin archivar. Al archivarlos, salen
# de las listas con todo su árbol; al borrarlos, se borran con sus subproyectos y sus tareas.
def proyectos(antes):
    return Proyecto.objects.filter(padre__isnull=True, estado=Proyecto.FINALIZADO, terminado__lt=antes, archivado__isnull=True)


# Tareas sueltas de un grupo y personales, hechas antes de «antes» y sin archivar.
def tareas(antes):
    return Tarea.objects.filter(proyecto__isnull=True, estado=Tarea.HECHA, terminado__lt=antes, archivado__isnull=True)
