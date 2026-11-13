"""
Tablas del módulo «etiquetas»: palabras cortas (de una a tres) para clasificar y encontrar cosas, con sus
palabras relacionadas (sinónimos). Ver docs/diseno.md, apartado 3.2.

Cada organización tiene sus etiquetas (las de una no se ven ni se sugieren en otra, porque una etiqueta
ya cuenta algo), y el superadmin puede crear etiquetas comunes para todas. Cualquier cosa de cualquier
módulo se puede etiquetar con un ancla (tipo + id), sin clave ajena.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from base.tablas import forma_de_frase, normalizar


class Etiqueta(models.Model):
    """
    Etiqueta: una palabra o un grupo de dos o tres palabras («Huelga», «Local nuevo»). Se guardan
    siempre con la primera letra en mayúscula, el resto en minúsculas y sin tildes (la ñ se queda), así
    que «HUELGA», «huelga» y «Huélga» son la misma.
    """

    organizacion = models.ForeignKey(
        "grupos.Organizacion",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="etiquetas",
        verbose_name="organización",
        help_text="Organización a la que pertenece. Vacía: etiqueta común a todas (solo la crea el superadmin).",
    )
    nombre = models.CharField(
        "nombre", max_length=40,
        help_text="De una a tres palabras. Al guardar queda con la primera letra en mayúscula, el resto en minúsculas y sin tildes.",
    )
    normalizada = models.CharField(
        "nombre normalizado",
        max_length=40,
        editable=False,
        help_text="El nombre sin tildes, en minúsculas y sin espacios de más. Sirve para no repetir etiquetas.",
    )
    relacionadas = models.TextField(
        "palabras relacionadas",
        blank=True,
        help_text="Sinónimos o palabras parecidas, separadas por comas. Al buscar cualquiera de ellas, aparece esta etiqueta.",
    )
    relacionadas_normalizadas = models.TextField(
        "palabras relacionadas normalizadas", blank=True, editable=False, help_text="Las palabras relacionadas, normalizadas, para buscar."
    )
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        verbose_name="creada por", help_text="Quién la creó (al usarla por primera vez).",
    )
    creada_el = models.DateField("creada el día", default=timezone.localdate, help_text="Día en que se creó.")

    class Meta:
        verbose_name = "etiqueta"
        verbose_name_plural = "etiquetas"
        ordering = ["normalizada"]
        constraints = [
            models.UniqueConstraint(
                fields=["organizacion", "normalizada"], name="etiqueta_unica_en_su_organizacion",
                violation_error_message="Ya hay una etiqueta igual en esta organización.",
            ),
            models.UniqueConstraint(
                fields=["normalizada"], condition=models.Q(organizacion__isnull=True), name="etiqueta_comun_unica",
                violation_error_message="Ya hay una etiqueta común igual.",
            ),
        ]

    # Texto con el que se muestra: su nombre.
    def __str__(self):
        return self.nombre

    # Comprueba la etiqueta antes de guardarla desde un formulario (también desde la trastienda): limpia
    # el nombre y avisa si ya hay una igual en su organización o entre las comunes.
    def clean(self):
        from .servicios import comprobar_nombre

        super().clean()
        self.nombre = comprobar_nombre(self.nombre)
        self.normalizada = normalizar(self.nombre)
        repetidas = Etiqueta.objects.filter(normalizada=self.normalizada).exclude(pk=self.pk)
        repetidas = repetidas.filter(models.Q(organizacion__isnull=True) | models.Q(organizacion_id=self.organizacion_id))
        if repetidas.exists():
            raise ValidationError({"nombre": f"Ya hay una etiqueta «{repetidas.first()}» igual (en esta organización o común)."})

    # Guarda la etiqueta con su nombre y sus palabras relacionadas en la forma fija (primera letra en
    # mayúscula, el resto en minúsculas y sin tildes) y normalizados, se llame o no a clean().
    def save(self, *args, **kwargs):
        self.nombre = forma_de_frase(self.nombre)
        self.normalizada = normalizar(self.nombre)
        palabras = [forma_de_frase(palabra) for palabra in self.relacionadas.split(",") if palabra.strip()]
        self.relacionadas = ", ".join(palabras)
        self.relacionadas_normalizadas = ",".join(normalizar(palabra) for palabra in palabras)
        super().save(*args, **kwargs)


class EtiquetaDe(models.Model):
    """Que algo concreto (un proyecto, un debate…, indicado con un ancla) lleva una etiqueta."""

    etiqueta = models.ForeignKey(
        Etiqueta, on_delete=models.CASCADE, related_name="usos", verbose_name="etiqueta", help_text="La etiqueta."
    )
    ancla_tipo = models.CharField("tipo de lo etiquetado", max_length=60, help_text="Tipo de ancla («proyectos.proyecto»…).")
    ancla_id = models.PositiveBigIntegerField("id de lo etiquetado", help_text="Número de lo etiquetado.")

    class Meta:
        verbose_name = "uso de una etiqueta"
        verbose_name_plural = "usos de las etiquetas"
        constraints = [
            models.UniqueConstraint(fields=["etiqueta", "ancla_tipo", "ancla_id"], name="etiqueta_una_vez_por_cosa"),
        ]
        indexes = [models.Index(fields=["ancla_tipo", "ancla_id"], name="etiquetas_de_una_cosa")]

    # Texto con el que se muestra: «huelga en proyectos.proyecto 7».
    def __str__(self):
        return f"{self.etiqueta} en {self.ancla_tipo} {self.ancla_id}"
