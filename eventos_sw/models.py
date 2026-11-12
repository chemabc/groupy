"""
Tablas del módulo «eventos_sw».
"""

from django.db import models
from django.db.models import Q
from django.utils import timezone


class AvisoPendiente(models.Model):
    """
    Bandeja de salida: un aviso asíncrono que un módulo debe recibir y que aún no ha recibido.

    Cuando se emite un eventos_sw, se crea una fila por cada escucha asíncrona, dentro de la misma
    transacción que el cambio. Así, si el cambio se deshace, el aviso tampoco existe. La orden
    «procesar_bandeja» ejecuta cada aviso y borra su fila si sale bien; si falla, lo reintenta más tarde y,
    tras varios fallos, lo deja marcado como fallido para que alguien lo revise.
    """

    # Nombre del eventos_sw. Ejemplo: «consultas.cerrada».
    evento = models.CharField(
        "evento",
        max_length=100,
        help_text="Nombre del aviso interno que se emitió, por ejemplo «consultas.cerrada».",
    )
    # Ruta de la función que debe recibirlo.
    receptor = models.CharField(
        "receptor",
        max_length=200,
        help_text="Función del módulo que escucha y que debe ejecutarse con este aviso.",
    )
    # Datos del aviso (solo valores simples: números, textos, listas).
    datos = models.JSONField(
        "datos",
        default=dict,
        blank=True,
        help_text="Datos que acompañan al aviso, como el número de la consulta cerrada.",
    )
    # Cuándo se emitió.
    creado = models.DateTimeField(
        "creado",
        default=timezone.now,
        help_text="Momento en que se emitió el aviso.",
    )
    # A partir de cuándo se puede (re)intentar.
    proximo_intento = models.DateTimeField(
        "próximo intento",
        default=timezone.now,
        help_text="La bandeja no lo procesará antes de este momento. Tras un fallo, se retrasa cada vez más.",
    )
    # Cuántas veces ha fallado.
    intentos = models.PositiveSmallIntegerField(
        "intentos fallidos",
        default=0,
        help_text="Número de veces que la función receptora ha fallado con este aviso.",
    )
    # Explicación del último fallo.
    ultimo_error = models.TextField(
        "último error",
        blank=True,
        help_text="Error del último intento fallido, para poder corregirlo.",
    )
    # Si se ha dejado de intentar.
    fallido = models.BooleanField(
        "fallido",
        default=False,
        help_text="Ha fallado demasiadas veces y ya no se reintenta solo. Hay que revisarlo a mano.",
    )

    class Meta:
        verbose_name = "aviso pendiente"
        verbose_name_plural = "avisos pendientes"
        indexes = [
            # Índice para la consulta de la bandeja («los no fallidos cuyo momento ya ha llegado»).
            # Es parcial: solo incluye las filas no fallidas, así se mantiene pequeño.
            models.Index(
                fields=["proximo_intento"],
                condition=Q(fallido=False),
                name="aviso_pendiente_por_procesar",
            ),
        ]

    # Texto con el que se muestra el aviso en la trastienda y en los mensajes de error.
    def __str__(self):
        return f"{self.evento} → {self.receptor}"
