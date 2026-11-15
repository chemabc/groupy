"""
Tablas del módulo «publico» (ver docs/diseno.md, apartado 15): la portada pública y las miniwebs de los
grupos.

- Pagina: una página con texto con formato (Markdown), que se escribe como borrador y se publica. Si es de
  la plataforma o de una organización y está marcada «pública», sale en su portada sin sesión; si es de un
  grupo (o interna de una organización), la ven el grupo y lo que cuelga de él.
- ImagenDePagina: las imágenes que lleva una página.
- RelacionDeConsumo: un grupo (por ejemplo, de actividad) publica para otro, que ha aceptado: lo que publica
  el primero les aparece al segundo y a los que cuelgan de él.
- LecturaDeNovedades: hasta cuándo ha mirado cada persona las novedades (para su número).
"""

from django.conf import settings
from django.db import models


class Pagina(models.Model):
    """
    Una página de una web: la portada pública de la plataforma o de una organización, o la miniweb de un
    grupo. Se escribe en Markdown (en el editor en tiempo real, si lo hay) como borrador; al «Publicar» se
    guarda una foto convertida en HTML seguro, que es lo que se ve. Lo publicado no cambia hasta volver a
    publicar. Sale como una pestaña de su web, en el orden indicado.
    """

    titulo = models.CharField("título", max_length=120, help_text="Nombre de la pestaña: «Quiénes somos», «Calendario de la huerta».")
    organizacion = models.ForeignKey(
        "grupos.Organizacion", on_delete=models.CASCADE, null=True, blank=True, related_name="+", verbose_name="organización",
        help_text="De qué organización es. Vacía (y sin grupo): la portada de la plataforma.",
    )
    grupo = models.ForeignKey(
        "grupos.Grupo", on_delete=models.CASCADE, null=True, blank=True, related_name="+", verbose_name="grupo",
        help_text="De qué grupo es su miniweb. Vacío: de toda la organización (o de la plataforma).",
    )
    publica = models.BooleanField(
        "pública", default=False,
        help_text="Si sale en la portada pública, sin sesión. Solo las de la plataforma y las de una organización (no las de un grupo).",
    )
    orden = models.PositiveSmallIntegerField("orden", default=10, help_text="Posición de la pestaña: los números bajos salen antes.")
    borrador = models.TextField("borrador", blank=True, help_text="El texto que se está escribiendo, en Markdown. No se ve hasta publicar.")
    version = models.PositiveIntegerField("versión", default=0, help_text="Sube con cada cambio del borrador; sirve para no pisar el trabajo de otra persona.")
    texto_publicado = models.TextField("texto publicado", blank=True, help_text="El Markdown tal como se publicó (para buscar).")
    html = models.TextField("lo publicado", blank=True, help_text="La foto publicada, ya convertida en HTML seguro. Vacía: aún sin publicar.")
    publicada_el = models.DateTimeField("publicada el", null=True, blank=True, help_text="Cuándo se publicó por última vez.")
    publicada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="publicada por",
        help_text="Quién la publicó por última vez.",
    )
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="creada por", help_text="Quién la creó."
    )
    creada = models.DateTimeField("creada", auto_now_add=True, help_text="Cuándo se creó.")
    actualizada = models.DateTimeField("último cambio", auto_now=True, help_text="Cuándo cambió por última vez (borrador o publicación).")

    class Meta:
        verbose_name = "página"
        verbose_name_plural = "páginas"
        ordering = ["orden", "pk"]
        constraints = [
            models.CheckConstraint(condition=~models.Q(publica=True, grupo__isnull=False), name="pagina_de_grupo_no_publica"),
        ]

    # Texto con el que se muestra: su título.
    def __str__(self):
        return self.titulo

    # Si está publicada (tiene una foto publicada).
    @property
    def publicada(self):
        return bool(self.publicada_el)

    # De quién es, en palabras: «GRU Henares», «ORG Tajo» o «Plataforma». Necesita el grupo y la
    # organización cargados.
    @property
    def duena(self):
        if self.grupo_id:
            return self.grupo.nombre
        if self.organizacion_id:
            return self.organizacion.nombre
        return "Plataforma"


# Dónde se guarda cada imagen: una carpeta por mes y un nombre al azar (con su extensión).
def ruta_de_imagen(imagen, nombre):
    import uuid

    extension = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else "png"
    return f"publico/{imagen.subida:%Y/%m}/{uuid.uuid4().hex}.{extension}"


class ImagenDePagina(models.Model):
    """
    Una imagen que lleva una página (PNG, JPG, WebP o GIF, hasta 5 MB). Se pone en el texto con
    «![descripción](dirección)». La ve quien puede ver la página; si la página es pública, cualquiera.
    """

    pagina = models.ForeignKey(Pagina, on_delete=models.CASCADE, related_name="imagenes", verbose_name="página", help_text="La página que la lleva.")
    fichero = models.ImageField("imagen", upload_to=ruta_de_imagen, max_length=200, help_text="PNG, JPG, WebP o GIF, hasta 5 MB.")
    nombre = models.CharField("nombre", max_length=200, help_text="Cómo se llamaba el archivo; sirve de descripción de partida.")
    subida = models.DateTimeField("subida", help_text="Cuándo se subió.")

    class Meta:
        verbose_name = "imagen de una página"
        verbose_name_plural = "imágenes de las páginas"
        ordering = ["-subida", "-pk"]

    # Texto con el que se muestra: su nombre.
    def __str__(self):
        return self.nombre


class RelacionDeConsumo(models.Model):
    """
    Publicación y consumo entre dos grupos: el que publica (por ejemplo, un grupo de actividad que no está
    en las asambleas) lo propone y la administración del que consume lo acepta. Desde entonces, las páginas
    del que publica las ven también el que consume y los grupos que cuelgan de él, y les salen como
    novedad. Cualquiera de las dos administraciones la corta.
    """

    PROPUESTA = "propuesta"
    ACEPTADA = "aceptada"
    ESTADOS = [(PROPUESTA, "Propuesta (espera respuesta)"), (ACEPTADA, "Aceptada")]

    productor = models.ForeignKey(
        "grupos.Grupo", on_delete=models.CASCADE, related_name="+", verbose_name="grupo que publica", help_text="El que publica sus páginas."
    )
    consumidor = models.ForeignKey(
        "grupos.Grupo", on_delete=models.CASCADE, related_name="+", verbose_name="grupo que las recibe",
        help_text="El que las recibe (con los grupos que cuelgan de él).",
    )
    estado = models.CharField("estado", max_length=10, choices=ESTADOS, default=PROPUESTA, help_text="Propuesta (espera el sí del grupo que recibe) o aceptada.")
    mensaje = models.CharField("mensaje", max_length=300, blank=True, help_text="Por qué lo propone, para quien tiene que aceptarlo.")
    propuesta_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="propuesta por", help_text="Quién la propuso."
    )
    aceptada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="aceptada por",
        help_text="Quién la aceptó.",
    )
    creada = models.DateTimeField("propuesta el", auto_now_add=True, help_text="Cuándo se propuso.")
    aceptada_el = models.DateTimeField("aceptada el", null=True, blank=True, help_text="Cuándo se aceptó.")

    class Meta:
        verbose_name = "relación de publicación y consumo"
        verbose_name_plural = "relaciones de publicación y consumo"
        ordering = ["-creada", "-pk"]
        constraints = [
            models.UniqueConstraint(fields=["productor", "consumidor"], name="una_relacion_de_consumo_por_pareja"),
            models.CheckConstraint(condition=~models.Q(productor=models.F("consumidor")), name="consumo_entre_grupos_distintos"),
        ]

    # Texto con el que se muestra: «GRU Huerta → GRU Henares».
    def __str__(self):
        return f"{self.productor} → {self.consumidor}"


class LecturaDeNovedades(models.Model):
    """Hasta cuándo ha mirado una persona las novedades de las webs (lo publicado después cuenta como nuevo)."""

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+", verbose_name="usuario", help_text="Quién.")
    vistas_hasta = models.DateTimeField("vistas hasta", help_text="La última vez que miró las novedades.")

    class Meta:
        verbose_name = "lectura de novedades"
        verbose_name_plural = "lecturas de novedades"

    # Texto con el que se muestra: «Nutria: 15/11/2026».
    def __str__(self):
        return f"{self.usuario}: {self.vistas_hasta:%d/%m/%Y}"
