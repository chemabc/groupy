"""
Tablas del módulo «usuarios»: la cuenta con seudónimo con la que cada persona actúa en la plataforma.

La identidad real (nombre, correo oficial) nunca está aquí: solo existe en la bóveda (ver
docs/registro-y-validacion.md). Por eso el usuario no tiene nombre, apellidos ni correo oficial, y su
fecha de alta es solo un día, nunca una hora.
"""

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from base.preferencias import opciones
from base.tablas import normalizar

# Forma que debe tener un alias: de 3 a 30 letras (también con tilde o ñ), números, espacios, puntos,
# guiones y guiones bajos. Así no caben direcciones, símbolos raros ni código.
validar_forma_del_alias = RegexValidator(
    r"^[\w .\-]{3,30}$",
    "El alias debe tener de 3 a 30 caracteres: letras, números, espacios, puntos y guiones.",
)


# Deja un alias en su forma limpia: sin espacios al principio ni al final, y con un solo espacio entre
# palabras («  Lince   rojo » → «Lince rojo»). Se aplica antes de guardar y antes de buscar.
#   - alias: el alias tal como se ha escrito.
def limpiar_alias(alias):
    return " ".join(alias.split())


# Forma con la que se comparan los alias: limpia, sin tildes y en minúsculas («Águila» → «aguila»). Dos
# alias con la misma forma se consideran el mismo, para que nadie pueda suplantar a otra persona con un
# alias casi igual. También sirve para entrar escribiendo el alias sin tildes.
#   - alias: el alias tal como se ha escrito.
def normalizar_alias(alias):
    return normalizar(limpiar_alias(alias))


class GestorDeUsuarios(BaseUserManager):
    """
    Forma de crear y buscar usuarios que necesita Django (el «manager»). La usan la orden
    «createsuperuser», las pruebas y los datos de ejemplo.
    """

    # Crea un usuario con su alias y su contraseña (cifrada). Devuelve el usuario ya guardado.
    #   - alias: seudónimo con el que entra y con el que le ven los demás.
    #   - password: contraseña en claro; se guarda cifrada.
    #   - otros: más campos del usuario (es_superadmin, correo_alternativo…).
    def create_user(self, alias, password=None, **otros):
        usuario = self.model(alias=alias, **otros)
        usuario.set_password(password)
        usuario.full_clean(exclude=["password"])
        usuario.save(using=self._db)
        return usuario

    # Crea un superadmin. La usa la orden «python manage.py createsuperuser».
    def create_superuser(self, alias, password=None, **otros):
        otros["es_superadmin"] = True
        return self.create_user(alias, password, **otros)

    # Busca al usuario por su alias, sin tener en cuenta mayúsculas, tildes ni espacios de más. Django
    # la usa al iniciar sesión: así «aguila» entra en la cuenta de «Águila».
    #   - alias: lo escrito en el cuadro «Alias» de la pantalla de entrada.
    def get_by_natural_key(self, alias):
        return self.get(alias_normalizado=normalizar_alias(alias))


class Usuario(AbstractBaseUser):
    """
    Usuario: la persona dentro de la plataforma, siempre con seudónimo. Su nombre visible es su alias.
    Guarda también sus preferencias de presentación (tema, letra y densidad).
    """

    alias = models.CharField(
        "alias",
        max_length=30,
        # Django lo exige al campo con el que se entra. La regla de verdad, más estricta, es la de
        # alias_normalizado.
        unique=True,
        validators=[validar_forma_del_alias],
        help_text=(
            "Seudónimo con el que entras y con el que te ven las demás personas. No pongas tu nombre "
            "real. No puede coincidir con otro, aunque cambien las mayúsculas o las tildes."
        ),
    )
    alias_normalizado = models.CharField(
        "alias normalizado",
        max_length=30,
        unique=True,
        editable=False,
        help_text=(
            "El alias sin tildes y en minúsculas. Se calcula solo y no puede repetirse: así «María» y "
            "«maria» no pueden existir a la vez."
        ),
    )
    # Se redeclara para darle explicación; Django la guarda cifrada.
    password = models.CharField(
        "contraseña",
        max_length=128,
        help_text="La contraseña, cifrada con Argon2. Nadie, ni el superadmin, puede leerla.",
    )
    # Se redeclara para darle explicación. Django la pone al día cada vez que la persona inicia sesión.
    last_login = models.DateTimeField(
        "último inicio de sesión",
        blank=True,
        null=True,
        help_text="Cuándo inició sesión por última vez.",
    )
    correo_alternativo = models.EmailField(
        "correo alternativo",
        blank=True,
        help_text=(
            "Correo para avisos y para recuperar la cuenta. Es opcional y conviene que no sea el oficial "
            "ni lleve tu nombre real."
        ),
    )
    es_superadmin = models.BooleanField(
        "superadmin",
        default=False,
        help_text="Si administra toda la plataforma (ver docs/diseno.md, apartado 5.1).",
    )
    activo = models.BooleanField(
        "activo",
        default=True,
        help_text="Si puede iniciar sesión. Una cuenta desactivada se conserva, pero no puede entrar.",
    )
    # Cómo se creó la cuenta.
    ALTA_DIRECTA = "directa"
    CON_PASE = "pase"
    ORIGENES = [(ALTA_DIRECTA, "Alta directa (sin bóveda)"), (CON_PASE, "Con pase (persona validada en la bóveda)")]
    origen = models.CharField(
        "origen",
        max_length=10,
        choices=ORIGENES,
        default=ALTA_DIRECTA,
        help_text=(
            "Cómo se creó: a mano o importada por el superadmin (alta directa), o con un pase de la bóveda "
            "(registro real, fase 8). Nunca dice qué persona hay detrás."
        ),
    )
    activado_el = models.DateField(
        "activado el día",
        default=timezone.localdate,
        help_text=(
            "Día en que se activó la cuenta. Solo el día, nunca la hora, para que no se pueda emparejar "
            "con el alta en la bóveda."
        ),
    )
    tema = models.CharField(
        "tema",
        max_length=10,
        choices=opciones("tema"),
        blank=True,
        help_text="Colores de la pantalla. Vacío: el del sistema operativo.",
    )
    letra = models.CharField(
        "letra",
        max_length=10,
        choices=opciones("letra"),
        default="normal",
        help_text="Tamaño de la letra.",
    )
    densidad = models.CharField(
        "densidad",
        max_length=15,
        choices=opciones("densidad"),
        default="comoda",
        help_text="Cuánto espacio se deja entre los elementos de la pantalla.",
    )

    objects = GestorDeUsuarios()

    # Campo con el que se inicia sesión.
    USERNAME_FIELD = "alias"
    # Campo de correo que usa Django cuando necesita escribir a alguien.
    EMAIL_FIELD = "correo_alternativo"
    # Campos que pide «createsuperuser» además del alias y la contraseña: ninguno.
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["alias_normalizado"]

    # Texto con el que se muestra el usuario en cualquier sitio: su alias.
    def __str__(self):
        return self.alias

    # Comprueba el usuario antes de guardarlo desde un formulario (también desde la trastienda): limpia
    # el alias y avisa si ya hay otro igual sin contar mayúsculas ni tildes.
    def clean(self):
        super().clean()
        self.alias = limpiar_alias(self.alias)
        self.alias_normalizado = normalizar_alias(self.alias)
        repetidos = Usuario.objects.filter(alias_normalizado=self.alias_normalizado).exclude(pk=self.pk)
        if repetidos.exists():
            raise ValidationError({"alias": "Ya hay un usuario con ese alias (sin contar mayúsculas ni tildes)."})

    # Guarda el usuario, calculando antes el alias normalizado. Así queda bien aunque no se llame a
    # clean() (por ejemplo, desde una orden o una prueba).
    def save(self, *args, **kwargs):
        self.alias = limpiar_alias(self.alias)
        self.alias_normalizado = normalizar_alias(self.alias)
        super().save(*args, **kwargs)

    # Lo que Django llama «is_active» es aquí «activo». Lo consulta al iniciar sesión.
    @property
    def is_active(self):
        return self.activo

    # La trastienda (panel de Django) solo deja entrar al superadmin.
    @property
    def is_staff(self):
        return self.activo and self.es_superadmin

    # En la trastienda, el superadmin puede hacerlo todo.
    @property
    def is_superuser(self):
        return self.is_staff

    # Permisos de la trastienda: todos para el superadmin, ninguno para los demás. Los permisos de la
    # aplicación no van por aquí, sino por el módulo «permisos».
    def has_perm(self, permiso, objeto=None):
        return self.is_staff

    # Si puede ver una sección de la trastienda: igual que has_perm.
    def has_module_perms(self, etiqueta):
        return self.is_staff
