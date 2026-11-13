"""
Tablas del módulo «limpieza» (ver docs/diseno.md, apartado 14.3):

- Plazo: los días para archivar y para borrar cada tipo de elemento, si el superadmin los ha cambiado
  (sin fila, valen los de partida que declara cada módulo en su contrato).
- Archivado: cada elemento archivado, con lo necesario para listarlo sin preguntar a su módulo (título,
  enlace, quién lo ve), si ya se ha avisado de que se va a borrar y si alguien lo ha conservado.
- Borrado: el registro visible de lo que se ha borrado (qué, cuándo y por qué). Nunca se borra.
"""

from django.conf import settings
from django.db import models


class Plazo(models.Model):
    """
    Plazos de un tipo de elemento elegidos por el superadmin. Sin fila, valen los de partida del contrato.
    """

    tipo = models.CharField(
        "tipo de elemento", max_length=80, unique=True, help_text="Código del tipo, tal como lo declara su módulo («proyectos.tarea»)."
    )
    activo = models.BooleanField(
        "activo", default=True, help_text="Si se limpia este tipo. Desactivado: no se archiva ni se borra nada de este tipo."
    )
    archivar_a = models.PositiveIntegerField(
        "días hasta archivar", help_text="Días desde que terminó hasta archivarlo (sale de las listas). No cuenta en lo que se borra sin archivar."
    )
    borrar_a = models.PositiveIntegerField(
        "días hasta borrar", help_text="Días desde que se archivó hasta borrarlo (o desde que terminó, en lo que se borra sin archivar)."
    )

    class Meta:
        verbose_name = "plazo de limpieza"
        verbose_name_plural = "plazos de limpieza"
        ordering = ["tipo"]

    # Texto con el que se muestra: «proyectos.tarea: 30 / 365».
    def __str__(self):
        return f"{self.tipo}: {self.archivar_a} / {self.borrar_a}"


class Archivado(models.Model):
    """
    Un elemento archivado: ya no sale en las listas de su módulo y se borrará pasado el plazo, salvo que
    alguien lo conserve. Quince días antes de borrarlo se avisa a quienes lo ven.
    """

    tipo = models.CharField("tipo de elemento", max_length=80, help_text="Código del tipo («proyectos.proyecto»).")
    objeto_id = models.PositiveBigIntegerField("id del elemento", help_text="El número del elemento en su tabla.")
    titulo = models.CharField("título", max_length=200, help_text="Su título al archivarlo, para listarlo sin abrir su módulo.")
    enlace = models.CharField("enlace", max_length=300, help_text="Dirección de su ficha.")
    audiencia = models.ForeignKey(
        "audiencias.Audiencia", on_delete=models.CASCADE, null=True, related_name="+", verbose_name="quién lo ve",
        help_text="La misma audiencia que el elemento: quien lo ve, lo ve en el archivo (y recibe los avisos).",
    )
    archivado_el = models.DateTimeField("archivado el", help_text="Cuándo se archivó. Desde aquí cuenta el plazo para borrarlo.")
    avisado_el = models.DateTimeField(
        "avisado el", null=True, blank=True, help_text="Cuándo se avisó de que se va a borrar. Se borra como pronto 15 días después."
    )
    conservado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="conservado por",
        help_text="Quién pulsó «Conservar».",
    )
    conservado_el = models.DateTimeField(
        "conservado el", null=True, blank=True, help_text="Cuándo se conservó. Lo conservado sigue archivado, pero no se borra solo."
    )

    class Meta:
        verbose_name = "elemento archivado"
        verbose_name_plural = "elementos archivados"
        ordering = ["-archivado_el", "-pk"]
        constraints = [models.UniqueConstraint(fields=["tipo", "objeto_id"], name="archivado_una_vez")]

    # Texto con el que se muestra: su título.
    def __str__(self):
        return self.titulo


class Borrado(models.Model):
    """
    Registro de un elemento borrado por la limpieza: se ve en «Archivo → Borrados» para que quede memoria
    de qué se borró y cuándo. Nunca se borra.
    """

    PLAZO = "plazo"
    A_MANO = "a_mano"
    MOTIVOS = [(PLAZO, "Pasó el plazo"), (A_MANO, "Poda a mano del superadmin")]

    tipo = models.CharField("tipo de elemento", max_length=80, help_text="Código del tipo («proyectos.proyecto»).")
    objeto_id = models.PositiveBigIntegerField("id del elemento", help_text="El número que tenía en su tabla.")
    titulo = models.CharField("título", max_length=200, help_text="Su título.")
    audiencia = models.ForeignKey(
        "audiencias.Audiencia", on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="quién lo veía",
        help_text="Quién lo veía: lo ve en el registro.",
    )
    archivado_el = models.DateTimeField("archivado el", help_text="Cuándo se archivó.")
    borrado_el = models.DateTimeField("borrado el", auto_now_add=True, help_text="Cuándo se borró.")
    motivo = models.CharField("motivo", max_length=10, choices=MOTIVOS, default=PLAZO, help_text="Por qué se borró: pasó el plazo o lo podó el superadmin.")
    quien = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="quién",
        help_text="Quién lo borró a mano. Vacío si fue por el plazo.",
    )

    class Meta:
        verbose_name = "elemento borrado"
        verbose_name_plural = "elementos borrados"
        ordering = ["-borrado_el", "-pk"]

    # Texto con el que se muestra: su título.
    def __str__(self):
        return self.titulo
