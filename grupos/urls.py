"""
Direcciones del módulo «grupos», que cuelgan de /organizaciones/ (ver config/urls.py).
"""

from django.urls import path

from . import views

app_name = "grupos"

urlpatterns = [
    # Subsecciones del menú: mis grupos, árbol, relaciones e invitaciones.
    path("", views.mis_grupos, name="mis_grupos"),
    path("arbol/", views.arbol, name="arbol"),
    path("relaciones/", views.relaciones, name="relaciones"),
    path("invitaciones/", views.invitaciones, name="invitaciones"),
    # Fichas de un grupo y de una organización.
    path("grupo/<int:pk>/", views.grupo, name="grupo"),
    path("organizacion/<int:pk>/", views.organizacion, name="organizacion"),
    # Las organizaciones que administra quien mira («Administrar → Mi organización → Datos»).
    path("mis-organizaciones/", views.mis_organizaciones, name="mis_organizaciones"),
]
