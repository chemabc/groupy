"""
Tablas del módulo «comunicaciones» (ver docs/diseno.md, apartado 17):

- Notificacion: un aviso a una persona («Han invitado a GRU Segre…»), que aparece en su bandeja de
  «Comunicaciones → Notificaciones». Lo crea el repartidor (comunicaciones/servicios.py) a partir de los
  tipos de aviso que declaran los módulos en su contrato.
- PreferenciaDeAviso: que una persona ha desactivado (o vuelto a activar) un tipo de aviso. Sin fila, el
  aviso está activado.

Los mensajes y conversaciones llegarán en la siguiente pieza.
"""

from django.conf import settings
from django.db import models

from base.contrato import ORIGENES_DE_AVISO


class Notificacion(models.Model):
    """
    Notificación: un aviso para una persona. Se ve en su bandeja hasta que la borra. Las vistas se pueden
    limpiar todas de una vez; más adelante, el módulo «limpieza» borrará las vistas a los 90 días y las no
    vistas a los 365 (lo podrá cambiar el superadmin).
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificaciones",
        verbose_name="usuario", help_text="A quién va dirigida.",
    )
    tipo = models.CharField(
        "tipo de aviso", max_length=80, help_text="Código del tipo de aviso, tal como lo declara su módulo («grupos.invitacion_recibida»)."
    )
    origen = models.CharField(
        "origen", max_length=20, choices=ORIGENES_DE_AVISO,
        help_text="Bandeja en la que aparece: organización y grupos, superadmin, admins, proyectos, eventos, debates, solicitudes o sistema.",
    )
    texto = models.TextField("texto", help_text="Lo que se le cuenta, en una o dos frases.")
    enlace = models.CharField("enlace", max_length=300, blank=True, help_text="Dirección a la que lleva al pulsarla.")
    creada = models.DateTimeField("creada", auto_now_add=True, help_text="Cuándo se creó.")
    vista_el = models.DateTimeField(
        "vista el", null=True, blank=True, help_text="Cuándo la vio (la abrió o la marcó como vista). Vacío: sin ver."
    )

    class Meta:
        verbose_name = "notificación"
        verbose_name_plural = "notificaciones"
        ordering = ["-creada", "-pk"]
        indexes = [models.Index(fields=["usuario", "vista_el"], name="notificacion_por_usuario")]

    # Texto con el que se muestra: el principio del texto.
    def __str__(self):
        return self.texto[:60]


class PreferenciaDeAviso(models.Model):
    """
    Si una persona quiere recibir un tipo de aviso. Sin fila, sí. De momento solo hay un canal (la web);
    el correo y Telegram llegarán después, como columnas nuevas.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="preferencias_de_aviso",
        verbose_name="usuario", help_text="De quién es la preferencia.",
    )
    tipo = models.CharField("tipo de aviso", max_length=80, help_text="Código del tipo de aviso.")
    web = models.BooleanField("en la web", default=True, help_text="Si le llega a su bandeja de notificaciones.")

    class Meta:
        verbose_name = "preferencia de aviso"
        verbose_name_plural = "preferencias de aviso"
        constraints = [models.UniqueConstraint(fields=["usuario", "tipo"], name="preferencia_de_aviso_unica")]

    # Texto con el que se muestra: «Lince: grupos.invitacion_recibida (no)».
    def __str__(self):
        return f"{self.usuario}: {self.tipo} ({'sí' if self.web else 'no'})"
