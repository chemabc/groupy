"""
Direcciones del módulo «usuarios», que cuelgan de /cuenta/ (ver config/urls.py).
"""

from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [
    # Pantalla de entrada (alias y contraseña).
    path("entrar/", views.Entrar.as_view(), name="entrar"),
    # Cierra la sesión. Solo acepta POST (el botón «Salir» de la cabecera) y vuelve a la entrada.
    path("salir/", LogoutView.as_view(), name="salir"),
    # Mi cuenta → Preferencias.
    path("preferencias/", views.preferencias, name="preferencias"),
    # Guarda una preferencia (la llama interfaz.js).
    path("preferencias/guardar/", views.guardar_preferencia, name="guardar_preferencia"),
    # Mi cuenta → Contraseña.
    path("contrasena/", views.contrasena, name="contrasena"),
]
