"""
Configuración y contrato del módulo «permisos».
"""

from django.db.models.signals import post_migrate

from base.contrato import Capa, ModuloConfig, Permiso


class PermisosConfig(ModuloConfig):
    """
    Contrato del módulo «permisos». Declara los permisos para repartir cometidos y dar excepciones, y al
    arrancar conecta la invalidación de la caché y la sincronización de los permisos por defecto.
    """

    name = "permisos"
    verbose_name = "Roles y permisos"
    capa = Capa.ORGANIZACION
    descripcion = (
        "Roles (los del sistema y los que cree el superadmin), qué permisos tiene cada rol, cometidos de "
        "cada persona en cosas concretas y excepciones individuales. Calcula qué puede hacer cada persona "
        "y lo guarda en la caché."
    )
    permisos = (
        Permiso(
            "permisos.asignar_cometidos",
            "Repartir cometidos (facilitación, toma de acta…) en las cosas del grupo",
            roles=("admin_grupo", "admin_org"),
        ),
        Permiso(
            "permisos.dar_excepciones",
            "Dar o quitar un permiso suelto a una persona del grupo",
            roles=("admin_org",),
        ),
    )

    # Al arrancar: conecta las señales que invalidan la caché y, después de cada «migrate», crea los roles
    # del sistema que falten y da a los permisos nuevos sus roles por defecto. Django lanza la misma señal
    # cuando las pruebas con servidor de verdad vacían la base, así que también se reparan solos.
    def ready(self):
        from . import senales
        from .servicios import sincronizar_permisos

        senales.conectar()
        # weak=False: Django guarda las conexiones de forma «débil» y una función creada aquí mismo (lambda)
        # desaparecería al salir de este método.
        post_migrate.connect(
            lambda **resto: sincronizar_permisos(), sender=self, weak=False, dispatch_uid="permisos.sincronizar"
        )
