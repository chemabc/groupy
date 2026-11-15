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
- Conversacion y Mensaje: conversaciones de una persona con una administración.
- MensajeDeGrupo y LecturaDeSala: la sala de cada grupo (su conversación, un solo hilo) y hasta dónde ha
  leído cada persona.
- ConversacionEntrePersonas, MensajeEntrePersonas y Bloqueo: conversaciones de dos en dos, con bloqueo.
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


# ── Conversaciones con grupos y con personas (15 de noviembre de 2026, [A-56]) ─────────────────────────


class MensajeDeGrupo(models.Model):
    """
    Un mensaje en la sala de un grupo: la conversación de todo el grupo, un solo hilo donde escriben sus
    miembros (como el chat del grupo). Solo leen y escriben las personas que están en el grupo; nadie de
    fuera, tampoco el superadmin si no es miembro. Se ve en «Comunicaciones → Conversaciones → Con grupos».
    """

    grupo = models.ForeignKey(
        "grupos.Grupo", on_delete=models.CASCADE, related_name="+", verbose_name="grupo", help_text="Grupo en cuya sala se escribió."
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="autor", help_text="Quién lo escribió."
    )
    firma = models.CharField("firma", max_length=150, help_text="El alias de quien lo escribió, tal como se ve en la sala.")
    texto = models.TextField("texto", help_text="El mensaje.")
    creado = models.DateTimeField("escrito", auto_now_add=True, help_text="Cuándo se escribió.")

    class Meta:
        verbose_name = "mensaje de grupo"
        verbose_name_plural = "mensajes de grupo"
        ordering = ["pk"]
        indexes = [models.Index(fields=["grupo", "-id"], name="mensaje_de_grupo_por_sala")]

    # Texto con el que se muestra: el principio del mensaje.
    def __str__(self):
        return self.texto[:60]


class LecturaDeSala(models.Model):
    """
    Hasta qué mensaje ha leído una persona la sala de un grupo. Sirve para marcar las salas con mensajes
    nuevos y para el número del menú («Con grupos (2)»). Sin fila: no ha leído nada.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+", verbose_name="usuario", help_text="Quién ha leído."
    )
    grupo = models.ForeignKey("grupos.Grupo", on_delete=models.CASCADE, related_name="+", verbose_name="grupo", help_text="La sala de qué grupo.")
    ultimo_leido = models.PositiveBigIntegerField(
        "último mensaje leído", default=0, help_text="Número del último mensaje de la sala que ha visto esta persona."
    )

    class Meta:
        verbose_name = "lectura de sala"
        verbose_name_plural = "lecturas de sala"
        constraints = [models.UniqueConstraint(fields=["usuario", "grupo"], name="una_lectura_por_sala")]

    # Texto con el que se muestra: «Nutria en GRU Henares: 12».
    def __str__(self):
        return f"{self.usuario} en {self.grupo}: {self.ultimo_leido}"


class ConversacionEntrePersonas(models.Model):
    """
    Conversación de dos personas, por su alias. Se empieza con quien compartes algún grupo; cualquiera de
    las dos puede bloquear a la otra (y el superadmin recibe un aviso). Solo la leen esas dos personas: ni
    la administración ni el superadmin (ver docs/diseno.md, apartado 5.1). La pareja se guarda siempre con
    el número más bajo primero, para que haya una sola conversación por pareja.
    """

    primera = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+", verbose_name="primera persona",
        help_text="La de número más bajo de las dos.",
    )
    segunda = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+", verbose_name="segunda persona",
        help_text="La de número más alto de las dos.",
    )
    iniciada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="iniciada por",
        help_text="Quién escribió el primer mensaje.",
    )
    creada = models.DateTimeField("creada", auto_now_add=True, help_text="Cuándo empezó.")
    actualizada = models.DateTimeField("último mensaje", auto_now_add=True, help_text="Cuándo se escribió el último mensaje.")
    pendiente_primera = models.BooleanField("sin leer (primera)", default=False, help_text="Si la primera persona tiene algo sin leer.")
    pendiente_segunda = models.BooleanField("sin leer (segunda)", default=False, help_text="Si la segunda persona tiene algo sin leer.")

    class Meta:
        verbose_name = "conversación entre personas"
        verbose_name_plural = "conversaciones entre personas"
        ordering = ["-actualizada", "-pk"]
        constraints = [
            models.UniqueConstraint(fields=["primera", "segunda"], name="una_conversacion_por_pareja"),
            models.CheckConstraint(condition=models.Q(primera__lt=models.F("segunda")), name="pareja_en_orden"),
        ]

    # Texto con el que se muestra: «Lince ↔ Nutria».
    def __str__(self):
        return f"{self.primera} ↔ {self.segunda}"

    # La otra persona de la conversación, vista desde una de las dos (con las dos cargadas).
    #   - usuario: una de las dos.
    def la_otra(self, usuario):
        return self.segunda if self.primera_id == usuario.pk else self.primera

    # Si una de las dos personas tiene algo sin leer.
    #   - usuario: una de las dos.
    def pendiente_para(self, usuario):
        return self.pendiente_primera if self.primera_id == usuario.pk else self.pendiente_segunda


class MensajeEntrePersonas(models.Model):
    """Un mensaje de una conversación entre dos personas."""

    conversacion = models.ForeignKey(
        ConversacionEntrePersonas, on_delete=models.CASCADE, related_name="mensajes", verbose_name="conversación",
        help_text="Conversación a la que pertenece.",
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="autor", help_text="Quién lo escribió."
    )
    texto = models.TextField("texto", help_text="El mensaje.")
    creado = models.DateTimeField("escrito", auto_now_add=True, help_text="Cuándo se escribió.")

    class Meta:
        verbose_name = "mensaje entre personas"
        verbose_name_plural = "mensajes entre personas"
        ordering = ["pk"]

    # Texto con el que se muestra: el principio del mensaje.
    def __str__(self):
        return self.texto[:60]


class Bloqueo(models.Model):
    """
    Una persona ha bloqueado a otra: ninguna de las dos puede escribir a la otra (ni empezar una
    conversación) hasta que quien bloqueó lo quite. Al bloquear, el superadmin recibe un aviso, para poder
    actuar si hay acoso (sin leer la conversación).
    """

    quien = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bloqueos", verbose_name="quien bloquea",
        help_text="La persona que ha bloqueado.",
    )
    a_quien = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+", verbose_name="persona bloqueada",
        help_text="La persona que ya no puede escribirle.",
    )
    creado = models.DateTimeField("bloqueado el", auto_now_add=True, help_text="Cuándo se bloqueó.")

    class Meta:
        verbose_name = "bloqueo"
        verbose_name_plural = "bloqueos"
        constraints = [models.UniqueConstraint(fields=["quien", "a_quien"], name="un_bloqueo_por_pareja")]

    # Texto con el que se muestra: «Nutria bloquea a Lince».
    def __str__(self):
        return f"{self.quien} bloquea a {self.a_quien}"
