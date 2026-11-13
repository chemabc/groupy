"""
Tablas del módulo «tipologias»: los tipos de proyecto y de evento, en árbol, con sus campos
personalizados (ver docs/diseno.md, apartado 9).

Un subtipo hereda los campos de su tipo, y del tipo de este, y así hasta arriba («Acción → Concentración»:
la concentración pide los campos de la acción y los suyos). Las tipologías comunes las crea el superadmin;
el admin de cada organización puede añadir subtipos propios de su organización, que solo se ven en ella.
"""

import re

from django.core.exceptions import ValidationError
from django.db import models

from base.tablas import normalizar


class Tipologia(models.Model):
    """
    Tipología: un tipo de proyecto o de evento (Reunión, Acción, Concentración…), dentro de un árbol.
    """

    # Familias: de qué es tipo. Los módulos «proyectos» y «eventos» usan cada una la suya.
    PROYECTO = "proyecto"
    EVENTO = "evento"
    FAMILIAS = [(PROYECTO, "De proyectos"), (EVENTO, "De eventos")]

    familia = models.CharField("familia", max_length=20, choices=FAMILIAS, help_text="Si es un tipo de proyecto o de evento.")
    padre = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="hijas", verbose_name="tipología padre",
        help_text="El tipo del que es un subtipo (hereda sus campos). Vacío si es un tipo principal.",
    )
    organizacion = models.ForeignKey(
        "grupos.Organizacion", on_delete=models.CASCADE, null=True, blank=True, related_name="tipologias",
        verbose_name="organización",
        help_text="Organización a la que pertenece (solo se usa en ella). Vacía: común a todas (solo la crea el superadmin).",
    )
    nombre = models.CharField("nombre", max_length=80, help_text="Nombre del tipo, como se verá en las listas.")
    descripcion = models.TextField("descripción", blank=True, help_text="Para qué sirve este tipo, en una o dos frases.")

    class Meta:
        verbose_name = "tipología"
        verbose_name_plural = "tipologías"
        ordering = ["familia", "nombre"]

    # Texto con el que se muestra: su nombre.
    def __str__(self):
        return self.nombre

    # Comprueba la tipología: el padre es de la misma familia; una común solo cuelga de comunes; una de una
    # organización cuelga de una común o de otra de su misma organización; sin círculos ni nombres
    # repetidos entre hermanas.
    def clean(self):
        super().clean()
        if self.padre_id:
            padre = self.padre
            if padre.familia != self.familia:
                raise ValidationError({"padre": "El tipo padre debe ser de la misma familia (proyectos o eventos)."})
            if padre.organizacion_id and padre.organizacion_id != self.organizacion_id:
                raise ValidationError({"padre": "Un tipo de una organización solo puede ser padre de tipos de esa misma organización."})
            vistos, actual = {self.pk}, padre
            while actual is not None:
                if actual.pk in vistos:
                    raise ValidationError({"padre": "El tipo padre no puede ser el propio tipo ni uno de sus subtipos."})
                vistos.add(actual.pk)
                actual = actual.padre
        # Hermanas con las que no puede compartir nombre: las comunes y las de su misma organización. Las
        # de otras organizaciones no cuentan (ni se dejan adivinar con este error). Una común se compara
        # con todas, para que ninguna organización vea dos tipos con el mismo nombre en el mismo sitio.
        hermanas = Tipologia.objects.filter(familia=self.familia, padre_id=self.padre_id).exclude(pk=self.pk)
        if self.organizacion_id is not None:
            hermanas = hermanas.filter(models.Q(organizacion__isnull=True) | models.Q(organizacion_id=self.organizacion_id))
        if any(normalizar(hermana.nombre) == normalizar(self.nombre) for hermana in hermanas):
            raise ValidationError({"nombre": "Ya hay un tipo con ese nombre en el mismo sitio del árbol."})


class Campo(models.Model):
    """
    Campo personalizado de una tipología: un dato extra que se pide al crear algo de ese tipo
    («Número de asistentes previstos»). Los valores se guardan en JSON dentro del propio proyecto o evento.
    """

    # Tipos de campo.
    TEXTO = "texto"
    TEXTO_LARGO = "texto_largo"
    NUMERO = "numero"
    FECHA = "fecha"
    SI_NO = "si_no"
    LISTA = "lista"
    TIPOS = [
        (TEXTO, "Texto corto"),
        (TEXTO_LARGO, "Texto largo"),
        (NUMERO, "Número"),
        (FECHA, "Fecha"),
        (SI_NO, "Sí o no"),
        (LISTA, "Lista de opciones"),
    ]

    tipologia = models.ForeignKey(
        Tipologia, on_delete=models.CASCADE, related_name="campos", verbose_name="tipología", help_text="La tipología que lo pide."
    )
    nombre = models.CharField("nombre", max_length=80, help_text="Lo que se pregunta, como se verá en el formulario.")
    clave = models.SlugField(
        "clave", max_length=60, editable=False,
        help_text="Nombre interno con el que se guarda el valor (se calcula del nombre y no cambia).",
    )
    tipo = models.CharField("tipo", max_length=20, choices=TIPOS, default=TEXTO, help_text="Qué clase de dato es.")
    obligatorio = models.BooleanField("obligatorio", default=False, help_text="Si hay que rellenarlo para poder guardar.")
    ayuda = models.CharField("explicación", max_length=200, blank=True, help_text="Texto de ayuda que se ve debajo del campo.")
    opciones = models.TextField(
        "opciones", blank=True, help_text="Solo para «Lista de opciones»: una opción por línea."
    )
    orden = models.PositiveSmallIntegerField("orden", default=0, help_text="Posición dentro de su tipología (se cambia arrastrando).")

    class Meta:
        verbose_name = "campo personalizado"
        verbose_name_plural = "campos personalizados"
        ordering = ["tipologia", "orden", "pk"]
        constraints = [models.UniqueConstraint(fields=["tipologia", "clave"], name="clave_de_campo_unica")]

    # Texto con el que se muestra: su nombre.
    def __str__(self):
        return self.nombre

    # Las opciones de una lista, una por línea, sin vacías.
    @property
    def lista_de_opciones(self):
        return [linea.strip() for linea in self.opciones.splitlines() if linea.strip()]

    # Comprueba el campo: una lista necesita al menos dos opciones, y su clave no puede repetirse en la
    # tipología ni en las de arriba o abajo del árbol (porque se heredan).
    def clean(self):
        super().clean()
        if self.tipo == self.LISTA and len(self.lista_de_opciones) < 2:
            raise ValidationError({"opciones": "Una lista necesita al menos dos opciones, una por línea."})
        if self.tipo != self.LISTA:
            self.opciones = ""
        self.clave = self.clave or clave_de(self.nombre)
        if not self.clave:
            raise ValidationError({"nombre": "El nombre debe tener alguna letra o número."})
        parientes = _ids_de_la_rama(self.tipologia)
        repetido = Campo.objects.filter(tipologia_id__in=parientes, clave=self.clave).exclude(pk=self.pk).first()
        if repetido is not None:
            raise ValidationError({"nombre": f"Ya hay un campo «{repetido}» con ese nombre en «{repetido.tipologia}» (se heredan)."})

    # Guarda el campo calculando su clave la primera vez.
    def save(self, *args, **kwargs):
        self.clave = self.clave or clave_de(self.nombre)
        super().save(*args, **kwargs)


# Clave interna a partir del nombre de un campo: sin tildes, en minúsculas y con «_» («Número de
# asistentes» → «numero_de_asistentes»).
def clave_de(nombre):
    return re.sub(r"[^a-z0-9]+", "_", normalizar(nombre)).strip("_")[:60]


# Ids de una tipología, de sus antecesoras y de todas sus descendientes: las que comparten campos con ella.
def _ids_de_la_rama(tipologia):
    ids, actual = set(), tipologia
    while actual is not None:
        ids.add(actual.pk)
        actual = actual.padre
    pendientes = [tipologia.pk]
    while pendientes:
        hijas = list(Tipologia.objects.filter(padre_id__in=pendientes).values_list("pk", flat=True))
        ids.update(hijas)
        pendientes = hijas
    return ids
