"""
Direcciones del módulo «grupos», que cuelgan de /organizaciones/ (ver config/urls.py).
"""

from django.urls import path

from . import editor, miembros, views

app_name = "grupos"

urlpatterns = [
    # Subsecciones del menú: mis grupos (árboles y grafo), árbol, relaciones e invitaciones.
    path("", views.mis_grupos, name="mis_grupos"),
    # «Administrar → Miembros» (grupos/miembros.py) y los ajustes de inactividad.
    path("miembros/", miembros.miembros, name="miembros"),
    path("inactividad/", views.inactividad, name="inactividad"),
    # Personas con las que compartir algo de la biblioteca del editor (grupos/editor.py).
    path("personas-para-el-editor/", editor.personas_para_editor, name="personas_para_editor"),
    path("grafo/", views.grafo, name="grafo"),
    path("arbol/", views.arbol, name="arbol"),
    path("relaciones/", views.relaciones, name="relaciones"),
    path("invitaciones/", views.invitaciones, name="invitaciones"),
    # Fichas de un grupo y de una organización.
    path("grupo/<int:pk>/", views.grupo, name="grupo"),
    path("organizacion/<int:pk>/", views.organizacion, name="organizacion"),
    # Las organizaciones que administra quien mira («Administrar → Mi organización → Datos»).
    path("mis-organizaciones/", views.mis_organizaciones, name="mis_organizaciones"),
]
