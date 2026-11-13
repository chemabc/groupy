"""
Direcciones del módulo «talentos», que cuelgan de /talentos/ (ver config/urls.py).
"""

from django.urls import path

from . import views

app_name = "talentos"

urlpatterns = [
    # Mis talentos, peticiones (lista, nueva y cada una), recuentos de mis grupos y catálogo.
    path("", views.mis_talentos, name="mis_talentos"),
    path("peticiones/", views.peticiones, name="peticiones"),
    path("peticiones/nueva/", views.nueva_peticion, name="nueva_peticion"),
    path("peticiones/<int:pk>/", views.peticion, name="peticion"),
    path("grupos/", views.del_grupo, name="del_grupo"),
    path("catalogo/", views.catalogo, name="catalogo"),
]
