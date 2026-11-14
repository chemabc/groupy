"""
Direcciones del módulo «proyectos», que cuelgan de /proyectos/ (ver config/urls.py).
"""

from django.urls import path

from . import views

app_name = "proyectos"

urlpatterns = [
    # Listas y crear.
    path("", views.proyectos, name="proyectos"),
    path("personales/", views.personales, name="personales"),
    path("nuevo/", views.nuevo, name="nuevo"),
    # Cada proyecto: ficha, editar y kanban (con las tareas de sus subproyectos).
    path("<int:pk>/", views.proyecto, name="proyecto"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/kanban/", views.kanban, name="kanban"),
    # Tareas: las mías (lista y kanban), crear, ficha y mover en el kanban.
    path("tareas/", views.tareas, name="tareas"),
    path("tareas/kanban/", views.tareas_kanban, name="tareas_kanban"),
    path("tareas/nueva/", views.nueva_tarea, name="nueva_tarea"),
    # Lista de personas (JSON) para elegir responsable y colaboradoras de una tarea.
    path("tareas/personas/", views.personas_para_tarea, name="personas_para_tarea"),
    path("tareas/<int:pk>/", views.tarea, name="tarea"),
    # Cambia un solo dato de una tarea desde su ficha, sobre lo ya escrito (lo pide htmx).
    path("tareas/<int:pk>/campo/", views.tarea_campo, name="tarea_campo"),
    path("tareas/mover/", views.mover_tarea, name="mover_tarea"),
]
