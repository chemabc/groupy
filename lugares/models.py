"""
Tablas del módulo «lugares» (ver docs/diseno.md, apartado 8.2):

- Lugar: un sitio de trabajo (un instituto, un hospital…), de una lista común a toda la plataforma.
- LugarDePersona: el lugar que ha elegido cada persona. Solo lo ven ella y el superadmin.
- PropuestaDeLugar: un lugar nuevo o un cambio en los datos de un lugar, que propone una persona y aprueba
  (o no) el superadmin.
- ConfiguracionDeLugares: qué ven los miembros de cada organización (el mapa, los recuentos) y si se
  publica en su web pública.
"""

import re

from django.conf import settings
from django.db import models

# Formas de sacar las coordenadas de una URL de localización (OpenStreetMap, Google Maps y otras):
# «#map=17/40.41/-3.70», «mlat=40.41&mlon=-3.70», «@40.41,-3.70,17z», «?q=40.41,-3.70», «ll=40.41,-3.70».
PATRONES_DE_COORDENADAS = [
    re.compile(r"#map=\d+/(-?\d+\.\d+)/(-?\d+\.\d+)"),
    re.compile(r"mlat=(-?\d+\.\d+)&mlon=(-?\d+\.\d+)"),
    re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)"),
    re.compile(r"[?&](?:q|query|ll)=(-?\d+\.\d+)(?:,|%2C)\s*(-?\d+\.\d+)"),
]


# Saca (latitud, longitud) de una URL de localización, o (None, None) si no las encuentra.
#   - url: la dirección (por ejemplo, la de compartir de OpenStreetMap o de Google Maps).
def coordenadas_de(url):
    for patron in PATRONES_DE_COORDENADAS:
        encontrado = patron.search(url or "")
        if encontrado:
            latitud, longitud = float(encontrado.group(1)), float(encontrado.group(2))
            if -90 <= latitud <= 90 and -180 <= longitud <= 180:
                return latitud, longitud
    return None, None


class DatosDeLugar(models.Model):
    """
    Los datos de un lugar, comunes a la lista y a las propuestas. Es abstracta: no crea tabla propia.
    """

    nombre = models.CharField("nombre", max_length=150, help_text="Cómo se llama: «IES Cervantes», «Hospital del Henares».")
    direccion = models.CharField("dirección", max_length=250, help_text="Calle, número, código postal y municipio.")
    url_localizacion = models.URLField(
        "URL de localización", max_length=500,
        help_text="Enlace al sitio en un mapa (OpenStreetMap, Google Maps…). De él se sacan las coordenadas para el mapa.",
    )
    latitud = models.FloatField("latitud", null=True, blank=True, help_text="Se rellena sola desde la URL si se puede. Por ejemplo, 40.4168.")
    longitud = models.FloatField("longitud", null=True, blank=True, help_text="Se rellena sola desde la URL si se puede. Por ejemplo, -3.7038.")
    telefonos = models.CharField("teléfonos", max_length=200, blank=True, help_text="Uno o varios, separados por comas. Opcional.")
    correos = models.CharField("correos", max_length=300, blank=True, help_text="Uno o varios, separados por comas. Opcional.")
    notas = models.TextField("notas", blank=True, help_text="Lo que convenga saber del lugar: horarios, accesos, a quién preguntar… Opcional.")

    class Meta:
        abstract = True

    # Antes de guardar: si faltan las coordenadas, se intentan sacar de la URL de localización.
    def save(self, *args, **kwargs):
        if self.latitud is None or self.longitud is None:
            self.latitud, self.longitud = coordenadas_de(self.url_localizacion)
        super().save(*args, **kwargs)


class Lugar(DatosDeLugar):
    """
    Lugar de trabajo de la lista común a toda la plataforma. Lo crea o lo sube el superadmin, o entra al
    aceptar una propuesta. Cada persona puede elegir el suyo.
    """

    activo = models.BooleanField("en la lista", default=True, help_text="Si se puede elegir. Uno retirado se queda para quien ya lo tenía.")
    creado = models.DateTimeField("creado", auto_now_add=True, help_text="Cuándo entró en la lista.")

    class Meta:
        verbose_name = "lugar"
        verbose_name_plural = "lugares"
        ordering = ["nombre"]

    # Texto con el que se muestra: su nombre.
    def __str__(self):
        return self.nombre


class LugarDePersona(models.Model):
    """El lugar que ha elegido una persona. Solo lo ven ella y el superadmin (los recuentos, a partir de 5)."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lugar_elegido", verbose_name="usuario", help_text="Quién."
    )
    lugar = models.ForeignKey(Lugar, on_delete=models.PROTECT, related_name="personas", verbose_name="lugar", help_text="Dónde trabaja.")
    desde = models.DateField("desde", auto_now=True, help_text="Día en que lo eligió (o lo cambió).")

    class Meta:
        verbose_name = "lugar de una persona"
        verbose_name_plural = "lugares de las personas"

    # Texto con el que se muestra: «Nutria: IES Cervantes».
    def __str__(self):
        return f"{self.usuario}: {self.lugar}"


class PropuestaDeLugar(DatosDeLugar):
    """
    Propuesta de una persona: un lugar nuevo para la lista o un cambio en los datos de uno que ya está. La
    revisa el superadmin: si la acepta, el lugar se crea (y pasa a ser el de quien lo propuso) o se cambia.
    """

    PENDIENTE = "pendiente"
    ACEPTADA = "aceptada"
    RECHAZADA = "rechazada"
    ESTADOS = [(PENDIENTE, "Pendiente"), (ACEPTADA, "Aceptada"), (RECHAZADA, "Rechazada")]

    lugar = models.ForeignKey(
        Lugar, on_delete=models.CASCADE, null=True, blank=True, related_name="propuestas", verbose_name="lugar que cambia",
        help_text="Si es un cambio, el lugar que cambia. Vacío: es un lugar nuevo.",
    )
    propuesta_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+", verbose_name="propuesta por", help_text="Quién la propone."
    )
    motivo = models.TextField("motivo", blank=True, help_text="Por qué se propone (sobre todo en los cambios).")
    estado = models.CharField("estado", max_length=20, choices=ESTADOS, default=PENDIENTE, help_text="En qué punto está.")
    respuesta = models.TextField("respuesta", blank=True, help_text="Lo que contesta el superadmin, sobre todo si la rechaza.")
    creada = models.DateTimeField("propuesta", auto_now_add=True, help_text="Cuándo se propuso.")
    revisada_el = models.DateTimeField("revisada", null=True, blank=True, help_text="Cuándo la aceptó o rechazó el superadmin.")

    class Meta:
        verbose_name = "propuesta de lugar"
        verbose_name_plural = "propuestas de lugares"
        ordering = ["-creada", "-pk"]

    # Texto con el que se muestra: «Lugar nuevo: IES Cervantes» o «Cambio en IES Cervantes».
    def __str__(self):
        return f"Cambio en {self.lugar}" if self.lugar_id else f"Lugar nuevo: {self.nombre}"


class ConfiguracionDeLugares(models.Model):
    """
    Qué muestra cada organización sobre los lugares. La ajustan el superadmin y el admin de la
    organización, por si resulta información delicada. Sin fila, lo que dice cada campo por defecto.
    """

    organizacion = models.OneToOneField(
        "grupos.Organizacion", on_delete=models.CASCADE, related_name="configuracion_de_lugares", verbose_name="organización",
        help_text="La organización.",
    )
    mapa_para_miembros = models.BooleanField(
        "sus miembros ven el mapa y la lista", default=True, help_text="Si las personas de la organización ven el mapa y la lista de lugares."
    )
    recuentos_para_miembros = models.BooleanField(
        "sus miembros ven los recuentos", default=True,
        help_text="Si ven cuántas personas de la organización hay en cada lugar (solo a partir de 5; nunca quiénes).",
    )
    publicar_en_la_web = models.BooleanField(
        "publicar el mapa en su web pública", default=False,
        help_text="Si el mapa de lugares (sin recuentos) sale en la parte pública de la organización. Llegará con el módulo «público».",
    )

    class Meta:
        verbose_name = "configuración de lugares"
        verbose_name_plural = "configuraciones de lugares"

    # Texto con el que se muestra: «Lugares de ORG Tajo».
    def __str__(self):
        return f"Lugares de {self.organizacion}"
