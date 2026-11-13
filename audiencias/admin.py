"""
Audiencias y configuración de visibilidad en la trastienda (el panel de Django), solo para consultar y
para emergencias.
"""

from django.contrib import admin

from base.trastienda import ConAyuda

from .models import Audiencia, ConfiguracionDeVisibilidad
from .servicios import describir


@admin.register(Audiencia)
class AudienciaEnLaTrastienda(ConAyuda, admin.ModelAdmin):
    """Audiencias: quién ve cada cosa. Solo se consultan."""

    ayuda = (
        "Cada cosa que se publica apunta a una audiencia, que dice quién la ve: las personas implicadas "
        "(privada), unos grupos con todos sus subgrupos, toda una organización o cualquiera (pública). Las "
        "audiencias iguales se comparten entre cosas; las privadas no.\n\n"
        "Nadie de otra organización ve nada sin una invitación aceptada para eso concreto.\n\n"
        "Se crean desde la aplicación al publicar; aquí solo se consultan."
    )
    list_display = ["id", "tipo", "organizacion", "explicacion", "personal", "creada_el"]
    list_filter = ["tipo", "personal"]
    readonly_fields = ["explicacion"]

    # Columna y campo «a quién llega», con la frase que verá quien publica.
    @admin.display(description="a quién llega")
    def explicacion(self, audiencia):
        return describir(audiencia)

    # Las audiencias no se crean ni se cambian a mano: lo hace la aplicación, comprobando las reglas.
    def has_add_permission(self, request):
        return False

    # No se cambian a mano (ver has_add_permission).
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ConfiguracionDeVisibilidad)
class ConfiguracionEnLaTrastienda(ConAyuda, admin.ModelAdmin):
    """Qué niveles de visibilidad ofrece cada organización."""

    ayuda = (
        "Qué puede elegir quien publica algo en cada organización: hasta cuántos niveles por encima de su "
        "grupo puede subir, si puede publicar para toda la organización y si puede hacerlo público.\n\n"
        "Una organización sin configuración usa la más cerrada: hasta el grupo padre, sin «toda la "
        "organización» y sin lo público."
    )
    list_display = ["organizacion", "altura_maxima", "permite_toda_la_organizacion", "permite_publico"]
