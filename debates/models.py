"""
Tablas del módulo «debates» (ver docs/diseno.md, apartado 11).
"""

from django.conf import settings
from django.db import models


class Debate(models.Model):
    """
    Una pregunta con dos o más opciones que se debaten en paralelo, cada una en su columna, con argumentos
    a favor y en contra y votos que solo se ven como recuentos. Se abre con una solicitud con apoyos; quien
    la pide tiene la facilitación y lo cierra con una conclusión, que pasa al registro de decisiones.
    """

    PENDIENTE = "pendiente"
    ABIERTO = "abierto"
    CERRADO = "cerrado"
    ESTADOS = [(PENDIENTE, "Esperando apoyos"), (ABIERTO, "Abierto"), (CERRADO, "Cerrado")]

    pregunta = models.CharField("pregunta", max_length=300, help_text="Lo que se debate: «¿Dónde hacemos el huerto?».")
    descripcion = models.TextField("contexto", blank=True, help_text="Lo que hay que saber para debatir (en Markdown).")
    grupo = models.ForeignKey("grupos.Grupo", on_delete=models.CASCADE, related_name="+", verbose_name="grupo", help_text="Grupo que debate.")
    audiencia = models.ForeignKey(
        "audiencias.Audiencia", on_delete=models.PROTECT, related_name="+", verbose_name="quién participa",
        help_text="Quién lo ve y participa. Ampliarlo a otros grupos es cambiar esto.",
    )
    visibilidad = models.CharField("visibilidad elegida", max_length=30, default="grupo:0", help_text="La opción elegida («grupo:0»…).")
    ancla_tipo = models.CharField("cuelga de (tipo)", max_length=60, blank=True, help_text="Si cuelga de algo, su tipo: «eventos.evento»…")
    ancla_id = models.PositiveBigIntegerField("cuelga de (número)", null=True, blank=True, help_text="Si cuelga de algo, su número.")
    creador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="lo propuso", help_text="Quién lo propuso."
    )
    estado = models.CharField("estado", max_length=10, choices=ESTADOS, default=PENDIENTE, help_text="Esperando apoyos, abierto o cerrado.")
    cierra = models.DateTimeField("se cierra", null=True, blank=True, help_text="Cuándo termina (opcional, salvo que la organización lo pida).")
    creado = models.DateTimeField("propuesto", auto_now_add=True, help_text="Cuándo se propuso.")
    cerrado_el = models.DateTimeField("cerrado el", null=True, blank=True, help_text="Cuándo se cerró.")
    elegida = models.ForeignKey(
        "Opcion", on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="opción elegida",
        help_text="La opción con la que se cerró, si se eligió una.",
    )
    intervenciones_desde = models.DateTimeField(
        "intervenciones contadas desde", null=True, blank=True,
        help_text="Cuándo se confirmó la última opción de consenso: desde entonces se vuelven a contar las intervenciones de todo el mundo.",
    )
    conclusion = models.TextField("conclusión", blank=True, help_text="Lo que se decidió al cerrarlo; pasa al registro de decisiones.")

    class Meta:
        verbose_name = "debate"
        verbose_name_plural = "debates"
        ordering = ["-creado", "-pk"]
        indexes = [models.Index(fields=["ancla_tipo", "ancla_id"], name="debate_por_ancla")]

    # Texto con el que se muestra: la pregunta.
    def __str__(self):
        return self.pregunta


class Opcion(models.Model):
    """
    Una respuesta posible a la pregunta del debate, con su columna de argumentos. Las de después de abrirse
    nacen «propuestas» y se abren cuando las apoyan N personas.
    """

    PROPUESTA = "propuesta"
    ABIERTA = "abierta"
    ESTADOS = [(PROPUESTA, "Propuesta (esperando apoyos)"), (ABIERTA, "Abierta")]

    debate = models.ForeignKey(Debate, on_delete=models.CASCADE, related_name="opciones", verbose_name="debate", help_text="El debate.")
    texto = models.CharField("opción", max_length=300, help_text="La respuesta que se propone.")
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="la propuso", help_text="Quién la propuso."
    )
    de_consenso = models.BooleanField("de consenso", default=False, help_text="Si se propone como síntesis de varias opciones: se confirma con apoyos de personas que habían apoyado opciones distintas, y reinicia las intervenciones.")
    de_partida = models.BooleanField("de partida", default=False, help_text="Si venía con el debate (no cuenta para el límite de opciones nuevas).")
    estado = models.CharField("estado", max_length=10, choices=ESTADOS, default=ABIERTA, help_text="Propuesta (esperando apoyos) o abierta.")
    creada = models.DateTimeField("propuesta el", auto_now_add=True, help_text="Cuándo se propuso.")

    class Meta:
        verbose_name = "opción"
        verbose_name_plural = "opciones"
        ordering = ["creada", "pk"]

    # Texto con el que se muestra: la opción.
    def __str__(self):
        return self.texto


class Argumento(models.Model):
    """
    Lo que alguien escribe a favor o en contra de una opción, o en respuesta a otro argumento. Lleva siempre
    el alias de quien lo escribe.
    """

    opcion = models.ForeignKey(Opcion, on_delete=models.CASCADE, related_name="argumentos", verbose_name="opción", help_text="La opción de la que trata.")
    padre = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="respuestas", verbose_name="responde a",
        help_text="El argumento al que responde, si es una respuesta.",
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="lo escribió", help_text="Quién lo escribió."
    )
    texto = models.TextField("argumento", help_text="Lo que se argumenta.")
    a_favor = models.BooleanField("a favor", default=True, help_text="Si es a favor de la opción (si no, en contra).")
    pasado = models.BooleanField(
        "pasado del límite", default=False, help_text="Si se escribió pasado el límite blando (sale muy marcado)."
    )
    creado = models.DateTimeField("escrito", auto_now_add=True, help_text="Cuándo se escribió.")

    class Meta:
        verbose_name = "argumento"
        verbose_name_plural = "argumentos"
        ordering = ["creado", "pk"]

    # Texto con el que se muestra: el principio del argumento.
    def __str__(self):
        return self.texto[:60]


class Voto(models.Model):
    """
    Lo que una persona opina de una opción, de un argumento o del debate entero («todas me valen»). Un voto
    por persona y elemento; se muestran solo como recuentos, y las justificaciones de ⭐ y ⛔ sin nombre.
    """

    MUY_IMPORTANTE = "estrella"
    APOYO = "apoyo"
    CONTRA = "contra"
    OPOSICION = "oposicion"
    REPETITIVO = "repetitivo"
    NO_TIENE_QUE_VER = "fuera"
    TODAS_ME_VALEN = "todas"
    TIPOS = [
        (MUY_IMPORTANTE, "⭐ Muy importante"), (APOYO, "👍 Apoyo"), (CONTRA, "👎 En contra"), (OPOSICION, "⛔ Oposición total"),
        (REPETITIVO, "🔁 Repetitivo"), (NO_TIENE_QUE_VER, "🚫 No tiene que ver"), (TODAS_ME_VALEN, "🤝 Todas me valen"),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+", verbose_name="quién", help_text="Quién vota.")
    debate = models.ForeignKey(Debate, on_delete=models.CASCADE, related_name="votos", verbose_name="debate", help_text="El debate.")
    opcion = models.ForeignKey(Opcion, on_delete=models.CASCADE, null=True, blank=True, related_name="votos", verbose_name="opción", help_text="La opción, si se vota una.")
    argumento = models.ForeignKey(
        Argumento, on_delete=models.CASCADE, null=True, blank=True, related_name="votos", verbose_name="argumento", help_text="El argumento, si se vota uno."
    )
    tipo = models.CharField("voto", max_length=12, choices=TIPOS, help_text="Qué opina.")
    justificacion = models.CharField("justificación", max_length=300, blank=True, help_text="Breve, para ⭐ y ⛔. Se muestra sin nombre.")
    creado = models.DateTimeField("votado", auto_now=True, help_text="Cuándo votó (o cambió el voto).")

    class Meta:
        verbose_name = "voto"
        verbose_name_plural = "votos"
        constraints = [
            # Un voto por persona y elemento (los vacíos cuentan como iguales: uno solo para el debate entero).
            models.UniqueConstraint(fields=["usuario", "debate", "opcion", "argumento"], name="un_voto_por_elemento", nulls_distinct=False),
        ]

    # Texto con el que se muestra: el tipo de voto.
    def __str__(self):
        return self.get_tipo_display()


class LimitesDeDebate(models.Model):
    """
    Límites para que un debate no se desborde (docs/diseno.md, apartado 11): al pasar el blando se permite
    una intervención más, muy marcada; al llegar al duro, ya no se puede. Van en cascada: los de la
    plataforma (los pone el superadmin) y los de cada organización, que solo pueden ser más estrictos. Vacío:
    sin límite en ese nivel.
    """

    organizacion = models.OneToOneField(
        "grupos.Organizacion", on_delete=models.CASCADE, null=True, blank=True, related_name="limites_de_debate",
        verbose_name="organización", help_text="Vacío: los de toda la plataforma.",
    )
    palabras_blando = models.PositiveIntegerField("palabras por intervención (blando)", null=True, blank=True, help_text="Pasado esto, la intervención sale marcada.")
    palabras_duro = models.PositiveIntegerField("palabras por intervención (duro)", null=True, blank=True, help_text="Pasado esto, no se publica.")
    intervenciones_blando = models.PositiveIntegerField(
        "intervenciones por persona (blando)", null=True, blank=True, help_text="Argumentos de una persona en un debate; al llegar, uno más y marcado."
    )
    intervenciones_duro = models.PositiveIntegerField("intervenciones por persona (duro)", null=True, blank=True, help_text="Al llegar, ya no puede escribir más.")
    opciones_por_persona = models.PositiveIntegerField("opciones nuevas por persona", null=True, blank=True, help_text="Cuántas opciones puede proponer cada persona.")
    apoyos_para_opcion = models.PositiveIntegerField("apoyos para abrir una opción", null=True, blank=True, help_text="Cuántas personas deben apoyar una opción nueva.")
    fin_obligatorio = models.BooleanField("fecha de fin obligatoria", default=False, help_text="Si cada debate debe decir cuándo se cierra.")

    class Meta:
        verbose_name = "límites de los debates"
        verbose_name_plural = "límites de los debates"

    # Texto con el que se muestra: de quién son.
    def __str__(self):
        return f"Límites de {self.organizacion or 'la plataforma'}"
