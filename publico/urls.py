"""
Direcciones del módulo «publico», en la raíz del sitio (ver config/urls.py):
- la portada sin sesión (/portada/ y /o/<organización>/);
- «🌐 Webs» y la gestión (/webs/…).
"""

from django.urls import path

from . import views

app_name = "publico"

urlpatterns = [
    # Portada pública (sin sesión): la de la plataforma y la de cada organización, con sus pestañas.
    path("portada/", views.portada, name="portada"),
    path("portada/<int:pk>/", views.portada, name="portada_pagina"),
    path("o/<int:organizacion>/", views.portada_de_organizacion, name="portada_de_organizacion"),
    path("o/<int:organizacion>/<int:pk>/", views.portada_de_organizacion, name="portada_de_organizacion_pagina"),
    # «🌐 Webs»: entrada, la web de un grupo o de una organización, cada página, novedades, buscar y jerarquía.
    path("webs/", views.webs, name="webs"),
    path("webs/grupo/<int:pk>/", views.grupo, name="grupo"),
    path("webs/organizacion/<int:pk>/", views.organizacion, name="organizacion"),
    path("webs/pagina/<int:pk>/", views.pagina, name="pagina"),
    path("webs/novedades/", views.novedades, name="novedades"),
    path("webs/buscar/", views.buscar, name="buscar"),
    path("webs/jerarquia/", views.jerarquia, name="jerarquia"),
    # Imágenes de las páginas (las de las páginas públicas se ven sin sesión).
    path("webs/imagen/<int:pk>/", views.imagen, name="imagen"),
    # Gestionar: las páginas, cada una (datos, publicar, imágenes), escribir y su vista previa, y relaciones.
    path("webs/gestionar/", views.paginas, name="paginas"),
    path("webs/gestionar/<int:pk>/", views.editar, name="editar"),
    path("webs/gestionar/<int:pk>/escribir/", views.escribir, name="escribir"),
    path("webs/gestionar/vista-previa/", views.vista_previa, name="vista_previa"),
    path("webs/relaciones/", views.relaciones, name="relaciones"),
]
