"""
Tablas del módulo «decisiones» (ver docs/diseno.md, apartado 16).
"""

from django.db import models
from django.utils import timezone


class Decision(models.Model):
    """
    Una decisión de un grupo: un acuerdo de un acta, el resultado de un debate o de una consulta. Se crea
    sola cuando su origen la anuncia y nunca se borra; si se vuelve a decidir, queda sustituida por la nueva.
    """

    CONSENSO = "consenso"
    VOTACION = "votacion"
    DEBATE = "debate"
    CONSULTA = "consulta"
    FORMAS = [(CONSENSO, "Consenso"), (VOTACION, "Votación"), (DEBATE, "Debate"), (CONSULTA, "Consulta")]

    texto = models.TextField("decisión", help_text="Qué se ha decidido.")
    forma = models.CharField("cómo se tomó", max_length=20, choices=FORMAS, help_text="Por consenso, por votación, al cerrar un debate o en una consulta.")
    detalle = models.CharField("detalle", max_length=200, blank=True, help_text="El recuento o lo que haga falta saber: «12 a favor, 3 en contra».")
    grupo = models.ForeignKey(
        "grupos.Grupo", on_delete=models.CASCADE, related_name="+", verbose_name="grupo", help_text="Grupo que la tomó."
    )
    audiencia = models.ForeignKey(
        "audiencias.Audiencia", on_delete=models.PROTECT, related_name="+", verbose_name="quién la ve",
        help_text="Quién puede verla: la misma audiencia que su origen (quien podía participar).",
    )
    origen_tipo = models.CharField("tipo de origen", max_length=60, help_text="De dónde sale, como ancla: «documentos.documento», «debates.debate»…")
    origen_id = models.PositiveBigIntegerField("número del origen", help_text="Número del acta, el debate o la consulta.")
    enlace = models.CharField("enlace", max_length=300, blank=True, help_text="Dirección de su origen, para ir a verlo.")
    tomada = models.DateTimeField("tomada el", default=timezone.now, help_text="Cuándo se tomó.")
    sustituida_por = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="sustituye_a", verbose_name="sustituida por",
        help_text="La decisión más nueva que la reemplaza. Vacío: sigue vigente.",
    )

    class Meta:
        verbose_name = "decisión"
        verbose_name_plural = "decisiones"
        ordering = ["-tomada", "-pk"]
        indexes = [models.Index(fields=["origen_tipo", "origen_id"], name="decision_por_origen")]

    # Texto con el que se muestra: el principio de la decisión.
    def __str__(self):
        return self.texto[:80]
