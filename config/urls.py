"""
Lista de direcciones web de la aplicación y qué vista responde a cada una.

De momento solo hay una página de comprobación. Cada módulo añadirá sus direcciones a medida que se
programe (fase 0 en adelante, ver docs/diseno.md, apartado 19).
"""

from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path


# Página de comprobación: si se ve el texto, Django está instalado y responde. Se quitará cuando exista
# la pantalla de inicio de verdad.
def funciona(request):
    return HttpResponse("<body>Gestión de asambleas v2: Django responde.</body>")


urlpatterns = [
    # Panel de Django: solo trastienda técnica de emergencia para el superadmin (ver diseno.md, apartado 4).
    path("trastienda/", admin.site.urls),
    # Página de comprobación.
    path("", funciona),
]

# Direcciones internas de la barra de depuración (solo en desarrollo, ver config/settings.py).
if settings.USAR_BARRA_DE_DEPURACION:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()
