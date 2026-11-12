"""
Configuración y contrato del módulo «grupos».
"""

from base.contrato import Capa, DatosDeEjemplo, Emision, ModuloConfig


class GruposConfig(ModuloConfig):
    """
    Contrato del módulo «grupos». Avisa con eventos_sw cuando cambia la estructura de los grupos o lo que
    cada persona es en ellos, para que «permisos» y «audiencias» rehagan sus cálculos, y cuando se
    invita a un grupo de otra organización a algo.
    """

    name = "grupos"
    verbose_name = "Organizaciones y grupos"
    capa = Capa.ORGANIZACION
    descripcion = (
        "Organizaciones, grupos y subgrupos (con su tabla de cierre), pertenencias con su rol y su "
        "asamblea base, admin de cada organización, relaciones libres entre grupos e invitaciones a "
        "grupos de otras organizaciones."
    )
    emite = (
        Emision(
            "grupos.estructura_cambiada",
            "Se ha creado un grupo o ha cambiado de grupo padre. Datos: grupo_id.",
        ),
        Emision(
            "grupos.pertenencias_cambiadas",
            "Una persona ha entrado en un grupo, ha salido, ha cambiado de rol o de asamblea base, o la "
            "han nombrado (o dejado de nombrar) admin de una organización. Datos: usuario_id.",
        ),
        Emision(
            "grupos.invitacion_creada",
            "Un grupo ha invitado a un grupo de otra organización a algo (un proyecto). Datos: "
            "invitacion_id, ancla_tipo, ancla_id, grupo_invitado_id.",
        ),
        Emision(
            "grupos.invitacion_aceptada",
            "El grupo invitado ha aceptado la invitación. Datos: los de grupos.invitacion_creada.",
        ),
        Emision(
            "grupos.invitacion_rechazada",
            "El grupo invitado ha rechazado la invitación. Datos: los de grupos.invitacion_creada.",
        ),
        Emision(
            "grupos.invitacion_retirada",
            "El grupo que invitó ha retirado la invitación. Datos: los de grupos.invitacion_creada.",
        ),
    )
    datos_de_ejemplo = DatosDeEjemplo(crear="grupos.ejemplos.crear", borrar="grupos.ejemplos.borrar")
