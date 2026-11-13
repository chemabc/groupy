"""
Tablas del módulo «eventos» (ver docs/diseno.md, apartado 10): actividades con fecha (reuniones,
acciones, recaudatorios…) que convoca un grupo.

- Evento: los datos comunes (grupo, tipología, quién lo ve, modalidad y lugar, fecha y duración, coste,
  cartel y texto para las redes) y los campos propios de su tipología (en JSON).
- Asistencia: la respuesta de cada persona a «¿Vas a ir?». Todos los que ven el evento ven cuántas
  personas van; los alias, solo quien convoca y quien tiene un cometido en el evento.

Los cometidos (facilitación, logística…) se guardan en el módulo «permisos», anclados al evento.
"""

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


# Comprueba que una imagen subida no pasa del tamaño máximo (settings.TAMANO_MAXIMO_DE_IMAGEN).
def validar_tamano(fichero):
    if fichero and fichero.size > settings.TAMANO_MAXIMO_DE_IMAGEN:
        raise ValidationError(f"La imagen pesa demasiado: como mucho {settings.TAMANO_MAXIMO_DE_IMAGEN // (1024 * 1024)} MB.")


class Evento(models.Model):
    """
    Actividad con fecha que convoca un grupo. Su tipología (Reunión, Acción, Recaudatorio, Genérico o un
    subtipo) añade campos propios. Una reunión necesita una solicitud con apoyos: mientras no los tiene,
    queda «pendiente de apoyos» y solo la ve quien la convoca.
    """

    PENDIENTE = "pendiente"
    CONVOCADO = "convocado"
    CANCELADO = "cancelado"
    ESTADOS = [(PENDIENTE, "Pendiente de apoyos"), (CONVOCADO, "Convocado"), (CANCELADO, "Cancelado")]

    PRESENCIAL = "presencial"
    EN_LINEA = "en_linea"
    MODALIDADES = [(PRESENCIAL, "Presencial"), (EN_LINEA, "En línea")]

    GRATIS = "gratis"
    DONACIONES = "donaciones"
    ENTRADA = "entrada"
    COSTES = [(GRATIS, "Gratis"), (DONACIONES, "Con donaciones"), (ENTRADA, "Con entrada")]

    grupo = models.ForeignKey("grupos.Grupo", on_delete=models.CASCADE, related_name="+", verbose_name="grupo que convoca", help_text="Grupo que lo convoca.")
    convocante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="convoca", help_text="Quién lo convoca."
    )
    tipologia = models.ForeignKey(
        "tipologias.Tipologia", on_delete=models.PROTECT, related_name="+", verbose_name="tipo", help_text="Reunión, Acción, Recaudatorio, Genérico… (con sus campos)."
    )
    titulo = models.CharField("título", max_length=150, help_text="Cómo se llama: «Asamblea de noviembre», «Concentración por la sanidad».")
    descripcion = models.TextField("descripción", blank=True, help_text="De qué va, qué se hará, qué hay que saber.")
    audiencia = models.ForeignKey(
        "audiencias.Audiencia", on_delete=models.PROTECT, related_name="+", verbose_name="quién lo ve",
        help_text="Quién puede verlo (privado, el grupo, la organización…).",
    )
    visibilidad = models.CharField(
        "visibilidad elegida", max_length=30, default="privado",
        help_text="La opción de visibilidad que se eligió («grupo:1»…). Para una reunión pendiente, la que tendrá al convocarse.",
    )
    modalidad = models.CharField("modalidad", max_length=20, choices=MODALIDADES, default=PRESENCIAL, help_text="Presencial o en línea.")
    lugar = models.ForeignKey(
        "lugares.Lugar", on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="lugar de la lista",
        help_text="Si es en uno de los lugares de la lista. Opcional.",
    )
    direccion = models.CharField("dirección", max_length=250, blank=True, help_text="Dónde, si es presencial (o detalles: «aula 3»).")
    url = models.URLField("enlace", max_length=500, blank=True, help_text="Si es en línea, el enlace a la videollamada.")
    inicio = models.DateTimeField("empieza", help_text="Día y hora.")
    duracion = models.PositiveIntegerField("duración (minutos)", default=90, help_text="Cuánto dura, en minutos.")
    coste = models.CharField("coste", max_length=20, choices=COSTES, default=GRATIS, help_text="Gratis, con donaciones o con entrada.")
    coste_detalle = models.CharField("detalle del coste", max_length=200, blank=True, help_text="Precio, a quién va el dinero… Opcional.")
    cartel = models.ImageField(
        "cartel", upload_to="eventos/carteles/%Y/%m/", blank=True, validators=[validar_tamano],
        help_text="Imagen (JPG, PNG o WebP), hasta 5 MB. Solo la ve quien puede ver el evento.",
    )
    texto_para_redes = models.TextField(
        "texto para las redes", blank=True, help_text="Lo que se publicará al compartirlo (Telegram, WhatsApp, Mastodon…). Hay botón para copiarlo."
    )
    campos = models.JSONField("campos de su tipo", default=dict, blank=True, help_text="Los datos que pide su tipología (por ejemplo, «qué llevar»).")
    estado = models.CharField("estado", max_length=20, choices=ESTADOS, default=CONVOCADO, help_text="Pendiente de apoyos (reuniones), convocado o cancelado.")
    creado = models.DateTimeField("creado", auto_now_add=True, help_text="Cuándo se creó.")

    class Meta:
        verbose_name = "evento"
        verbose_name_plural = "eventos"
        ordering = ["inicio", "pk"]
        indexes = [models.Index(fields=["inicio"], name="evento_por_fecha")]

    # Texto con el que se muestra: su título.
    def __str__(self):
        return self.titulo

    # Cuándo termina (inicio más la duración).
    @property
    def fin(self):
        return self.inicio + timedelta(minutes=self.duracion)


class Asistencia(models.Model):
    """Respuesta de una persona a «¿Vas a ir?»: sí, no o aún no lo sabe."""

    SI = "si"
    NO = "no"
    NO_SE = "no_se"
    RESPUESTAS = [(SI, "Sí"), (NO, "No"), (NO_SE, "Aún no lo sé")]

    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="asistencias", verbose_name="evento", help_text="El evento.")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+", verbose_name="usuario", help_text="Quién responde.")
    respuesta = models.CharField("respuesta", max_length=10, choices=RESPUESTAS, help_text="Si va a ir.")
    actualizada = models.DateTimeField("respondida", auto_now=True, help_text="Cuándo respondió (o cambió la respuesta).")

    class Meta:
        verbose_name = "asistencia"
        verbose_name_plural = "asistencias"
        constraints = [models.UniqueConstraint(fields=["evento", "usuario"], name="una_asistencia_por_persona")]

    # Texto con el que se muestra: «Nutria: Sí».
    def __str__(self):
        return f"{self.usuario}: {self.get_respuesta_display()}"
