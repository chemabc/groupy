"""
Tablas del módulo «calendario» (ver docs/diseno.md, apartado 10.4):

- Recordatorio: una anotación libre en el calendario, sin módulo detrás («Llevar las pancartas al
  local», «Cierra el centro social»). La crea cualquier persona en uno de sus grupos y decide si la ve
  solo ella o su grupo; la administración del grupo puede abrirla al grupo padre y al abuelo.
- ClaveDeCalendario: la clave secreta de la suscripción .ics de cada persona (para ver su calendario en
  el móvil o en otro programa de calendario). Se puede cambiar cuando se quiera: la dirección anterior
  deja de funcionar.

Lo demás que sale en el calendario (eventos…) lo aporta cada módulo con su FuenteDeCalendario.
"""

import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


# Clave secreta nueva para la suscripción .ics: 32 caracteres al azar (letras, números, «-» y «_»).
def clave_nueva():
    return secrets.token_urlsafe(24)


class Recordatorio(models.Model):
    """
    Anotación libre en el calendario de un grupo. Quién la ve se guarda como audiencia: solo quien la
    crea, su grupo o (si lo decide la administración del grupo) hasta el grupo padre o el abuelo.
    """

    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+", verbose_name="autor", help_text="Quién lo apuntó.")
    grupo = models.ForeignKey("grupos.Grupo", on_delete=models.CASCADE, related_name="+", verbose_name="grupo", help_text="Grupo en el que se apunta.")
    titulo = models.CharField("título", max_length=150, help_text="Qué hay que recordar: «Llevar las pancartas al local».")
    notas = models.TextField("notas", blank=True, help_text="Más detalles, si hacen falta.")
    todo_el_dia = models.BooleanField("todo el día", default=False, help_text="Si ocupa días enteros, sin hora.")
    inicio = models.DateTimeField("empieza", help_text="Día y hora (si es de día entero, el primer día).")
    fin = models.DateTimeField(
        "termina", null=True, blank=True, help_text="Opcional. Si es de día entero, el último día que ocupa."
    )
    audiencia = models.ForeignKey(
        "audiencias.Audiencia", on_delete=models.PROTECT, related_name="+", verbose_name="quién lo ve",
        help_text="Quién puede verlo: solo quien lo apuntó, su grupo, o hasta el grupo padre o el abuelo.",
    )
    visibilidad = models.CharField("visibilidad elegida", max_length=30, default="privado", help_text="La opción elegida: «privado», «grupo:0»…")
    creado = models.DateTimeField("creado", auto_now_add=True, help_text="Cuándo se apuntó.")
    archivado = models.DateTimeField(
        "archivado el", null=True, blank=True,
        help_text="Cuándo lo archivó la limpieza, pasado un tiempo desde su fecha: sale de la lista, pero sigue en el calendario. Vacío: no archivado.",
    )

    class Meta:
        verbose_name = "recordatorio"
        verbose_name_plural = "recordatorios"
        ordering = ["inicio", "pk"]
        indexes = [models.Index(fields=["inicio"], name="recordatorio_por_fecha")]

    # Texto con el que se muestra: su título.
    def __str__(self):
        return self.titulo

    # Comprueba que no termina antes de empezar.
    def clean(self):
        super().clean()
        if self.fin and self.inicio and self.fin < self.inicio:
            raise ValidationError({"fin": "Tiene que terminar después de empezar."})


class ClaveDeCalendario(models.Model):
    """
    Clave secreta de la suscripción .ics de una persona. Quien conoce la dirección con la clave ve las
    fechas de su calendario sin iniciar sesión, por eso se puede cambiar en cualquier momento.
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+", verbose_name="usuario", help_text="De quién es el calendario."
    )
    clave = models.CharField("clave", max_length=64, unique=True, default=clave_nueva, help_text="Parte secreta de la dirección de suscripción.")
    creada = models.DateTimeField("creada", auto_now=True, help_text="Cuándo se creó o se cambió por última vez.")

    class Meta:
        verbose_name = "clave de calendario"
        verbose_name_plural = "claves de calendario"

    # Texto con el que se muestra: «Calendario de Nutria».
    def __str__(self):
        return f"Calendario de {self.usuario}"
