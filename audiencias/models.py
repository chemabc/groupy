"""
Tablas del módulo «audiencias»: quién puede ver cada cosa (ver docs/diseno.md, apartado 3.4).

Cada cosa que se publica (un proyecto, un evento, un bloque de una ficha…) guarda solo un número,
audiencia_id, que apunta a una fila de Audiencia. La audiencia dice quién lo ve: unas personas concretas
(lo privado), unos grupos con todos sus subgrupos (lo semiprivado), toda una organización o cualquiera
(lo público). Las audiencias iguales se comparten (misma «huella»), salvo las privadas, que son de una
sola cosa.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class Audiencia(models.Model):
    """
    Audiencia: quién puede ver algo. Se crea siempre con audiencias/servicios.py, que comprueba la regla
    entre organizaciones (nadie de otra organización sin una invitación aceptada).
    """

    # Tipos de audiencia.
    PRIVADA = "privada"
    GRUPOS = "grupos"
    ORGANIZACION = "organizacion"
    PUBLICA = "publica"
    TIPOS = [
        (PRIVADA, "Privada: solo las personas implicadas"),
        (GRUPOS, "Semiprivada: unos grupos y sus subgrupos"),
        (ORGANIZACION, "Toda la organización"),
        (PUBLICA, "Pública: cualquiera, sin alias"),
    ]

    tipo = models.CharField("tipo", max_length=20, choices=TIPOS, help_text="A quién llega, a grandes rasgos.")
    huella = models.CharField(
        "huella",
        max_length=200,
        unique=True,
        null=True,
        blank=True,
        help_text=(
            "Resumen de su composición («grupos:3,7», «organizacion:2», «publica»). Dos elecciones iguales "
            "dan la misma huella y comparten la fila. Vacía en las privadas, que no se comparten."
        ),
    )
    organizacion = models.ForeignKey(
        "grupos.Organizacion",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audiencias",
        verbose_name="organización",
        help_text=(
            "Organización dueña de lo que se ve. Solo pueden entrar personas y grupos de otras "
            "organizaciones si hay una invitación aceptada. Vacía en lo personal y en lo público."
        ),
    )
    ancla_tipo = models.CharField(
        "tipo de lo que se ve",
        max_length=60,
        blank=True,
        help_text="Si la audiencia es de una sola cosa (privada, o con grupos invitados): su tipo de ancla.",
    )
    ancla_id = models.PositiveBigIntegerField(
        "id de lo que se ve", null=True, blank=True, help_text="Si la audiencia es de una sola cosa: su número."
    )
    personal = models.BooleanField(
        "personal",
        default=False,
        help_text=(
            "Contenido personal privado (proyectos y tareas personales): ni el superadmin lo ve desde la "
            "interfaz."
        ),
    )
    creada_el = models.DateField("creada el día", default=timezone.localdate, help_text="Día en que se creó.")

    class Meta:
        verbose_name = "audiencia"
        verbose_name_plural = "audiencias"

    # Texto con el que se muestra: «Audiencia 7 (grupos)».
    def __str__(self):
        return f"Audiencia {self.pk} ({self.get_tipo_display()})"


class GrupoDeAudiencia(models.Model):
    """Un grupo de una audiencia: lo ven sus miembros y los de todos sus subgrupos."""

    audiencia = models.ForeignKey(
        Audiencia, on_delete=models.CASCADE, related_name="grupos", verbose_name="audiencia",
        help_text="La audiencia.",
    )
    grupo = models.ForeignKey(
        "grupos.Grupo", on_delete=models.CASCADE, related_name="+", verbose_name="grupo",
        help_text="Lo ven las personas de este grupo y de todos sus subgrupos.",
    )

    class Meta:
        verbose_name = "grupo de una audiencia"
        verbose_name_plural = "grupos de las audiencias"
        constraints = [models.UniqueConstraint(fields=["audiencia", "grupo"], name="grupo_de_audiencia_unico")]

    # Texto con el que se muestra: el grupo.
    def __str__(self):
        return str(self.grupo)


class PersonaDeAudiencia(models.Model):
    """Una persona de una audiencia privada: quien la creó, la persona responsable, quien tiene un cometido…"""

    audiencia = models.ForeignKey(
        Audiencia, on_delete=models.CASCADE, related_name="personas", verbose_name="audiencia",
        help_text="La audiencia.",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+", verbose_name="usuario",
        help_text="Persona que lo ve.",
    )

    class Meta:
        verbose_name = "persona de una audiencia"
        verbose_name_plural = "personas de las audiencias"
        constraints = [models.UniqueConstraint(fields=["audiencia", "usuario"], name="persona_de_audiencia_unica")]

    # Texto con el que se muestra: la persona.
    def __str__(self):
        return str(self.usuario)


class ConfiguracionDeVisibilidad(models.Model):
    """
    Qué niveles de visibilidad ofrece una organización a quien publica algo en ella. La ajustan el
    superadmin y el admin de la organización. Si una organización no tiene, vale la de por defecto (todo
    lo más cerrado: hasta el grupo padre, sin «toda la organización» ni lo público).
    """

    organizacion = models.OneToOneField(
        "grupos.Organizacion", on_delete=models.CASCADE, related_name="configuracion_de_visibilidad",
        verbose_name="organización", help_text="La organización.",
    )
    altura_maxima = models.PositiveSmallIntegerField(
        "altura máxima",
        default=1,
        help_text=(
            "Hasta dónde se puede subir al elegir «mi grupo y los de arriba»: 0, solo el propio grupo; 1, "
            "hasta el grupo padre; 2, hasta el abuelo; y así."
        ),
    )
    permite_toda_la_organizacion = models.BooleanField(
        "permite «toda la organización»", default=False, help_text="Si se puede publicar para toda la organización."
    )
    permite_publico = models.BooleanField(
        "permite lo público",
        default=False,
        help_text="Si se puede publicar para cualquiera, también sin cuenta (siempre sin alias).",
    )

    class Meta:
        verbose_name = "configuración de visibilidad"
        verbose_name_plural = "configuraciones de visibilidad"

    # Texto con el que se muestra: «Visibilidad de ORG Tajo».
    def __str__(self):
        return f"Visibilidad de {self.organizacion}"
