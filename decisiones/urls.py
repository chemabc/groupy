"""
Direcciones del módulo «decisiones», que cuelgan de /decisiones/ (ver config/urls.py).
"""

from django.urls import path

from . import views

app_name = "decisiones"

urlpatterns = [
    # Listas: las vigentes y todas (también las sustituidas).
    path("", views.lista, name="lista"),
    path("todas/", views.todas, name="todas"),
    # Ficha de una decisión (con «sustituida por…»).
    path("<int:pk>/", views.decision, name="decision"),
]
