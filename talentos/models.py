"""
Tablas del módulo «talentos» (ver docs/diseno.md, apartado 8.3):

- Talento: algo que una persona puede ofrecer, de un catálogo común: un recurso («Furgoneta») o una
  habilidad («Trabajos verticales»), con palabras relacionadas.
- TalentoDePersona: que una persona tiene un talento. Es un dato personal: nadie ve quién lo tiene.
- Compartido: con qué grupos comparte cada persona cada talento. Los miembros del grupo ven cuántas
  personas lo comparten con él, nunca quiénes.
- PeticionDeTalentos y Necesidad: lo que pide una administración a un grupo (por ejemplo, «2 furgonetas
  y 1 persona de trabajos verticales» para una mudanza).
- Ofrecimiento: que alguien ofrece un talento para una petición. Solo entonces se revela su alias, y solo
  a la administración.
"""

from django.conf import settings
from django.db import models

from base.tablas import forma_de_frase, normalizar


class Talento(models.Model):
    """Talento del catálogo común: un recurso o una habilidad, con sus palabras relacionadas."""

    RECURSO = "recurso"
    HABILIDAD = "habilidad"
    TIPOS = [(RECURSO, "Recurso (algo que se tiene)"), (HABILIDAD, "Habilidad (algo que se sabe hacer)")]

    nombre = models.CharField("nombre", max_length=60, help_text="Como se verá: «Furgoneta», «Trabajos verticales».")
    normalizada = models.CharField("nombre normalizado", max_length=60, unique=True, editable=False, help_text="Sin tildes ni mayúsculas, para no repetir.")
    tipo = models.CharField("tipo", max_length=20, choices=TIPOS, default=HABILIDAD, help_text="Si es algo que se tiene o algo que se sabe hacer.")
    relacionadas = models.CharField(
        "palabras relacionadas", max_length=300, blank=True, help_text="Sinónimos separados por comas («Camioneta, Transporte»): al buscarlas, aparece este talento."
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="creado por",
        help_text="Quién lo añadió al catálogo.",
    )

    class Meta:
        verbose_name = "talento"
        verbose_name_plural = "talentos"
        ordering = ["normalizada"]

    # Texto con el que se muestra: su nombre.
    def __str__(self):
        return self.nombre

    # Antes de guardar: el nombre y las relacionadas en forma fija (primera mayúscula, sin tildes; como las
    # etiquetas) y el nombre normalizado.
    def save(self, *args, **kwargs):
        self.nombre = forma_de_frase(" ".join(self.nombre.split()))
        self.normalizada = normalizar(self.nombre)
        palabras = [forma_de_frase(" ".join(p.split())) for p in self.relacionadas.split(",") if p.strip()]
        self.relacionadas = ", ".join(palabras)
        super().save(*args, **kwargs)


class TalentoDePersona(models.Model):
    """Que una persona tiene un talento. Dato personal: los demás solo ven cuántas personas lo comparten."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="talentos", verbose_name="usuario", help_text="Quién.")
    talento = models.ForeignKey(Talento, on_delete=models.CASCADE, related_name="personas", verbose_name="talento", help_text="Qué talento.")
    detalle = models.CharField(
        "detalle", max_length=200, blank=True, help_text="Algo más, solo para ti y para quien te pida el talento si lo ofreces («furgoneta de 9 plazas»)."
    )

    class Meta:
        verbose_name = "talento de una persona"
        verbose_name_plural = "talentos de las personas"
        constraints = [models.UniqueConstraint(fields=["usuario", "talento"], name="talento_de_persona_unico")]

    # Texto con el que se muestra: «Nutria: Furgoneta».
    def __str__(self):
        return f"{self.usuario}: {self.talento}"


class Compartido(models.Model):
    """Que una persona comparte uno de sus talentos con un grupo (en el que está)."""

    talento_de_persona = models.ForeignKey(
        TalentoDePersona, on_delete=models.CASCADE, related_name="compartidos", verbose_name="talento de la persona", help_text="El talento."
    )
    grupo = models.ForeignKey("grupos.Grupo", on_delete=models.CASCADE, related_name="+", verbose_name="grupo", help_text="Con qué grupo lo comparte.")

    class Meta:
        verbose_name = "talento compartido"
        verbose_name_plural = "talentos compartidos"
        constraints = [models.UniqueConstraint(fields=["talento_de_persona", "grupo"], name="compartido_unico")]

    # Texto con el que se muestra: «Nutria: Furgoneta con GRU Henares».
    def __str__(self):
        return f"{self.talento_de_persona} con {self.grupo}"


class PeticionDeTalentos(models.Model):
    """
    Lo que una administración pide a un grupo: unos talentos, cuántos de cada uno y para qué. Llega a
    quienes los comparten con ese grupo (o con sus subgrupos). Más adelante, también desde un proyecto.
    """

    ABIERTA = "abierta"
    CERRADA = "cerrada"
    ESTADOS = [(ABIERTA, "Abierta"), (CERRADA, "Cerrada")]

    grupo = models.ForeignKey(
        "grupos.Grupo", on_delete=models.CASCADE, related_name="+", verbose_name="grupo",
        help_text="A qué grupo se pide (con sus subgrupos). Su administración ve quién se ofrece.",
    )
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="autor", help_text="Quién la hace.")
    asunto = models.CharField("para qué", max_length=120, help_text="En pocas palabras: «Mudanza del local».")
    descripcion = models.TextField("descripción", blank=True, help_text="Cuándo, dónde y lo que haga falta saber.")
    estado = models.CharField("estado", max_length=20, choices=ESTADOS, default=ABIERTA, help_text="Abierta (se aceptan ofrecimientos) o cerrada.")
    creada = models.DateTimeField("creada", auto_now_add=True, help_text="Cuándo se hizo.")
    ancla_tipo = models.CharField("tipo de aquello", max_length=60, blank=True, help_text="Si es para algo concreto (un proyecto), su tipo de ancla.")
    ancla_id = models.PositiveBigIntegerField("id de aquello", null=True, blank=True, help_text="Y su número.")

    class Meta:
        verbose_name = "petición de talentos"
        verbose_name_plural = "peticiones de talentos"
        ordering = ["-creada", "-pk"]

    # Texto con el que se muestra: el asunto.
    def __str__(self):
        return self.asunto


class Necesidad(models.Model):
    """Un talento que hace falta en una petición, y cuántas personas (o recursos)."""

    peticion = models.ForeignKey(PeticionDeTalentos, on_delete=models.CASCADE, related_name="necesidades", verbose_name="petición", help_text="La petición.")
    talento = models.ForeignKey(Talento, on_delete=models.PROTECT, related_name="+", verbose_name="talento", help_text="Qué hace falta.")
    cantidad = models.PositiveSmallIntegerField("cuántos", default=1, help_text="Cuántas personas (o recursos) hacen falta.")

    class Meta:
        verbose_name = "talento que hace falta"
        verbose_name_plural = "talentos que hacen falta"
        constraints = [models.UniqueConstraint(fields=["peticion", "talento"], name="necesidad_unica")]

    # Texto con el que se muestra: «2 × Furgoneta».
    def __str__(self):
        return f"{self.cantidad} × {self.talento}"


class Ofrecimiento(models.Model):
    """Que una persona ofrece un talento para una petición. La administración ve su alias; el resto, no."""

    necesidad = models.ForeignKey(Necesidad, on_delete=models.CASCADE, related_name="ofrecimientos", verbose_name="talento pedido", help_text="Qué ofrece.")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+", verbose_name="usuario", help_text="Quién lo ofrece.")
    mensaje = models.CharField("mensaje", max_length=300, blank=True, help_text="Algo que quiera añadir («solo por la tarde»).")
    creado = models.DateTimeField("ofrecido", auto_now_add=True, help_text="Cuándo lo ofreció.")

    class Meta:
        verbose_name = "ofrecimiento"
        verbose_name_plural = "ofrecimientos"
        constraints = [models.UniqueConstraint(fields=["necesidad", "usuario"], name="ofrecimiento_unico")]

    # Texto con el que se muestra: «Nutria ofrece Furgoneta».
    def __str__(self):
        return f"{self.usuario} ofrece {self.necesidad.talento}"
