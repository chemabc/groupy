"""
Tablas de la bóveda: la identidad real de las personas (ver docs/registro-y-validacion.md).

Van en su propia base de datos («boveda»), sin ninguna columna que las una con la plataforma: ninguna
tabla de aquí sabe qué alias tiene cada persona. Se guardan solo fechas (nunca horas), identificadores
al azar y, en lugar del correo oficial una vez validado, su huella (un código del que no se puede volver
al correo).

Estas tablas no están en la trastienda: su historial guardaría la hora exacta de cada cambio en la base
de la plataforma (apartado 8 del documento de registro).
"""

import uuid

from django.db import models
from django.utils import timezone


class Persona(models.Model):
    """
    Persona: la identidad real de alguien que usa la plataforma. En las listas se muestra como
    «Persona 3f2a9c1e» (el principio de su identificador al azar); el nombre, solo dentro de su ficha.
    """

    # Estados de la validación.
    PENDIENTE = "pendiente"
    VALIDADA = "validada"
    ESTADOS = [(PENDIENTE, "Pendiente de validar"), (VALIDADA, "Validada")]

    # Métodos de validación (apartado 6 del documento de registro). De momento solo se usa «superadmin».
    POR_SUPERADMIN = "superadmin"
    METODOS = [
        ("dominio", "Dominio de correo"),
        ("documentos", "Documentos firmados"),
        ("documentos_y_dominio", "Documentos y dominio"),
        (POR_SUPERADMIN, "Alta por el superadmin"),
        ("colectiva", "Validación colectiva"),
    ]

    id = models.UUIDField(
        "identificador",
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Número al azar, sin relación con nada de la plataforma. Su principio da el «Persona 3f2a9c1e».",
    )
    nombre = models.CharField(
        "nombre real", max_length=150, help_text="Nombre y apellidos reales. Solo se ve dentro de la ficha de la persona."
    )
    correo_oficial = models.EmailField(
        "correo oficial",
        blank=True,
        help_text=(
            "Correo oficial (el de la organización). Solo se guarda mientras la persona está pendiente: al "
            "validarla se borra y queda su huella."
        ),
    )
    huella_del_correo = models.CharField(
        "huella del correo",
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        help_text="Código calculado a partir del correo oficial: dice si ese correo ya está registrado, sin guardarlo.",
    )
    organizacion_id = models.PositiveBigIntegerField(
        "organización",
        null=True,
        blank=True,
        help_text=(
            "Número de la organización de la plataforma en la que se da de alta. Es solo un número: entre la "
            "bóveda y la plataforma no hay claves ajenas."
        ),
    )
    estado = models.CharField("estado", max_length=20, choices=ESTADOS, default=PENDIENTE, help_text="Si ya está validada.")
    metodo = models.CharField(
        "método de validación", max_length=30, choices=METODOS, blank=True, help_text="Cómo se validó su identidad."
    )
    validada_el = models.DateField("validada el día", null=True, blank=True, help_text="Día de la validación (nunca la hora).")
    creada_el = models.DateField("registrada el día", default=timezone.localdate, help_text="Día en que se registró (nunca la hora).")

    class Meta:
        verbose_name = "persona"
        verbose_name_plural = "personas"
        ordering = ["creada_el", "id"]

    # Texto con el que se muestra en las listas: «Persona 3f2a9c1e», nunca el nombre.
    def __str__(self):
        return f"Persona {self.codigo}"

    # Las 8 primeras cifras de su identificador («3f2a9c1e»).
    @property
    def codigo(self):
        return self.id.hex[:8]


class PaseEmitido(models.Model):
    """
    Que una persona ya recibió su pase (el vale de un solo uso para activar un alias) en una ronda. Solo
    se apunta el día, sin el pase. En el alta provisional por el superadmin se marca como «ya emitido» sin
    que exista ningún pase: así, cuando llegue el registro real, no podrá conseguir un segundo alias.
    """

    persona = models.ForeignKey(
        Persona, on_delete=models.CASCADE, related_name="pases", verbose_name="persona", help_text="Quién lo recibió."
    )
    ronda = models.PositiveSmallIntegerField(
        "ronda", default=0, help_text="Ronda de validación (0 la primera; las demás, revalidaciones)."
    )
    emitido_el = models.DateField("emitido el día", default=timezone.localdate, help_text="Día (nunca la hora).")
    provisional = models.BooleanField(
        "marcado en el alta provisional",
        default=False,
        help_text="Si se marcó como emitido en el alta provisional por el superadmin, sin pase de verdad.",
    )

    class Meta:
        verbose_name = "pase emitido"
        verbose_name_plural = "pases emitidos"
        constraints = [models.UniqueConstraint(fields=["persona", "ronda"], name="un_pase_por_persona_y_ronda")]

    # Texto con el que se muestra.
    def __str__(self):
        return f"Pase de {self.persona} (ronda {self.ronda})"


class DominioPermitido(models.Model):
    """
    Dominio de correo admitido para validarse en una organización (por ejemplo, «educa.madrid.org»). En el
    registro real, quien elija esa organización solo podrá usar un correo de sus dominios.
    """

    organizacion_id = models.PositiveBigIntegerField(
        "organización", help_text="Número de la organización de la plataforma (sin clave ajena entre las dos bases)."
    )
    dominio = models.CharField(
        "dominio", max_length=150, help_text="Lo que va detrás de la arroba, en minúsculas: «educa.madrid.org»."
    )

    class Meta:
        verbose_name = "dominio permitido"
        verbose_name_plural = "dominios permitidos"
        ordering = ["organizacion_id", "dominio"]
        constraints = [models.UniqueConstraint(fields=["organizacion_id", "dominio"], name="dominio_unico_por_organizacion")]

    # Texto con el que se muestra: el dominio.
    def __str__(self):
        return self.dominio
