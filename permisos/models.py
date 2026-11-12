"""
Tablas del módulo «permisos»: roles, qué permisos tiene cada rol, cometidos de cada persona y
excepciones individuales. Ver docs/diseno.md, apartados 3.5 y 5.

Los permisos en sí no son una tabla: los declara cada módulo en su contrato (base/contrato.py, Permiso)
y están en el registro. Aquí se guarda solo qué rol tiene cada uno, que el superadmin puede cambiar.
"""

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class Rol(models.Model):
    """
    Rol: nivel de poder de una persona en un grupo o en una organización. Los del sistema (usuario,
    admin_grupo, admin_org) existen siempre; el superadmin puede crear otros (por ejemplo, «Tesorería»)
    y decidir qué permisos tiene cada uno. El superadmin no es un rol: es una marca del usuario y puede
    hacerlo todo.
    """

    # Dónde se tiene el rol.
    GRUPO = "grupo"
    ORGANIZACION = "organizacion"
    NIVELES = [(GRUPO, "En un grupo"), (ORGANIZACION, "En una organización")]

    codigo = models.CharField(
        "código",
        max_length=40,
        primary_key=True,
        validators=[RegexValidator(r"^[a-z][a-z0-9_]*$", "Solo minúsculas sin tildes, números y «_», empezando por letra.")],
        help_text="Nombre interno, sin espacios ni tildes (p. ej. «tesoreria»). No se puede cambiar después.",
    )
    nombre = models.CharField("nombre", max_length=60, help_text="Nombre visible del rol (p. ej. «Tesorería»).")
    descripcion = models.TextField("descripción", blank=True, help_text="Para qué sirve el rol, en lenguaje llano.")
    nivel = models.CharField(
        "nivel",
        max_length=20,
        choices=NIVELES,
        default=GRUPO,
        help_text=(
            "Si se tiene en un grupo (y solo en ese grupo) o en una organización (en todos sus grupos). Los "
            "roles personalizados, de momento, son de grupo."
        ),
    )
    del_sistema = models.BooleanField(
        "del sistema",
        default=False,
        help_text="Los roles del sistema (usuario, admin del grupo, admin de la organización) no se pueden borrar.",
    )

    class Meta:
        verbose_name = "rol"
        verbose_name_plural = "roles"
        ordering = ["-del_sistema", "nombre"]

    # Texto con el que se muestra el rol: su nombre.
    def __str__(self):
        return self.nombre


class PermisoDeRol(models.Model):
    """Que un rol tiene un permiso. El permiso se nombra por su código, declarado en algún contrato."""

    rol = models.ForeignKey(
        Rol, on_delete=models.CASCADE, related_name="permisos", verbose_name="rol", help_text="Rol que tiene el permiso."
    )
    permiso = models.CharField(
        "permiso", max_length=80, help_text="Código del permiso, tal como lo declara su módulo (p. ej. «grupos.invitar»)."
    )

    class Meta:
        verbose_name = "permiso de un rol"
        verbose_name_plural = "permisos de los roles"
        constraints = [models.UniqueConstraint(fields=["rol", "permiso"], name="permiso_de_rol_unico")]

    # Texto con el que se muestra: «Usuario: grupos.invitar».
    def __str__(self):
        return f"{self.rol}: {self.permiso}"


class PermisoConocido(models.Model):
    """
    Permisos que ya se han visto alguna vez. Sirve para dar los roles por defecto de un permiso solo la
    primera vez que aparece: si después el superadmin se lo quita a un rol, no vuelve a aparecer solo.
    """

    codigo = models.CharField("código", max_length=80, primary_key=True, help_text="Código del permiso.")
    visto_el = models.DateField("visto el día", default=timezone.localdate, help_text="Día en que apareció por primera vez.")

    class Meta:
        verbose_name = "permiso conocido"
        verbose_name_plural = "permisos conocidos"

    # Texto con el que se muestra: su código.
    def __str__(self):
        return self.codigo


class Cometido(models.Model):
    """
    Cometido de una persona en algo concreto: la facilitación de un debate, la toma de acta de una
    reunión, la coordinación de un proyecto… Lo concreto se indica con un ancla (tipo + id). Se guarda
    también el grupo donde vive eso, para que sus miembros puedan ver quién tiene cada cometido.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cometidos", verbose_name="usuario",
        help_text="Quién lo tiene.",
    )
    codigo = models.CharField(
        "cometido", max_length=80, help_text="Código del cometido, tal como lo declara su módulo (p. ej. «debates.facilitacion»)."
    )
    ancla_tipo = models.CharField(
        "tipo de aquello", max_length=60, help_text="Tipo de ancla de aquello en lo que se tiene (p. ej. «debates.debate»)."
    )
    ancla_id = models.PositiveBigIntegerField("id de aquello", help_text="Número de aquello en lo que se tiene.")
    grupo = models.ForeignKey(
        "grupos.Grupo", on_delete=models.CASCADE, null=True, blank=True, related_name="cometidos", verbose_name="grupo",
        help_text="Grupo donde vive aquello. Sus miembros pueden ver este cometido. Vacío si no es de ningún grupo.",
    )
    desde = models.DateField("desde", default=timezone.localdate, help_text="Día desde el que lo tiene.")

    class Meta:
        verbose_name = "cometido"
        verbose_name_plural = "cometidos"
        constraints = [
            models.UniqueConstraint(fields=["usuario", "codigo", "ancla_tipo", "ancla_id"], name="cometido_unico"),
        ]
        indexes = [models.Index(fields=["ancla_tipo", "ancla_id"], name="cometido_por_ancla")]

    # Texto con el que se muestra: «Lince: debates.facilitacion en debates.debate 7».
    def __str__(self):
        return f"{self.usuario}: {self.codigo} en {self.ancla_tipo} {self.ancla_id}"


class ExcepcionDePermiso(models.Model):
    """
    Excepción individual: dar o quitar un permiso a una persona en un grupo concreto, por encima de lo que
    digan sus roles. Solo vale en ese grupo (no se hereda). Quitar gana a dar.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="excepciones_de_permiso",
        verbose_name="usuario", help_text="A quién se le da o se le quita.",
    )
    grupo = models.ForeignKey(
        "grupos.Grupo", on_delete=models.CASCADE, related_name="excepciones_de_permiso", verbose_name="grupo",
        help_text="En qué grupo vale la excepción.",
    )
    permiso = models.CharField("permiso", max_length=80, help_text="Código del permiso.")
    concede = models.BooleanField(
        "concede", default=True, help_text="Marcado: se le da el permiso. Sin marcar: se le quita, aunque su rol lo tenga."
    )
    motivo = models.TextField("motivo", help_text="Por qué se hace la excepción. Queda a la vista del grupo.")
    creada_el = models.DateField("creada el día", default=timezone.localdate, help_text="Día en que se creó.")

    class Meta:
        verbose_name = "excepción de permiso"
        verbose_name_plural = "excepciones de permiso"
        constraints = [
            models.UniqueConstraint(fields=["usuario", "grupo", "permiso"], name="excepcion_unica"),
        ]

    # Texto con el que se muestra: «Lince: + grupos.invitar en GRU Henares».
    def __str__(self):
        return f"{self.usuario}: {'+' if self.concede else '−'} {self.permiso} en {self.grupo}"
