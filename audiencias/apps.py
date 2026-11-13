"""
Configuración y contrato del módulo «audiencias».
"""

from base.contrato import Ayuda, Capa, EntradaDeMenu, ModuloConfig, Permiso, Vista


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

    # «Configuración → Visibilidad» (13 de noviembre de 2026), colgada de la sección de «tipologias».
    menu = (
        EntradaDeMenu(
            codigo="audiencias.visibilidad",
            nombre="Visibilidad",
            url="audiencias:visibilidad",
            icono="◎",
            color="#0369a1",
            permiso="audiencias.configurar",
            dentro_de="tipologias.configuracion",
            orden=20,
            vistas=(Vista("Por organización", "audiencias:visibilidad"),),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="audiencias.visibilidad",
            titulo="Visibilidad",
            texto=(
                "Quien publica algo elige quién lo ve. Todo nace privado (solo las personas implicadas). Puede "
                "abrirse a su grupo con sus subgrupos y, subiendo, al grupo padre, al abuelo… (cada nivel "
                "incluye todos los subgrupos de ese grupo); a unos grupos concretos; a toda la organización; o "
                "al público (cualquiera, sin cuenta y sin alias).\n\n"
                "Aquí cada organización decide cuáles de esas opciones ofrece: hasta qué altura se puede subir, "
                "si se permite «toda la organización» y si se permite lo público. Sin ajustar, vale la más "
                "cerrada: hasta el grupo padre, sin toda la organización y sin lo público. Lo ya publicado no "
                "cambia.\n\n"
                "Nada llega nunca a otra organización sin una invitación hecha y aceptada por quien tiene permiso."
            ),
        ),
    )

    # Al arrancar: conecta las señales que invalidan la caché de audiencias.
    def ready(self):
        from . import senales

        senales.conectar()
