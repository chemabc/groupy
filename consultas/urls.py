"""
Direcciones del módulo «consultas», que cuelgan de /consultas/ (ver config/urls.py).
"""

from django.urls import path

from . import views

app_name = "consultas"

urlpatterns = [
    # Lista y crear.
    path("", views.lista, name="lista"),
    path("nueva/", views.nueva, name="nueva"),
    # Ficha de una consulta: preparar las preguntas, votar y ver los resultados.
    path("<int:pk>/", views.consulta, name="consulta"),
]
