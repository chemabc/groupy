"""
Tablas del módulo «documentos»: órdenes del día (ODD), actas y documentos libres, con el registro de
cambios y los comentarios (ver docs/diseno.md, apartado 13).
"""

from django.conf import settings
from django.db import models


class Documento(models.Model):
    """
    Un texto con formato (Markdown) que escriben quienes tienen el cometido de redacción: el orden del día
    de una reunión, su acta o un documento libre. Puede colgar de otra cosa (una reunión, un proyecto) y
    entonces toma su grupo y quién lo ve. Detrás de cada párrafo se guarda quién ha contribuido a él.
    """

    ODD = "odd"
    ACTA = "acta"
    LIBRE = "libre"
    TIPOS = [(ODD, "Orden del día"), (ACTA, "Acta"), (LIBRE, "Documento")]
    BORRADOR = "borrador"
    APROBADO = "aprobado"
    ESTADOS = [(BORRADOR, "Borrador"), (APROBADO, "Aprobado")]

    tipo = models.CharField("tipo", max_length=10, choices=TIPOS, default=LIBRE, help_text="Orden del día, acta o documento libre.")
    titulo = models.CharField("título", max_length=200, help_text="Cómo se llama: «Acta de la asamblea del 14 de noviembre».")
    texto = models.TextField("texto", blank=True, help_text="El documento, en Markdown (# títulos, - listas, **negrita**…).")
    grupo = models.ForeignKey("grupos.Grupo", on_delete=models.CASCADE, related_name="+", verbose_name="grupo", help_text="Grupo al que pertenece.")
    audiencia = models.ForeignKey(
        "audiencias.Audiencia", on_delete=models.PROTECT, related_name="+", verbose_name="quién lo ve",
        help_text="Quién puede leerlo y comentarlo. Si cuelga de una reunión, el mismo que la reunión.",
    )
    ancla_tipo = models.CharField("cuelga de (tipo)", max_length=60, blank=True, help_text="Si cuelga de algo, su tipo: «eventos.evento»…")
    ancla_id = models.PositiveBigIntegerField("cuelga de (número)", null=True, blank=True, help_text="Si cuelga de algo, su número.")
    origen = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="derivados", verbose_name="sale de",
        help_text="El orden del día del que sale un acta.",
    )
    creador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="creado por", help_text="Quién lo creó."
    )
    estado = models.CharField("estado", max_length=10, choices=ESTADOS, default=BORRADOR, help_text="Borrador (se puede cambiar) o aprobado (ya no).")
    version = models.PositiveIntegerField("versión", default=0, help_text="Sube con cada cambio; sirve para no pisar el trabajo de otra persona.")
    autorias = models.JSONField(
        "quién ha escrito cada párrafo", default=list, blank=True,
        help_text="Una lista por párrafo con los alias que han contribuido a él; el último, quien lo cambió por última vez.",
    )
    creado = models.DateTimeField("creado", auto_now_add=True, help_text="Cuándo se creó.")
    actualizado = models.DateTimeField("último cambio", auto_now=True, help_text="Cuándo cambió por última vez.")
    aprobado_el = models.DateTimeField("aprobado el", null=True, blank=True, help_text="Cuándo se aprobó.")

    class Meta:
        verbose_name = "documento"
        verbose_name_plural = "documentos"
        ordering = ["-actualizado", "-pk"]
        indexes = [models.Index(fields=["ancla_tipo", "ancla_id"], name="documento_por_ancla")]

    # Texto con el que se muestra: su título.
    def __str__(self):
        return self.titulo


class CambioDeDocumento(models.Model):
    """
    Una línea del registro de cambios de un documento: quién lo cambió, cuándo y qué tocó. Nadie puede
    borrarlo (tampoco el superadmin): así nadie cambia un acta en silencio.
    """

    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name="cambios", verbose_name="documento", help_text="El documento.")
    alias = models.CharField("quién", max_length=30, help_text="Alias de quien lo cambió (se guarda el texto: si la cuenta desaparece, sigue).")
    cuando = models.DateTimeField("cuándo", auto_now_add=True, help_text="Fecha y hora del cambio.")
    resumen = models.CharField("qué cambió", max_length=200, help_text="«2 párrafos cambiados, 1 nuevo», «aprobado»…")

    class Meta:
        verbose_name = "cambio de documento"
        verbose_name_plural = "cambios de documentos"
        ordering = ["-cuando", "-pk"]

    # Texto con el que se muestra: quién y qué.
    def __str__(self):
        return f"{self.alias}: {self.resumen}"


class Comentario(models.Model):
    """
    Un comentario o una propuesta de cambio de alguien que lee el documento (sin poder escribirlo), hasta que
    se aprueba.
    """

    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name="comentarios", verbose_name="documento", help_text="El documento.")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="quién", help_text="Quién lo escribe."
    )
    texto = models.TextField("comentario", help_text="El comentario o la propuesta de cambio.")
    creado = models.DateTimeField("escrito", auto_now_add=True, help_text="Cuándo se escribió.")

    class Meta:
        verbose_name = "comentario"
        verbose_name_plural = "comentarios"
        ordering = ["creado", "pk"]

    # Texto con el que se muestra: el principio del comentario.
    def __str__(self):
        return self.texto[:60]
