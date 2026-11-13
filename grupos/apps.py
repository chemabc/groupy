"""
Configuración y contrato del módulo «grupos».
"""

from base.contrato import Capa, DatosDeEjemplo, Emision, ModuloConfig, Permiso


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
    permisos = (
        Permiso("grupos.editar_grupo", "Editar los datos del grupo", roles=("admin_grupo", "admin_org")),
        Permiso("grupos.crear_subgrupo", "Crear subgrupos dentro del grupo", roles=("admin_grupo", "admin_org")),
        Permiso("grupos.admitir", "Admitir personas en el grupo o sacarlas de él", roles=("admin_grupo", "admin_org")),
        Permiso("grupos.nombrar_admin_grupo", "Nombrar o quitar admins del grupo", roles=("admin_org",)),
        Permiso("grupos.editar_organizacion", "Editar los datos de la organización", roles=("admin_org",)),
        # Invitar a otra organización abre una puerta entre las dos: solo con privilegios (13 de noviembre
        # de 2026, a petición de la persona usuaria).
        Permiso(
            "grupos.invitar",
            "Invitar a un grupo de otra organización a algo del grupo",
            roles=("admin_grupo", "admin_org"),
        ),
        Permiso(
            "grupos.responder_invitacion",
            "Aceptar o rechazar las invitaciones de otras organizaciones al grupo",
            roles=("admin_grupo",),
        ),
    )
    datos_de_ejemplo = DatosDeEjemplo(crear="grupos.ejemplos.crear", borrar="grupos.ejemplos.borrar")
