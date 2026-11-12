"""
Tablas del módulo «grupos»: organizaciones, grupos y lo que cada persona es en ellos.

- Organizacion: ámbito independiente de las demás (ver docs/diseno.md, apartado 8.1).
- Grupo: colectivo real; puede contener subgrupos (campo «padre»), a cualquier profundidad (grupo
  general → grupo de zona → grupo de centro → …).
- Contencion: la tabla de cierre, con cada par «antecesor contiene a descendiente». Se mantiene sola al
  guardar un grupo y permite saber de una vez todos los grupos que contienen a otro, sin recorrer el
  árbol consulta a consulta.
- Pertenencia: que un usuario está en un grupo, con su rol allí y si es su asamblea base.
- AdminDeOrganizacion: quién es admin de cada organización.
- RelacionEntreGrupos: relaciones libres entre grupos («colabora con», «nació de»…), para el grafo.
- InvitacionDeGrupo: un grupo invita a un grupo de otra organización a algo concreto (un proyecto).
"""

from django.apps import apps
from django.conf import settings
from django.contrib.postgres.aggregates import StringAgg
from django.contrib.postgres.lookups import Unaccent
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import OuterRef, Subquery
from django.db.models.functions import Collate, Lower
from django.utils import timezone

from eventos_sw.servicios import emitir


class Organizacion(models.Model):
    """
    Organización: ámbito abstracto, jurídico, independiente de las demás. Agrupa grupos y tiene al menos
    uno. Nadie pertenece a una organización sin pertenecer a uno de sus grupos.
    """

    nombre = models.CharField(
        "nombre", max_length=100, unique=True, help_text="Nombre de la organización. No puede repetirse."
    )
    descripcion = models.TextField(
        "descripción", blank=True, help_text="Qué es y a qué se dedica, en pocas líneas."
    )
    creada_el = models.DateField(
        "creada el día", default=timezone.localdate, help_text="Día en que se dio de alta en la plataforma."
    )

    class Meta:
        verbose_name = "organización"
        verbose_name_plural = "organizaciones"
        ordering = ["nombre"]

    # Texto con el que se muestra la organización: su nombre.
    def __str__(self):
        return self.nombre


# Subconsulta con el «camino» de un grupo: los nombres de todos sus antecesores, del más alto al propio
# grupo («GRU Tajo › GRU Jarama › GRU Henares»). Sale de la tabla de cierre dentro de la misma consulta
# (PostgreSQL la resuelve para todas las filas de una vez), así que no añade consultas aunque haya
# muchas filas. Ordenar por el camino deja los grupos en orden de árbol.
#   - referencia: campo de la consulta de fuera que lleva al grupo («pk» en una consulta de grupos,
#     «grupo» en una de pertenencias).
def camino(referencia="pk"):
    return Subquery(
        Contencion.objects.filter(descendiente=OuterRef(referencia))
        .values("descendiente")
        .annotate(texto=StringAgg("antecesor__nombre", delimiter=" › ", order_by="-distancia"))
        .values("texto")
    )


# Subconsulta con la clave para ordenar grupos en orden de árbol: cada grupo justo después de su padre
# y, entre hermanos, por orden alfabético. Es el camino sin tildes y en minúsculas, unido con un carácter
# de control que va antes que cualquier letra, y se compara letra a letra (intercalación «C»). Hace falta
# porque al ordenar el camino que se ve («GRU Duero › GRU Adaja»), PostgreSQL sigue las reglas del idioma
# y no tiene en cuenta los signos como «›», así que «GRU Duero» acabaría entre sus afluentes.
#   - referencia: como en camino().
def orden_de_arbol(referencia="pk"):
    claves = (
        Contencion.objects.filter(descendiente=OuterRef(referencia))
        .values("descendiente")
        .annotate(texto=StringAgg(Lower(Unaccent("antecesor__nombre")), delimiter="\x01", order_by="-distancia"))
        .values("texto")
    )
    return Collate(Subquery(claves), "C")


class ConsultaDeGrupos(models.QuerySet):
    """
    Consultas de grupos con añadidos útiles para las listas. Se usa como Grupo.objects.
    """

    # Añade a cada grupo su camino (ver camino()).
    def con_camino(self):
        return self.annotate(camino=camino("pk"))

    # Añade el camino y ordena en orden de árbol: por organización y, dentro, cada grupo después de su
    # padre (ver orden_de_arbol()).
    def en_orden_de_arbol(self):
        return self.con_camino().annotate(orden=orden_de_arbol("pk")).order_by("organizacion__nombre", "orden")


class Grupo(models.Model):
    """
    Grupo: colectivo real y concreto (asamblea, grupo de trabajo, comisión…) de una organización. Puede
    estar dentro de otro grupo (su padre) y contener subgrupos. Al guardarlo se pone al día la tabla de
    cierre (Contencion).
    """

    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.PROTECT,
        related_name="grupos",
        verbose_name="organización",
        help_text="Organización a la que pertenece. No se puede cambiar después de crearlo.",
    )
    padre = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="hijos",
        verbose_name="grupo padre",
        help_text=(
            "Grupo que lo contiene, de la misma organización. Vacío si es un grupo principal. Puede haber "
            "tantos niveles como hagan falta (general → zona → centro → …): sus miembros cuentan también "
            "como miembros del padre, del abuelo y de todos los que están por encima."
        ),
    )
    nombre = models.CharField(
        "nombre", max_length=100, help_text="Nombre del grupo. No puede repetirse dentro de su organización."
    )
    descripcion = models.TextField("descripción", blank=True, help_text="Para qué existe el grupo y qué hace.")
    ambito = models.CharField(
        "ámbito geográfico",
        max_length=100,
        blank=True,
        help_text="Zona que abarca (un barrio, un municipio, una provincia…). Opcional.",
    )
    creado_el = models.DateField(
        "creado el día", default=timezone.localdate, help_text="Día en que se dio de alta en la plataforma."
    )

    objects = ConsultaDeGrupos.as_manager()

    class Meta:
        verbose_name = "grupo"
        verbose_name_plural = "grupos"
        ordering = ["organizacion__nombre", "nombre"]
        constraints = [
            models.UniqueConstraint(fields=["organizacion", "nombre"], name="grupo_nombre_unico_en_su_organizacion"),
        ]

    # Texto con el que se muestra el grupo: su nombre.
    def __str__(self):
        return self.nombre

    # Django llama a este método al leer un grupo de la base de datos. Se apuntan el padre y la
    # organización con los que estaba guardado, para saber al guardarlo si han cambiado.
    @classmethod
    def from_db(cls, db, field_names, values):
        grupo = super().from_db(db, field_names, values)
        grupo._padre_guardado = grupo.padre_id
        grupo._organizacion_guardada = grupo.organizacion_id
        return grupo

    # Comprueba el grupo antes de guardarlo: el padre debe ser de la misma organización, no puede estar
    # dentro del propio grupo (sería un círculo) y la organización no cambia.
    def clean(self):
        super().clean()
        if not self._state.adding and self.organizacion_id != getattr(self, "_organizacion_guardada", None):
            raise ValidationError({"organizacion": "Un grupo no puede cambiar de organización."})
        if self.padre_id is None:
            return
        if self.padre.organizacion_id != self.organizacion_id:
            raise ValidationError({"padre": "El grupo padre debe ser de la misma organización."})
        if self.pk and Contencion.objects.filter(antecesor_id=self.pk, descendiente_id=self.padre_id).exists():
            raise ValidationError({"padre": "El grupo padre no puede ser el propio grupo ni uno de sus subgrupos."})

    # Guarda el grupo y pone al día la tabla de cierre si es nuevo o ha cambiado de padre. Todo en una
    # transacción: o se guarda todo, o nada. Avisa con «grupos.estructura_cambiada».
    def save(self, *args, **kwargs):
        nuevo = self._state.adding
        cambia_de_padre = not nuevo and self.padre_id != getattr(self, "_padre_guardado", None)
        if nuevo or cambia_de_padre:
            self.clean()
        with transaction.atomic():
            super().save(*args, **kwargs)
            if nuevo:
                Contencion.objects.create(antecesor=self, descendiente=self, distancia=0)
                self._colgar_subarbol([(self.pk, 0)])
            elif cambia_de_padre:
                subarbol = list(Contencion.objects.filter(antecesor=self).values_list("descendiente_id", "distancia"))
                self._descolgar_subarbol([descendiente for descendiente, _distancia in subarbol])
                self._colgar_subarbol(subarbol)
            if nuevo or cambia_de_padre:
                emitir("grupos.estructura_cambiada", grupo_id=self.pk)
        self._padre_guardado = self.padre_id
        self._organizacion_guardada = self.organizacion_id

    # Borra de la tabla de cierre los pares que unen el subárbol del grupo (él y sus subgrupos) con sus
    # antiguos antecesores. Los pares de dentro del subárbol se quedan, porque no cambian.
    #   - subarbol: ids del grupo y de todos sus descendientes.
    def _descolgar_subarbol(self, subarbol):
        Contencion.objects.filter(descendiente_id__in=subarbol).exclude(antecesor_id__in=subarbol).delete()

    # Añade a la tabla de cierre los pares que unen cada antecesor del nuevo padre (también el padre
    # mismo) con cada grupo del subárbol, con su distancia. Con una sola consulta de escritura.
    #   - subarbol: pares (id del descendiente, distancia desde este grupo).
    def _colgar_subarbol(self, subarbol):
        if self.padre_id is None:
            return
        antecesores = Contencion.objects.filter(descendiente_id=self.padre_id).values_list("antecesor_id", "distancia")
        Contencion.objects.bulk_create(
            Contencion(antecesor_id=antecesor, descendiente_id=descendiente, distancia=hasta_el_padre + 1 + desde_aqui)
            for antecesor, hasta_el_padre in antecesores
            for descendiente, desde_aqui in subarbol
        )


class Contencion(models.Model):
    """
    Tabla de cierre de los grupos: una fila por cada par «antecesor contiene a descendiente», también
    del grupo consigo mismo (distancia 0). Así, «todos los grupos que contienen a X» o «todos los
    subgrupos de Y, a cualquier profundidad» se sacan con una sola consulta. Se rellena sola al guardar
    los grupos; no se edita a mano.
    """

    antecesor = models.ForeignKey(
        Grupo,
        on_delete=models.CASCADE,
        related_name="descendencia",
        verbose_name="antecesor",
        help_text="El grupo que contiene.",
    )
    descendiente = models.ForeignKey(
        Grupo,
        on_delete=models.CASCADE,
        related_name="ascendencia",
        verbose_name="descendiente",
        help_text="El grupo contenido (o el propio antecesor, con distancia 0).",
    )
    distancia = models.PositiveSmallIntegerField(
        "distancia", help_text="Niveles entre los dos: 0 el mismo grupo, 1 padre e hijo, 2 abuelo y nieto…"
    )

    class Meta:
        verbose_name = "contención entre grupos"
        verbose_name_plural = "contenciones entre grupos (tabla de cierre)"
        constraints = [
            models.UniqueConstraint(fields=["antecesor", "descendiente"], name="contencion_unica"),
        ]

    # Texto con el que se muestra: «Jarama ⊃ Henares (1)».
    def __str__(self):
        return f"{self.antecesor_id} ⊃ {self.descendiente_id} ({self.distancia})"


class Pertenencia(models.Model):
    """
    Pertenencia: que un usuario está en un grupo, con su rol allí. Quien está en un grupo cuenta también
    como miembro de los grupos que lo contienen (eso se calcula con la tabla de cierre, no se guarda).
    Una de sus pertenencias, como mucho, es su asamblea base.
    """

    # Códigos de los roles de grupo del sistema. Hay más roles posibles: los que crea el superadmin
    # (tabla Rol del módulo «permisos»). El superadmin es una marca del usuario, y el admin de una
    # organización está en AdminDeOrganizacion.
    USUARIO = "usuario"
    ADMIN_GRUPO = "admin_grupo"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pertenencias",
        verbose_name="usuario",
        help_text="Quién está en el grupo.",
    )
    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.CASCADE,
        related_name="pertenencias",
        verbose_name="grupo",
        help_text="En qué grupo está.",
    )
    rol = models.CharField(
        "rol",
        max_length=40,
        default=USUARIO,
        help_text=(
            "Código de su rol en el grupo: «usuario», «admin_grupo» (cuida la estructura, no filtra) o uno "
            "de los roles de grupo que haya creado el superadmin (ver «Roles y permisos»)."
        ),
    )
    rol_desde = models.DateField(
        "con este rol desde",
        default=timezone.localdate,
        help_text="Día desde el que tiene este rol. El grupo ve cuánto tiempo lleva cada admin.",
    )
    es_base = models.BooleanField(
        "asamblea base",
        default=False,
        help_text=(
            "Si este grupo es su asamblea base: su grupo más local, el que la valida. Solo puede tener una "
            "en toda la plataforma."
        ),
    )
    desde = models.DateField("desde", default=timezone.localdate, help_text="Día en que entró en el grupo.")

    class Meta:
        verbose_name = "pertenencia"
        verbose_name_plural = "pertenencias"
        constraints = [
            models.UniqueConstraint(fields=["usuario", "grupo"], name="pertenencia_unica"),
            models.UniqueConstraint(
                fields=["usuario"],
                condition=models.Q(es_base=True),
                name="una_asamblea_base_por_persona",
                violation_error_message="Esta persona ya tiene otra asamblea base.",
            ),
        ]

    # Texto con el que se muestra: «Lince en GRU Henares».
    def __str__(self):
        return f"{self.usuario} en {self.grupo}"

    # Comprueba que el rol existe y es de grupo. La tabla de roles es del módulo «permisos» y se busca por
    # su nombre (apps.get_model), sin importarlo, para no formar un círculo entre los dos módulos.
    def clean(self):
        super().clean()
        roles = apps.get_model("permisos", "Rol").objects.filter(nivel="grupo")
        if not roles.filter(codigo=self.rol).exists():
            raise ValidationError({"rol": f"No existe el rol de grupo «{self.rol}»."})


class SoloAdminsDeGrupo(models.Manager):
    """Gestor que solo devuelve las pertenencias con rol de admin del grupo. Lo usa AdminDeGrupo."""

    # Consulta base: las pertenencias cuyo rol es admin_grupo.
    def get_queryset(self):
        return super().get_queryset().filter(rol=Pertenencia.ADMIN_GRUPO)


class AdminDeGrupo(Pertenencia):
    """
    Admin de un grupo: no es una tabla aparte, sino las pertenencias con rol «admin del grupo» (un
    «modelo proxy» de Django: otra forma de ver la misma tabla). Existe para poder listar juntos, en la
    trastienda, los admins de grupo y los de organización.
    """

    objects = SoloAdminsDeGrupo()

    class Meta:
        proxy = True
        verbose_name = "admin de grupo"
        verbose_name_plural = "admins de grupo"


class AdminDeOrganizacion(models.Model):
    """
    Admin de una organización (admin_org). No se hereda: se nombra para cada organización, y quien lo es
    debe estar en algún grupo de ella.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organizaciones_que_administra",
        verbose_name="usuario",
        help_text="Quién es admin.",
    )
    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.CASCADE,
        related_name="admins",
        verbose_name="organización",
        help_text="De qué organización es admin.",
    )
    desde = models.DateField(
        "desde", default=timezone.localdate, help_text="Día en que se le nombró. Se ve cuánto tiempo lleva."
    )

    class Meta:
        verbose_name = "admin de organización"
        verbose_name_plural = "admins de organización"
        constraints = [
            models.UniqueConstraint(fields=["usuario", "organizacion"], name="admin_de_organizacion_unico"),
        ]

    # Texto con el que se muestra: «Lince, admin de ORG Tajo».
    def __str__(self):
        return f"{self.usuario}, admin de {self.organizacion}"

    # Comprueba que la persona está en algún grupo de la organización.
    def clean(self):
        super().clean()
        dentro = Pertenencia.objects.filter(usuario_id=self.usuario_id, grupo__organizacion_id=self.organizacion_id)
        if not dentro.exists():
            raise ValidationError("Para ser admin de una organización hay que estar en alguno de sus grupos.")


class RelacionEntreGrupos(models.Model):
    """
    Relación libre entre dos grupos (por ejemplo, «colabora con» o «nació de»), que se ve en el grafo de
    grupos. No da ni quita permisos: solo «contiene» (el campo padre de Grupo) afecta a lo que se ve.
    """

    origen = models.ForeignKey(
        Grupo, on_delete=models.CASCADE, related_name="relaciones_salientes", verbose_name="grupo de origen",
        help_text="Grupo desde el que sale la relación.",
    )
    destino = models.ForeignKey(
        Grupo, on_delete=models.CASCADE, related_name="relaciones_entrantes", verbose_name="grupo de destino",
        help_text="Grupo al que llega la relación.",
    )
    tipo = models.CharField(
        "tipo", max_length=50, help_text="Cómo se relacionan, en pocas palabras: «colabora con», «nació de»…"
    )
    descripcion = models.TextField("descripción", blank=True, help_text="Detalles de la relación, si hacen falta.")

    class Meta:
        verbose_name = "relación entre grupos"
        verbose_name_plural = "relaciones entre grupos"
        constraints = [
            models.UniqueConstraint(fields=["origen", "destino", "tipo"], name="relacion_unica"),
            models.CheckConstraint(
                condition=~models.Q(origen=models.F("destino")),
                name="relacion_entre_grupos_distintos",
                violation_error_message="Un grupo no puede relacionarse consigo mismo.",
            ),
        ]

    # Texto con el que se muestra: «GRU Jarama colabora con GRU Segre».
    def __str__(self):
        return f"{self.origen} {self.tipo} {self.destino}"


class InvitacionDeGrupo(models.Model):
    """
    Invitación de un grupo a un grupo de otra organización para algo concreto (de momento, un proyecto
    conjunto; ver docs/diseno.md, apartado 8.1). Lo invitado se indica con un ancla (tipo + id), sin
    clave ajena, porque está en otro módulo. La acepta o rechaza el admin del grupo invitado. Aceptarla
    solo abre lo invitado: no cambia ninguna pertenencia.
    """

    # Estados de la invitación.
    PENDIENTE = "pendiente"
    ACEPTADA = "aceptada"
    RECHAZADA = "rechazada"
    RETIRADA = "retirada"
    ESTADOS = [
        (PENDIENTE, "Pendiente"),
        (ACEPTADA, "Aceptada"),
        (RECHAZADA, "Rechazada"),
        (RETIRADA, "Retirada"),
    ]

    ancla_tipo = models.CharField(
        "tipo de lo invitado",
        max_length=60,
        help_text="Qué es aquello a lo que se invita, como tipo de ancla declarado en un contrato (p. ej. «proyectos.proyecto»).",
    )
    ancla_id = models.PositiveBigIntegerField("id de lo invitado", help_text="Número de aquello a lo que se invita.")
    grupo_que_invita = models.ForeignKey(
        Grupo, on_delete=models.CASCADE, related_name="invitaciones_hechas", verbose_name="grupo que invita",
        help_text="Grupo que hace la invitación.",
    )
    grupo_invitado = models.ForeignKey(
        Grupo, on_delete=models.CASCADE, related_name="invitaciones_recibidas", verbose_name="grupo invitado",
        help_text="Grupo de otra organización al que se invita.",
    )
    invitada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+",
        verbose_name="invitada por", help_text="Quién hizo la invitación.",
    )
    mensaje = models.TextField("mensaje", blank=True, help_text="Explicación para el grupo invitado: qué se propone y por qué.")
    estado = models.CharField(
        "estado", max_length=20, choices=ESTADOS, default=PENDIENTE, help_text="En qué punto está la invitación."
    )
    creada_el = models.DateField("creada el día", default=timezone.localdate, help_text="Día en que se invitó.")
    respondida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        verbose_name="respondida por", help_text="Quién la aceptó, la rechazó o la retiró.",
    )
    respondida_el = models.DateField(
        "respondida el día", null=True, blank=True, help_text="Día en que se aceptó, se rechazó o se retiró."
    )

    class Meta:
        verbose_name = "invitación de grupo"
        verbose_name_plural = "invitaciones de grupo"
        constraints = [
            models.UniqueConstraint(
                fields=["ancla_tipo", "ancla_id", "grupo_invitado"],
                condition=models.Q(estado="pendiente"),
                name="una_invitacion_pendiente",
                violation_error_message="Ese grupo ya tiene una invitación pendiente para esto mismo.",
            ),
        ]

    # Texto con el que se muestra: «GRU Jarama invita a GRU Segre (pendiente)».
    def __str__(self):
        return f"{self.grupo_que_invita} invita a {self.grupo_invitado} ({self.get_estado_display()})"

    # Datos que acompañan a los eventos_sw de la invitación.
    def datos_del_aviso(self):
        return {
            "invitacion_id": self.pk,
            "ancla_tipo": self.ancla_tipo,
            "ancla_id": self.ancla_id,
            "grupo_invitado_id": self.grupo_invitado_id,
        }
