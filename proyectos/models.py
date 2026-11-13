"""
Tablas del módulo «proyectos» (ver docs/diseno.md, apartado 14):

- Proyecto: lo que un grupo (o una persona, si es personal) se propone hacer, con su descripción,
  fechas y estado. Cualquier proyecto puede tener subproyectos, a cualquier profundidad: cada uno guarda
  su padre y la raíz de su árbol (para cargar el árbol entero con una sola consulta).
- Tarea: algo concreto con una persona responsable (y colaboradoras), dentro de un proyecto, suelta en
  un grupo o personal. Sus estados son las columnas del kanban.

- Recurso: algo que le hace falta a un proyecto (qué, cuánto, de dónde sale y si ya se tiene), que se puede
  pedir con una petición de talentos.

Las tareas de un mismo árbol pueden esperar a otras (dependencias): mientras alguna no está hecha, la que
espera queda bloqueada sola. Proyectos y tareas guardan cuándo terminaron (para el módulo «limpieza», que
archiva lo terminado pasado un plazo y, más tarde, lo borra) y cuándo se archivaron.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Proyecto(models.Model):
    """
    Proyecto de un grupo, o personal («privado e individual»: solo lo ve quien lo crea y no se publica).
    Puede colgar de otro proyecto (subproyecto) y tener los suyos.
    """

    SIN_EMPEZAR = "sin_empezar"
    EMPEZADO = "empezado"
    CASI_ACABADO = "casi_acabado"
    FUNCIONANDO = "funcionando"
    FINALIZADO = "finalizado"
    ESTADOS = [
        (SIN_EMPEZAR, "Sin empezar"),
        (EMPEZADO, "Empezado"),
        (CASI_ACABADO, "Casi acabado"),
        (FUNCIONANDO, "Acabado y funcionando"),
        (FINALIZADO, "Finalizado"),
    ]

    titulo = models.CharField("título", max_length=150, help_text="Cómo se llama: «Huerto del barrio», «Web de la asamblea».")
    tipologia = models.ForeignKey(
        "tipologias.Tipologia", on_delete=models.PROTECT, related_name="+", verbose_name="tipo",
        help_text="Comunicación, Tecnología, Preparación de acción… (con sus campos).",
    )
    campos = models.JSONField("campos de su tipo", default=dict, blank=True, help_text="Los datos que pide su tipología.")
    objetivo_general = models.TextField("objetivo general", blank=True, help_text="Para qué sirve dentro de una estrategia mayor.")
    objetivos_especificos = models.TextField("objetivos específicos", blank=True, help_text="Qué se quiere conseguir en concreto.")
    alcance = models.TextField("alcance", blank=True, help_text="Qué entra en el proyecto y qué queda fuera.")
    riesgos = models.TextField("riesgos y plan de contingencia", blank=True, help_text="Qué puede salir mal y qué se hará entonces.")
    inicio = models.DateField("inicio", null=True, blank=True, help_text="Cuándo empieza. Opcional.")
    limite = models.DateField("fecha límite", null=True, blank=True, help_text="Cuándo tiene que estar acabado. Sale en el calendario.")
    estado = models.CharField("estado", max_length=20, choices=ESTADOS, default=SIN_EMPEZAR, help_text="En qué punto está.")
    grupo = models.ForeignKey(
        "grupos.Grupo", on_delete=models.CASCADE, null=True, blank=True, related_name="+", verbose_name="grupo que coordina",
        help_text="Grupo que lo coordina. Vacío en los proyectos personales.",
    )
    creador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="creado por", help_text="Quién lo creó."
    )
    personal = models.BooleanField("personal", default=False, help_text="Privado e individual: solo lo ve quien lo crea, ni el superadmin.")
    padre = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="hijos", verbose_name="proyecto padre",
        help_text="El proyecto del que es un subproyecto. Vacío si es un proyecto principal.",
    )
    raiz = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="+", verbose_name="proyecto raíz",
        help_text="El proyecto principal de su árbol (él mismo si no tiene padre). Sirve para cargar el árbol de una vez.",
    )
    audiencia = models.ForeignKey(
        "audiencias.Audiencia", on_delete=models.PROTECT, related_name="+", verbose_name="quién lo ve",
        help_text="Quién puede verlo (privado, el grupo, la organización…).",
    )
    visibilidad = models.CharField("visibilidad elegida", max_length=30, default="privado", help_text="La opción elegida: «privado», «grupo:0»…")
    creado = models.DateTimeField("creado", auto_now_add=True, help_text="Cuándo se creó.")
    terminado = models.DateTimeField(
        "finalizado el", null=True, blank=True, help_text="Cuándo pasó a «Finalizado». Vacío si no lo está. Desde aquí cuenta el plazo para archivarlo."
    )
    archivado = models.DateTimeField(
        "archivado el", null=True, blank=True,
        help_text="Cuándo lo archivó la limpieza (sale de las listas, con sus subproyectos y tareas). Vacío: no archivado.",
    )

    class Meta:
        verbose_name = "proyecto"
        verbose_name_plural = "proyectos"
        ordering = ["titulo", "pk"]

    # Texto con el que se muestra: su título.
    def __str__(self):
        return self.titulo

    # Comprueba que no empieza después de su fecha límite.
    def clean(self):
        super().clean()
        if self.inicio and self.limite and self.limite < self.inicio:
            raise ValidationError({"limite": "La fecha límite no puede ser anterior al inicio."})

    # Al guardar, apunta cuándo terminó (si acaba de pasar a «Finalizado»). Si se reabre, deja de estar
    # terminado y sale del archivo (vuelve a las listas).
    def save(self, *args, **kwargs):
        apuntar_fin(self, self.estado == self.FINALIZADO)
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = {*kwargs["update_fields"], "terminado", "archivado"}
        super().save(*args, **kwargs)


class Tarea(models.Model):
    """
    Algo concreto que hacer, con una persona responsable (obligatoria) y colaboradoras. Está en un
    proyecto (y la ve quien ve el proyecto), suelta en un grupo o es personal (solo la ve su dueña).
    """

    PENDIENTE = "pendiente"
    EN_CURSO = "en_curso"
    BLOQUEADA = "bloqueada"
    HECHA = "hecha"
    ESTADOS = [(PENDIENTE, "Pendiente"), (EN_CURSO, "En curso"), (BLOQUEADA, "Bloqueada"), (HECHA, "Hecha")]

    titulo = models.CharField("título", max_length=200, help_text="Qué hay que hacer: «Pedir presupuesto de la imprenta».")
    descripcion = models.TextField("descripción", blank=True, help_text="Detalles, enlaces, lo que hace falta saber.")
    proyecto = models.ForeignKey(
        Proyecto, on_delete=models.CASCADE, null=True, blank=True, related_name="tareas", verbose_name="proyecto",
        help_text="El proyecto al que pertenece. Vacío si es suelta o personal.",
    )
    grupo = models.ForeignKey(
        "grupos.Grupo", on_delete=models.CASCADE, null=True, blank=True, related_name="+", verbose_name="grupo",
        help_text="El grupo de una tarea suelta (o el del proyecto). Vacío si es personal.",
    )
    personal = models.BooleanField("personal", default=False, help_text="Solo la ve quien la crea.")
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+", verbose_name="responsable", help_text="La persona que se encarga."
    )
    colaboradores = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="+", verbose_name="colaboran", help_text="Personas que ayudan. Opcional."
    )
    creador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="creada por", help_text="Quién la creó."
    )
    limite = models.DateField("fecha límite", null=True, blank=True, help_text="Para cuándo. Sale en el calendario.")
    estado = models.CharField("estado", max_length=20, choices=ESTADOS, default=PENDIENTE, help_text="Su columna en el kanban.")
    orden = models.PositiveIntegerField("orden", default=0, help_text="Posición dentro de su columna del kanban.")
    audiencia = models.ForeignKey(
        "audiencias.Audiencia", on_delete=models.PROTECT, null=True, blank=True, related_name="+", verbose_name="quién la ve",
        help_text="Solo en las sueltas y personales: quién la ve. Las de un proyecto las ve quien ve el proyecto.",
    )
    visibilidad = models.CharField("visibilidad elegida", max_length=30, default="privado", help_text="La opción elegida (en las sueltas).")
    creada = models.DateTimeField("creada", auto_now_add=True, help_text="Cuándo se creó.")
    actualizada = models.DateTimeField("actualizada", auto_now=True, help_text="Cuándo cambió por última vez.")
    espera_a = models.ManyToManyField(
        "self", symmetrical=False, blank=True, related_name="desbloquea", verbose_name="espera a",
        help_text="Tareas del mismo proyecto (o de su árbol) que tienen que estar hechas antes. Mientras no lo están, esta queda bloqueada.",
    )
    bloqueo_automatico = models.BooleanField(
        "bloqueada por dependencias", default=False,
        help_text="Si la bloqueó la aplicación por esperar a otras tareas: cuando estén hechas, vuelve sola a «Pendiente».",
    )
    terminado = models.DateTimeField(
        "hecha el", null=True, blank=True, help_text="Cuándo pasó a «Hecha». Vacío si no lo está. Desde aquí cuenta el plazo para archivarla."
    )
    archivado = models.DateTimeField(
        "archivada el", null=True, blank=True,
        help_text="Cuándo la archivó la limpieza (solo las sueltas y personales; las de un proyecto siguen al proyecto). Vacío: no archivada.",
    )

    class Meta:
        verbose_name = "tarea"
        verbose_name_plural = "tareas"
        ordering = ["estado", "orden", "pk"]

    # Texto con el que se muestra: su título.
    def __str__(self):
        return self.titulo

    # Al guardar, apunta cuándo terminó (si acaba de pasar a «Hecha»). Si se reabre, deja de estar
    # terminada y sale del archivo.
    def save(self, *args, **kwargs):
        apuntar_fin(self, self.estado == self.HECHA)
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = {*kwargs["update_fields"], "terminado", "archivado"}
        super().save(*args, **kwargs)



class Recurso(models.Model):
    """
    Algo que le hace falta a un proyecto: material, dinero, un local, una furgoneta… Con cuánto, de dónde
    sale y si ya se tiene. Se puede pedir a un grupo con una petición de talentos.
    """

    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="recursos", verbose_name="proyecto", help_text="El proyecto que lo necesita.")
    nombre = models.CharField("qué", max_length=60, help_text="Qué hace falta: «Furgoneta», «Mangueras», «Local para el taller».")
    cantidad = models.CharField("cuánto", max_length=60, blank=True, help_text="Cuánto o cuántos, como se diga mejor: «3», «200 €», «un fin de semana».")
    origen = models.CharField("de dónde sale", max_length=200, blank=True, help_text="Quién lo pone, dónde se consigue o con qué se paga.")
    conseguido = models.BooleanField("ya se tiene", default=False, help_text="Si ya está conseguido.")
    peticion = models.ForeignKey(
        "talentos.PeticionDeTalentos", on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="petición de talentos",
        help_text="La petición de talentos con la que se ha pedido, si se ha pedido así.",
    )
    creado = models.DateTimeField("creado", auto_now_add=True, help_text="Cuándo se apuntó.")

    class Meta:
        verbose_name = "recurso"
        verbose_name_plural = "recursos"
        ordering = ["conseguido", "nombre", "pk"]

    # Texto con el que se muestra: qué y cuánto.
    def __str__(self):
        return f"{self.nombre} ({self.cantidad})" if self.cantidad else self.nombre


# Pone al día «terminado» y «archivado» de un proyecto o una tarea antes de guardarlo: si está terminado y
# no tenía fecha, la de ahora; si no lo está, vacías las dos. La llaman los save() de Proyecto y Tarea.
#   - objeto: el proyecto o la tarea.
#   - acabado: si su estado es el de terminado («Finalizado» o «Hecha»).
def apuntar_fin(objeto, acabado):
    if acabado:
        objeto.terminado = objeto.terminado or timezone.now()
    else:
        objeto.terminado = None
        objeto.archivado = None
