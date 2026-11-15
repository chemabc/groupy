"""
Tablas del módulo «consultas» (ver docs/diseno.md, apartado 12). El voto es secreto: quién ha votado
(Participacion) y qué ha votado (Papeleta) van en tablas distintas, sin nada que las una.
"""

from django.conf import settings
from django.db import models


class Consulta(models.Model):
    """
    Una votación de un grupo: un formulario con una o varias preguntas, quién vota, cuándo se abre y se
    cierra, y cuándo y quién ve los resultados. Al cerrarse, el resultado pasa al registro de decisiones.
    """

    AL_CERRAR = "cierre"
    EN_UNA_FECHA = "fecha"
    EN_TIEMPO_REAL = "tiempo_real"
    CUANDO = [
        (AL_CERRAR, "Al cerrar"),
        (EN_UNA_FECHA, "En una fecha después del cierre"),
        (EN_TIEMPO_REAL, "En tiempo real (influye en quien aún no ha votado)"),
    ]

    titulo = models.CharField("título", max_length=200, help_text="Qué se consulta: «Presupuesto de 2027».")
    descripcion = models.TextField("explicación", blank=True, help_text="Lo que hay que saber para votar (Markdown).")
    grupo = models.ForeignKey("grupos.Grupo", on_delete=models.CASCADE, related_name="+", verbose_name="grupo", help_text="Grupo que consulta.")
    audiencia = models.ForeignKey(
        "audiencias.Audiencia", on_delete=models.PROTECT, related_name="+", verbose_name="quién vota", help_text="Quién puede votar (y la ve)."
    )
    visibilidad = models.CharField("quién vota (elegido)", max_length=30, default="grupo:0", help_text="La opción elegida para quién vota.")
    audiencia_resultados = models.ForeignKey(
        "audiencias.Audiencia", on_delete=models.PROTECT, related_name="+", verbose_name="quién ve los resultados",
        help_text="Quién ve los resultados, con los niveles de visibilidad de siempre.",
    )
    visibilidad_resultados = models.CharField("quién ve los resultados (elegido)", max_length=30, default="grupo:0", help_text="La opción elegida.")
    ancla_tipo = models.CharField("cuelga de (tipo)", max_length=60, blank=True, help_text="Si cuelga de algo, su tipo.")
    ancla_id = models.PositiveBigIntegerField("cuelga de (número)", null=True, blank=True, help_text="Si cuelga de algo, su número.")
    creador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="la creó", help_text="Quién la creó."
    )
    abre = models.DateTimeField("se abre", help_text="Desde cuándo se puede votar. Antes, se preparan las preguntas.")
    cierra = models.DateTimeField("se cierra", help_text="Hasta cuándo se puede votar.")
    resultados = models.CharField("resultados", max_length=12, choices=CUANDO, default=AL_CERRAR, help_text="Cuándo se ven los resultados.")
    publicar_el = models.DateTimeField("se publican el", null=True, blank=True, help_text="Si se ven en una fecha: cuál (después del cierre).")
    cambiar_voto = models.BooleanField(
        "se puede cambiar el voto", default=False, help_text="Si se puede cambiar antes del cierre. Si no, se avisa antes de votar."
    )
    creada = models.DateTimeField("creada", auto_now_add=True, help_text="Cuándo se creó.")
    cerrada_el = models.DateTimeField("cerrada el", null=True, blank=True, help_text="Cuándo se dio por cerrada (y pasó a decisiones).")

    class Meta:
        verbose_name = "consulta"
        verbose_name_plural = "consultas"
        ordering = ["-cierra", "-pk"]
        indexes = [models.Index(fields=["ancla_tipo", "ancla_id"], name="consulta_por_ancla")]

    # Texto con el que se muestra: el título.
    def __str__(self):
        return self.titulo


class Pregunta(models.Model):
    """Una pregunta del formulario de una consulta: de respuesta única, múltiple o abierta."""

    UNICA = "unica"
    MULTIPLE = "multiple"
    ABIERTA = "abierta"
    TIPOS = [(UNICA, "Respuesta única"), (MULTIPLE, "Respuesta múltiple"), (ABIERTA, "Respuesta abierta (texto)")]

    consulta = models.ForeignKey(Consulta, on_delete=models.CASCADE, related_name="preguntas", verbose_name="consulta", help_text="La consulta.")
    texto = models.CharField("pregunta", max_length=300, help_text="Lo que se pregunta.")
    tipo = models.CharField("tipo", max_length=10, choices=TIPOS, default=UNICA, help_text="Cómo se responde.")
    documentacion = models.TextField("documentación", blank=True, help_text="Información para responder (Markdown, con enlaces a documentos).")
    orden = models.PositiveSmallIntegerField("orden", default=0, help_text="Posición en el formulario.")

    class Meta:
        verbose_name = "pregunta"
        verbose_name_plural = "preguntas"
        ordering = ["orden", "pk"]

    # Texto con el que se muestra: la pregunta.
    def __str__(self):
        return self.texto


class Respuesta(models.Model):
    """Una respuesta posible de una pregunta de respuesta única o múltiple."""

    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name="respuestas", verbose_name="pregunta", help_text="La pregunta.")
    texto = models.CharField("respuesta", max_length=200, help_text="La respuesta que se puede elegir.")
    orden = models.PositiveSmallIntegerField("orden", default=0, help_text="Posición en la lista.")

    class Meta:
        verbose_name = "respuesta posible"
        verbose_name_plural = "respuestas posibles"
        ordering = ["orden", "pk"]

    # Texto con el que se muestra: la respuesta.
    def __str__(self):
        return self.texto


class Participacion(models.Model):
    """
    Que una persona ha votado en una consulta (para que nadie vote dos veces). No dice qué votó: eso va en
    una papeleta sin nombre.
    """

    consulta = models.ForeignKey(Consulta, on_delete=models.CASCADE, related_name="participaciones", verbose_name="consulta", help_text="La consulta.")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+", verbose_name="quién", help_text="Quién ha votado.")

    class Meta:
        verbose_name = "participación"
        verbose_name_plural = "participaciones"
        constraints = [models.UniqueConstraint(fields=["consulta", "usuario"], name="un_voto_por_persona")]

    # Texto con el que se muestra.
    def __str__(self):
        return f"{self.usuario} ha votado"


class Papeleta(models.Model):
    """
    Lo que se ha votado, sin nombre. Si la consulta deja cambiar el voto, lleva una clave que solo se puede
    calcular con un secreto del servidor (ver consultas/servicios.py, clave_de_papeleta); si no, una al azar.
    """

    consulta = models.ForeignKey(Consulta, on_delete=models.CASCADE, related_name="papeletas", verbose_name="consulta", help_text="La consulta.")
    clave = models.CharField("clave", max_length=64, unique=True, help_text="Seudónimo de la papeleta: no dice de quién es.")
    grupo = models.ForeignKey(
        "grupos.Grupo", on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="asamblea base",
        help_text="La asamblea base de quien votó, para el desglose por grupos (solo se enseña con 10 votos o más).",
    )
    respuestas = models.JSONField("respuestas", default=dict, help_text="Por pregunta: los números de las respuestas elegidas, o el texto.")

    class Meta:
        verbose_name = "papeleta"
        verbose_name_plural = "papeletas"

    # Texto con el que se muestra (sin nada de quién votó).
    def __str__(self):
        return f"Papeleta de {self.consulta}"
