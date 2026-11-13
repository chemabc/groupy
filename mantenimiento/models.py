"""
Tablas del módulo «mantenimiento».
"""

from django.db import models


class AjustesDeMantenimiento(models.Model):
    """
    Ajustes de las herramientas de mantenimiento, que cambia el superadmin. Hay una sola fila (la 1);
    se lee con AjustesDeMantenimiento.actuales().
    """

    alta_masiva_de_usuarios = models.BooleanField(
        "permitir el alta masiva de usuarios",
        default=False,
        help_text=(
            "Si se pueden crear usuarios a partir de una hoja de cálculo (Pruebas → Importar usuarios). Pensado "
            "para el periodo de pruebas: crea alias sin pasar por la bóveda. Empieza apagado."
        ),
    )

    class Meta:
        verbose_name = "ajustes de mantenimiento"
        verbose_name_plural = "ajustes de mantenimiento"

    # Texto con el que se muestra.
    def __str__(self):
        return "Ajustes de mantenimiento"

    # Devuelve la fila de ajustes, creándola (con los valores por defecto) si aún no existe.
    @classmethod
    def actuales(cls):
        ajustes, _creada = cls.objects.get_or_create(pk=1)
        return ajustes
