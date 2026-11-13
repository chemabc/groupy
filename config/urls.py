"""
Lista de direcciones web de la aplicación y qué módulo responde a cada una.

Cada módulo tiene su propio urls.py y aquí solo se incluye. Se irán añadiendo fase a fase (ver
docs/diseno.md, apartado 19).
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Panel de Django: solo trastienda técnica de emergencia para el superadmin (ver diseno.md, apartado 4).
    path("trastienda/", admin.site.urls),
    # Módulo «usuarios»: entrar, salir y «Mi cuenta».
    path("cuenta/", include("usuarios.urls")),
    # Módulo «grupos»: Organizaciones y grupos (mis grupos, árbol, fichas, relaciones e invitaciones).
    path("organizaciones/", include("grupos.urls")),
    # Módulo «eventos»: listas, convocar, ficha, editar y cartel.
    path("eventos/", include("eventos.urls")),
    # Módulo «proyectos»: proyectos, subproyectos y tareas.
    path("proyectos/", include("proyectos.urls")),
    # Módulo «calendario»: el calendario común, recordatorios y suscripción .ics.
    path("calendario/", include("calendario.urls")),
    # Módulo «limpieza»: el archivo, el registro de borrados y los plazos.
    path("limpieza/", include("limpieza.urls")),
    # Módulo «lugares»: mi lugar, mapa, lista, propuestas e importación.
    path("lugares/", include("lugares.urls")),
    # Módulo «talentos»: mis talentos, peticiones, recuentos y catálogo.
    path("talentos/", include("talentos.urls")),
    # Módulo «solicitudes»: pedir con apoyos y responder.
    path("solicitudes/", include("solicitudes.urls")),
    # Módulo «comunicaciones»: notificaciones y preferencias de aviso.
    path("comunicaciones/", include("comunicaciones.urls")),
    # Módulo «administracion»: pantallas del superadmin (personas de la bóveda, dominios y alias).
    path("usuarios/", include("administracion.urls")),
    # Módulo «tipologias»: Configuración → Tipologías.
    path("configuracion/tipologias/", include("tipologias.urls")),
    # Módulo «audiencias»: Configuración → Visibilidad.
    path("configuracion/visibilidad/", include("audiencias.urls")),
    # Módulo «etiquetas»: sugerencias del selector de etiquetas.
    path("etiquetas/", include("etiquetas.urls")),
    # Módulo «mantenimiento»: documentación del proyecto y entrada a la trastienda.
    path("mantenimiento/", include("mantenimiento.urls")),
    # Módulo «base»: la portada y el escaparate de componentes.
    path("", include("base.urls")),
]

# Direcciones internas de la barra de depuración (solo en desarrollo, ver config/settings.py).
if settings.USAR_BARRA_DE_DEPURACION:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()
