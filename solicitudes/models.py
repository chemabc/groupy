"""
Tablas del módulo «solicitudes» (ver docs/diseno.md, apartado 6):

- Solicitud: algo que una persona pide a un grupo (entrar en él, abrir un debate…) y que necesita
  apoyos de sus miembros, y a veces el sí de su administración, antes de una fecha.
- Apoyo: la respuesta de una persona a una solicitud: la apoya o la rechaza. Los rechazos no vetan.
- AjusteDeSolicitud: cuántos apoyos y cuántos días tiene cada tipo de solicitud en una organización (o
  en toda la plataforma). Sin ajuste, valen los del contrato del módulo que la declara.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class Solicitud(models.Model):
    """
    Solicitud: lo que una persona pide a un grupo. Queda pendiente hasta que consigue los apoyos (y, si
    hace falta, el sí de la administración o del superadmin), la cancela quien la pidió o caduca. Al
    aceptarse, el módulo que declara su tipo crea lo pedido (ver TipoDeSolicitud en base/contrato.py).
    """

    PENDIENTE = "pendiente"
    ACEPTADA = "aceptada"
    CANCELADA = "cancelada"
    CADUCADA = "caducada"
    ESTADOS = [(PENDIENTE, "Pendiente"), (ACEPTADA, "Aceptada"), (CANCELADA, "Cancelada"), (CADUCADA, "Caducada")]

    tipo = models.CharField("tipo", max_length=80, help_text="Código del tipo de solicitud, tal como lo declara su módulo («grupos.entrar»).")
    grupo = models.ForeignKey(
        "grupos.Grupo", on_delete=models.CASCADE, related_name="solicitudes", verbose_name="grupo",
        help_text="Grupo al que se pide. Pueden apoyarla sus miembros (también los de sus subgrupos).",
    )
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="solicitudes", verbose_name="solicitante",
        help_text="Quien la pide. No cuenta como apoyo.",
    )
    descripcion = models.TextField("descripción", help_text="Qué se pide.")
    justificacion = models.TextField("justificación", blank=True, help_text="Por qué.")
    datos = models.JSONField("datos", default=dict, blank=True, help_text="Lo que necesita el módulo para crear lo pedido (los datos de su formulario).")
    apoyos_necesarios = models.PositiveSmallIntegerField("apoyos necesarios", help_text="Cuántos apoyos hacen falta (se fija al pedirla).")
    necesita_aprobacion = models.BooleanField(
        "necesita el sí de la administración", default=False, help_text="Si, además de los apoyos, hace falta el sí de un admin del grupo."
    )
    aprobada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        verbose_name="aprobada por", help_text="Admin (o superadmin) que dio el sí de la administración.",
    )
    por_el_superadmin = models.BooleanField(
        "aceptada por el superadmin", default=False, help_text="Si la aceptó directamente el superadmin, sin esperar a los apoyos."
    )
    apoyos = models.PositiveSmallIntegerField("apoyos", default=0, help_text="Cuántas personas la apoyan.")
    rechazos = models.PositiveSmallIntegerField("rechazos", default=0, help_text="Cuántas la rechazan (solo se muestra el número).")
    caduca_el = models.DateField("caduca el día", help_text="Si ese día no tiene lo necesario, caduca.")
    estado = models.CharField("estado", max_length=20, choices=ESTADOS, default=PENDIENTE, help_text="En qué punto está.")
    creada = models.DateTimeField("pedida", auto_now_add=True, help_text="Cuándo se pidió.")
    resuelta_el = models.DateTimeField("resuelta", null=True, blank=True, help_text="Cuándo se aceptó, se canceló o caducó.")
    ancla_tipo = models.CharField("tipo de lo creado", max_length=60, blank=True, help_text="Al aceptarse, tipo de lo que se creó.")
    ancla_id = models.PositiveBigIntegerField("id de lo creado", null=True, blank=True, help_text="Al aceptarse, número de lo que se creó.")

    class Meta:
        verbose_name = "solicitud"
        verbose_name_plural = "solicitudes"
        ordering = ["-creada", "-pk"]
        indexes = [models.Index(fields=["estado", "caduca_el"], name="solicitud_por_estado")]

    # Texto con el que se muestra: la descripción.
    def __str__(self):
        return self.descripcion[:60]

    # Si ya tiene todo lo necesario para aceptarse: los apoyos y, si hace falta, el sí de la administración.
    @property
    def completa(self):
        return self.apoyos >= self.apoyos_necesarios and (not self.necesita_aprobacion or self.aprobada_por_id is not None)


class Apoyo(models.Model):
    """Respuesta de una persona a una solicitud: la apoya o la rechaza. Se puede retirar mientras está pendiente."""

    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, related_name="respuestas", verbose_name="solicitud", help_text="La solicitud.")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+", verbose_name="usuario", help_text="Quién responde.")
    acepta = models.BooleanField("la apoya", help_text="Marcado: la apoya. Sin marcar: la rechaza (no veta; solo cuenta).")
    creado = models.DateTimeField("respondida", default=timezone.now, help_text="Cuándo respondió.")

    class Meta:
        verbose_name = "apoyo"
        verbose_name_plural = "apoyos"
        constraints = [models.UniqueConstraint(fields=["solicitud", "usuario"], name="un_apoyo_por_persona")]

    # Texto con el que se muestra: «Nutria apoya» o «Nutria rechaza».
    def __str__(self):
        return f"{self.usuario} {'apoya' if self.acepta else 'rechaza'}"


class AjusteDeSolicitud(models.Model):
    """
    Cuántos apoyos necesita un tipo de solicitud y cuántos días tiene, en una organización o en toda la
    plataforma (organización vacía, lo pone el superadmin). Vale el de la organización si lo hay; si no, el
    de la plataforma; si no, el del contrato.
    """

    organizacion = models.ForeignKey(
        "grupos.Organizacion", on_delete=models.CASCADE, null=True, blank=True, related_name="+",
        verbose_name="organización", help_text="La organización. Vacía: para toda la plataforma.",
    )
    tipo = models.CharField("tipo", max_length=80, help_text="Código del tipo de solicitud.")
    apoyos = models.PositiveSmallIntegerField("apoyos", help_text="Apoyos de miembros del grupo que hacen falta.")
    dias = models.PositiveSmallIntegerField("días", help_text="Días para conseguirlos antes de caducar.")

    class Meta:
        verbose_name = "ajuste de solicitud"
        verbose_name_plural = "ajustes de solicitudes"
        constraints = [models.UniqueConstraint(fields=["organizacion", "tipo"], name="ajuste_de_solicitud_unico", nulls_distinct=False)]

    # Texto con el que se muestra: «grupos.entrar en ORG Tajo: 2 apoyos, 15 días».
    def __str__(self):
        return f"{self.tipo} en {self.organizacion or 'la plataforma'}: {self.apoyos} apoyos, {self.dias} días"
