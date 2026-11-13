"""
Direcciones del módulo «lugares», que cuelgan de /lugares/ (ver config/urls.py).
"""

from django.urls import path

from . import views

app_name = "lugares"

urlpatterns = [
    # Mi lugar, mapa, lista y ficha de un lugar.
    path("", views.mi_lugar, name="mi_lugar"),
    path("mapa/", views.mapa, name="mapa"),
    path("lista/", views.lista, name="lista"),
    path("lugar/<int:pk>/", views.lugar, name="lugar"),
    # Gestión del superadmin: propuestas, lugar nuevo e importar.
    path("propuestas/", views.propuestas, name="propuestas"),
    path("nuevo/", views.nuevo, name="nuevo"),
    path("importar/", views.importar, name="importar"),
    # Configuración → Lugares.
    path("configuracion/", views.configuracion, name="configuracion"),
]
