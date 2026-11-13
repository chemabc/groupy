"""
Direcciones del módulo «administracion», que cuelgan de /usuarios/ (ver config/urls.py).
"""

from django.urls import path

from . import views

app_name = "administracion"

urlpatterns = [
    # Bóveda: lista y alta de personas, ficha de cada una y dominios permitidos.
    path("boveda/personas/", views.personas, name="personas"),
    path("boveda/personas/<uuid:pk>/", views.persona, name="persona"),
    path("boveda/dominios/", views.dominios, name="dominios"),
    # Alias: lista y ficha.
    path("alias/", views.alias, name="alias"),
    path("alias/<int:pk>/", views.alias_ficha, name="alias_ficha"),
]
