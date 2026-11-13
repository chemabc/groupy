"""
Configuración y contrato del módulo «audiencias».
"""

from base.contrato import Capa, ModuloConfig, Permiso


class AudienciasConfig(ModuloConfig):
    """
    Contrato del módulo «audiencias»: quién puede ver cada cosa. Declara el permiso para ajustar qué
    niveles de visibilidad ofrece una organización, y al arrancar conecta la invalidación de la caché.
    """

    name = "audiencias"
    verbose_name = "Visibilidad (audiencias)"
    capa = Capa.ORGANIZACION
    descripcion = (
        "Quién puede ver cada cosa: privado (las personas implicadas), unos grupos y sus subgrupos, toda la "
        "organización o público. Nadie de otra organización lo ve sin una invitación aceptada. Calcula una "
        "vez qué ve cada persona y lo guarda en la caché."
    )
    permisos = (
        Permiso(
            "audiencias.configurar",
            "Ajustar qué niveles de visibilidad ofrece la organización (hasta dónde subir, toda la organización, público)",
            roles=("admin_org",),
        ),
    )

    # Al arrancar: conecta las señales que invalidan la caché de audiencias.
    def ready(self):
        from . import senales

        senales.conectar()
