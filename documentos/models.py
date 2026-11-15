"""
Tablas del módulo «documentos»: órdenes del día (ODD), actas y documentos libres, con el registro de
cambios y los comentarios (ver docs/diseno.md, apartado 13).
"""

from django.conf import settings
from django.db import models


class Documento(models.Model):
    """
    Un texto con formato (Markdown) que escriben quienes tienen el cometido de redacción: el orden del día
    de una reunión, su acta o un documento libre. Puede colgar de otra cosa (una reunión, un proyecto) y
    entonces toma su grupo y quién lo ve. Detrás de cada párrafo se guarda quién ha contribuido a él.
    """

    ODD = "odd"
    ACTA = "acta"
    LIBRE = "libre"
    TIPOS = [(ODD, "Orden del día"), (ACTA, "Acta"), (LIBRE, "Documento")]
    BORRADOR = "borrador"
    APROBADO = "aprobado"
    ESTADOS = [(BORRADOR, "Borrador"), (APROBADO, "Aprobado")]
    MARKDOWN = "markdown"
    TYPST = "typst"
    FORMATOS = [(MARKDOWN, "Markdown (sencillo, recomendado)"), (TYPST, "Typst (para maquetar a mano)")]

    tipo = models.CharField("tipo", max_length=10, choices=TIPOS, default=LIBRE, help_text="Orden del día, acta o documento libre.")
    titulo = models.CharField("título", max_length=200, help_text="Cómo se llama: «Acta de la asamblea del 14 de noviembre».")
    texto = models.TextField("texto", blank=True, help_text="El documento, en Markdown (# títulos, - listas, **negrita**…) o en Typst.")
    formato = models.CharField(
        "formato", max_length=10, choices=FORMATOS, default=MARKDOWN,
        help_text="En qué se escribe: Markdown (sencillo) o Typst (más potente para maquetar). El PDF sale siempre con Typst.",
    )
    grupo = models.ForeignKey("grupos.Grupo", on_delete=models.CASCADE, related_name="+", verbose_name="grupo", help_text="Grupo al que pertenece.")
    audiencia = models.ForeignKey(
        "audiencias.Audiencia", on_delete=models.PROTECT, related_name="+", verbose_name="quién lo ve",
        help_text="Quién puede leerlo y comentarlo. Si cuelga de una reunión, el mismo que la reunión.",
    )
    ancla_tipo = models.CharField("cuelga de (tipo)", max_length=60, blank=True, help_text="Si cuelga de algo, su tipo: «eventos.evento»…")
    ancla_id = models.PositiveBigIntegerField("cuelga de (número)", null=True, blank=True, help_text="Si cuelga de algo, su número.")
    origen = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="derivados", verbose_name="sale de",
        help_text="El orden del día del que sale un acta.",
    )
    creador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="creado por", help_text="Quién lo creó."
    )
    estado = models.CharField("estado", max_length=10, choices=ESTADOS, default=BORRADOR, help_text="Borrador (se puede cambiar) o aprobado (ya no).")
    version = models.PositiveIntegerField("versión", default=0, help_text="Sube con cada cambio; sirve para no pisar el trabajo de otra persona.")
    autorias = models.JSONField(
        "quién ha escrito cada párrafo", default=list, blank=True,
        help_text="Una lista por párrafo con los alias que han contribuido a él; el último, quien lo cambió por última vez.",
    )
    creado = models.DateTimeField("creado", auto_now_add=True, help_text="Cuándo se creó.")
    actualizado = models.DateTimeField("último cambio", auto_now=True, help_text="Cuándo cambió por última vez.")
    aprobado_el = models.DateTimeField("aprobado el", null=True, blank=True, help_text="Cuándo se aprobó.")

    class Meta:
        verbose_name = "documento"
        verbose_name_plural = "documentos"
        ordering = ["-actualizado", "-pk"]
        indexes = [models.Index(fields=["ancla_tipo", "ancla_id"], name="documento_por_ancla")]

    # Texto con el que se muestra: su título.
    def __str__(self):
        return self.titulo


class CambioDeDocumento(models.Model):
    """
    Una línea del registro de cambios de un documento: quién lo cambió, cuándo y qué tocó. Nadie puede
    borrarlo (tampoco el superadmin): así nadie cambia un acta en silencio.
    """

    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name="cambios", verbose_name="documento", help_text="El documento.")
    alias = models.CharField("quién", max_length=30, help_text="Alias de quien lo cambió (se guarda el texto: si la cuenta desaparece, sigue).")
    cuando = models.DateTimeField("cuándo", auto_now_add=True, help_text="Fecha y hora del cambio.")
    resumen = models.CharField("qué cambió", max_length=200, help_text="«2 párrafos cambiados, 1 nuevo», «aprobado»…")

    class Meta:
        verbose_name = "cambio de documento"
        verbose_name_plural = "cambios de documentos"
        ordering = ["-cuando", "-pk"]

    # Texto con el que se muestra: quién y qué.
    def __str__(self):
        return f"{self.alias}: {self.resumen}"


class Comentario(models.Model):
    """
    Un comentario o una propuesta de cambio de alguien que lee el documento (sin poder escribirlo), hasta que
    se aprueba.
    """

    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name="comentarios", verbose_name="documento", help_text="El documento.")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="quién", help_text="Quién lo escribe."
    )
    texto = models.TextField("comentario", help_text="El comentario o la propuesta de cambio.")
    creado = models.DateTimeField("escrito", auto_now_add=True, help_text="Cuándo se escribió.")

    class Meta:
        verbose_name = "comentario"
        verbose_name_plural = "comentarios"
        ordering = ["creado", "pk"]

    # Texto con el que se muestra: el principio del comentario.
    def __str__(self):
        return self.texto[:60]


class LimitesDeDocumento(models.Model):
    """
    Cuántas personas pueden escribir y comentar un documento a la vez en el editor en tiempo real. Van en
    cascada y vale el más estricto: los de la plataforma (el superadmin), los de cada organización (su
    admin), los de cada grupo (su admin; valen también en sus subgrupos) y los de cada documento (la
    administración de su grupo, en sus «Opciones»). Cada fila es de un solo nivel; la de la plataforma no
    tiene ninguno. Vacío: sin límite en ese nivel.
    """

    organizacion = models.ForeignKey(
        "grupos.Organizacion", on_delete=models.CASCADE, null=True, blank=True, related_name="+",
        verbose_name="organización", help_text="Si son de una organización: cuál.",
    )
    grupo = models.ForeignKey(
        "grupos.Grupo", on_delete=models.CASCADE, null=True, blank=True, related_name="+",
        verbose_name="grupo", help_text="Si son de un grupo (y sus subgrupos): cuál.",
    )
    documento = models.OneToOneField(
        Documento, on_delete=models.CASCADE, null=True, blank=True, related_name="limites_propios",
        verbose_name="documento", help_text="Si son de un documento concreto: cuál.",
    )
    max_escritores = models.PositiveIntegerField(
        "personas que escriben", null=True, blank=True,
        help_text="Cuántas personas pueden tener la redacción y escribir a la vez. Quien llega de más entra a leer.",
    )
    max_comentaristas = models.PositiveIntegerField(
        "personas que comentan a la vez", null=True, blank=True, help_text="Cuántas personas pueden estar comentando a la vez en el editor.",
    )

    class Meta:
        verbose_name = "límites de los documentos"
        verbose_name_plural = "límites de los documentos"
        constraints = [
            models.UniqueConstraint(fields=["organizacion", "grupo", "documento"], nulls_distinct=False, name="limites_de_documento_por_nivel"),
        ]

    # Texto con el que se muestra: de quién son.
    def __str__(self):
        return f"Límites de {self.documento or self.grupo or self.organizacion or 'la plataforma'}"


class VersionDeDocumento(models.Model):
    """
    Una versión guardada del texto de un documento, para verla después, compararla o volver a ella. No se
    guarda una por cada cambio (el editor en tiempo real guarda cada pocos segundos): mientras se sigue
    escribiendo, la última versión se va poniendo al día; si pasan más de VERSION_CADA minutos sin
    escribir, o al aprobarse, empieza una nueva.
    """

    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name="versiones", verbose_name="documento", help_text="El documento.")
    numero = models.PositiveIntegerField("número", help_text="1, 2, 3… en el orden en que se guardaron.")
    texto = models.TextField("texto", help_text="El texto entero, tal como quedó.")
    autores = models.JSONField("quién escribió", default=list, help_text="Los alias de quienes escribieron en esta versión.")
    empezada = models.DateTimeField("empezada", auto_now_add=True, help_text="Cuándo se empezó a escribir esta versión.")
    cerrada = models.DateTimeField("último cambio", auto_now=True, help_text="Cuándo cambió por última vez.")
    motivo = models.CharField("motivo", max_length=80, blank=True, help_text="«creado», «aprobado», «vuelta a la versión 3»… o vacío (edición).")

    class Meta:
        verbose_name = "versión de documento"
        verbose_name_plural = "versiones de documentos"
        ordering = ["-numero"]
        constraints = [models.UniqueConstraint(fields=["documento", "numero"], name="version_unica")]

    # Texto con el que se muestra.
    def __str__(self):
        return f"Versión {self.numero} de {self.documento}"


class ComentarioEnElTexto(models.Model):
    """
    Un comentario hecho en el editor en tiempo real sobre un trozo del texto (resaltado, con su bocadillo).
    Viven en el editor; aquí se guarda una copia cada vez que cambian, para que queden registrados con el
    documento (y se vean en su ficha aunque no haya editor).
    """

    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name="comentarios_en_el_texto", verbose_name="documento", help_text="El documento.")
    clave = models.CharField("clave", max_length=40, help_text="Su identificador en el editor.")
    alias = models.CharField("quién", max_length=30, help_text="Alias de quien lo hizo.")
    texto = models.TextField("comentario", help_text="Lo que dice.")
    cita = models.TextField("trozo comentado", blank=True, help_text="El trozo del texto que comenta, tal como estaba la última vez.")
    cuando = models.DateTimeField("cuándo", help_text="Cuándo se hizo.")
    resuelto = models.BooleanField("resuelto", default=False, help_text="Si se marcó como resuelto (deja de resaltarse).")
    respuestas = models.JSONField("respuestas", default=list, help_text="Las respuestas: alias, texto y cuándo.")

    class Meta:
        verbose_name = "comentario en el texto"
        verbose_name_plural = "comentarios en el texto"
        ordering = ["cuando"]
        constraints = [models.UniqueConstraint(fields=["documento", "clave"], name="comentario_en_el_texto_unico")]

    # Texto con el que se muestra.
    def __str__(self):
        return f"{self.alias}: {self.texto[:40]}"
