"""
Tablas del módulo «comunicaciones» (ver docs/diseno.md, apartado 17):

- Notificacion: un aviso a una persona («Han invitado a GRU Segre…»), que aparece en su bandeja de
  «Comunicaciones → Notificaciones». Lo crea el repartidor (comunicaciones/servicios.py) a partir de los
  tipos de aviso que declaran los módulos en su contrato.
- PreferenciaDeAviso: que una persona ha desactivado (o vuelto a activar) un tipo de aviso. Sin fila, el
  aviso está activado.
- NivelDeAviso: cuánta atención pide un aviso de la administración (Información, Atención, Problema…),
  con su color. Los edita el superadmin.
- AvisoDeAdministracion: un aviso que manda una administración (la de un grupo, la de una organización
  o el superadmin) a grupos o personas. Crea una notificación para cada destinatario.
"""

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

from base.contrato import ORIGENES_DE_AVISO


class NivelDeAviso(models.Model):
    """
    Nivel de un aviso de la administración: cuánta atención pide («Información», «Atención»,
    «Problema»…). Se ve con su color en la bandeja. Los crea y edita el superadmin en «Plataforma →
    Catálogos comunes → Niveles de aviso».
    """

    nombre = models.CharField("nombre", max_length=40, unique=True, help_text="Como se verá: «Atención».")
    descripcion = models.CharField(
        "descripción", max_length=200, blank=True, help_text="Cuándo usarlo, en una frase: «Hay que hacer algo pronto»."
    )
    color = models.CharField(
        "color", max_length=7, default="#2563eb",
        validators=[RegexValidator(r"^#[0-9a-fA-F]{6}$", "Un color como «#d97706» (almohadilla y seis cifras hexadecimales).")],
        help_text="Color con el que se pinta el aviso, como «#d97706».",
    )
    orden = models.PositiveSmallIntegerField("orden", default=10, help_text="Posición en los desplegables: los números bajos salen antes.")

    class Meta:
        verbose_name = "nivel de aviso"
        verbose_name_plural = "niveles de aviso"
        ordering = ["orden", "nombre"]

    # Texto con el que se muestra: su nombre.
    def __str__(self):
        return self.nombre


class Administracion(models.Model):
    """
    Campos comunes de lo que pertenece a una administración: la de un grupo (sus admins), la de una
    organización (sus admins) o la de la plataforma (el superadmin). Se escribe a la administración,
    nunca al alias privado de un admin. Es abstracta: no crea tabla propia.
    """

    grupo = models.ForeignKey(
        "grupos.Grupo", on_delete=models.CASCADE, null=True, blank=True, related_name="+", verbose_name="grupo",
        help_text="Si es la administración de un grupo, cuál.",
    )
    organizacion = models.ForeignKey(
        "grupos.Organizacion", on_delete=models.CASCADE, null=True, blank=True, related_name="+",
        verbose_name="organización", help_text="Si es la administración de una organización, cuál. Vacíos los dos: el superadmin.",
    )

    class Meta:
        abstract = True

    # Nombre de la administración: «Admin de GRU Henares», «Admin de ORG Tajo» o «Superadmin». Necesita
    # el grupo o la organización ya cargados (select_related) para no hacer consultas.
    @property
    def nombre_de_la_administracion(self):
        if self.grupo_id:
            return f"Admin de {self.grupo.nombre}"
        if self.organizacion_id:
            return f"Admin de {self.organizacion.nombre}"
        return "Superadmin"


class AvisoDeAdministracion(Administracion):
    """
    Aviso que manda una administración a grupos (con sus subgrupos) o a personas: información, algo que
    atender, un problema… Cada destinatario recibe una notificación en su bandeja, con el color del nivel.
    Si se permite responder, la notificación lleva un enlace para abrir una conversación con esa
    administración.
    """

    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="autor",
        help_text="El admin que lo escribió (firma entre paréntesis).",
    )
    nivel = models.ForeignKey(NivelDeAviso, on_delete=models.PROTECT, related_name="avisos", verbose_name="nivel", help_text="Cuánta atención pide.")
    asunto = models.CharField("asunto", max_length=120, help_text="De qué va, en pocas palabras.")
    texto = models.TextField("texto", help_text="El aviso.")
    permite_responder = models.BooleanField(
        "se puede responder", default=False, help_text="Si quien lo recibe puede abrir una conversación con esta administración desde el aviso."
    )
    destinatarios = models.TextField("destinatarios", help_text="A quién se mandó, en palabras («GRU Jarama y sus subgrupos; Nutria»).")
    numero_de_personas = models.PositiveIntegerField("personas", default=0, help_text="A cuántas personas llegó.")
    creado = models.DateTimeField("enviado", auto_now_add=True, help_text="Cuándo se envió.")

    class Meta:
        verbose_name = "aviso de la administración"
        verbose_name_plural = "avisos de la administración"
        ordering = ["-creado", "-pk"]

    # Texto con el que se muestra: el asunto.
    def __str__(self):
        return self.asunto


class Notificacion(models.Model):
    """
    Notificación: un aviso para una persona. Se ve en su bandeja hasta que la borra. Las vistas se pueden
    limpiar todas de una vez; el módulo «limpieza» borra las vistas a los 90 días y las no
    vistas a los 365 (el superadmin puede cambiarlo; ver comunicaciones/limpieza.py).
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
    aviso = models.ForeignKey(
        AvisoDeAdministracion, on_delete=models.CASCADE, null=True, blank=True, related_name="notificaciones",
        verbose_name="aviso de la administración", help_text="Si la notificación es un aviso de una administración, cuál (con su nivel y color).",
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


class Conversacion(Administracion):
    """
    Conversación de una persona con una administración (la de un grupo, la de una organización o el
    superadmin), por un tema administrativo de la plataforma. La atienden todos los admins de esa
    administración, como un buzón compartido, y la pueden leer los admins de la organización y el
    superadmin; nunca se escribe al alias privado de un admin. Tiene un estado para seguir los temas.
    Más adelante, el chat de grupos y proyectos usará también conversaciones.
    """

    ABIERTA = "abierta"
    EN_PROCESO = "en_proceso"
    SOLUCIONADA = "solucionada"
    ESTADOS = [(ABIERTA, "Abierta"), (EN_PROCESO, "En proceso"), (SOLUCIONADA, "Solucionada")]

    persona = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversaciones",
        verbose_name="persona", help_text="Quien escribe a la administración (o a quien la administración respondió un aviso).",
    )
    asunto = models.CharField("asunto", max_length=120, help_text="De qué trata, en pocas palabras.")
    estado = models.CharField(
        "estado", max_length=20, choices=ESTADOS, default=ABIERTA,
        help_text="Abierta (sin atender), en proceso (alguien se está ocupando) o solucionada. Lo cambian los admins.",
    )
    aviso = models.ForeignKey(
        AvisoDeAdministracion, on_delete=models.SET_NULL, null=True, blank=True, related_name="conversaciones",
        verbose_name="aviso", help_text="Si nació como respuesta a un aviso de la administración, cuál.",
    )
    creada = models.DateTimeField("creada", auto_now_add=True, help_text="Cuándo empezó.")
    actualizada = models.DateTimeField("último mensaje", auto_now_add=True, help_text="Cuándo se escribió el último mensaje.")
    pendiente_persona = models.BooleanField(
        "con respuesta sin leer", default=False, help_text="Si la administración ha escrito algo que la persona no ha leído."
    )
    pendiente_admins = models.BooleanField(
        "con mensaje sin leer", default=True, help_text="Si la persona ha escrito algo que ningún admin ha leído."
    )

    class Meta:
        verbose_name = "conversación con la administración"
        verbose_name_plural = "conversaciones con la administración"
        ordering = ["-actualizada", "-pk"]

    # Texto con el que se muestra: el asunto.
    def __str__(self):
        return self.asunto


class Mensaje(models.Model):
    """
    Un mensaje de una conversación. Si lo escribe un admin, firma con la administración y su alias entre
    paréntesis («Admin de GRU Henares (Lince)»).
    """

    conversacion = models.ForeignKey(
        Conversacion, on_delete=models.CASCADE, related_name="mensajes", verbose_name="conversación", help_text="Conversación a la que pertenece."
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="autor", help_text="Quién lo escribió."
    )
    de_la_administracion = models.BooleanField(
        "de la administración", default=False, help_text="Si lo escribió un admin en nombre de la administración."
    )
    firma = models.CharField("firma", max_length=200, help_text="Cómo aparece quien lo escribe: su alias o «Admin de GRU Henares (Lince)».")
    texto = models.TextField("texto", help_text="El mensaje.")
    creado = models.DateTimeField("escrito", auto_now_add=True, help_text="Cuándo se escribió.")

    class Meta:
        verbose_name = "mensaje"
        verbose_name_plural = "mensajes"
        ordering = ["creado", "pk"]

    # Texto con el que se muestra: el principio del mensaje.
    def __str__(self):
        return self.texto[:60]
