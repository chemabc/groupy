"""
Configuración y contrato del módulo «proyectos».
"""

from base.contrato import (
    Ancla,
    Ayuda,
    Capa,
    Cometido,
    DatosDeEjemplo,
    Emision,
    EntradaDeMenu,
    FuenteDeCalendario,
    Limpiable,
    ModuloConfig,
    Permiso,
    TipoDeAviso,
    Vista,
)


class ProyectosConfig(ModuloConfig):
    """
    Contrato del módulo «proyectos»: proyectos de los grupos y personales, con subproyectos a cualquier
    profundidad, y tareas (en un proyecto, sueltas en un grupo o personales) con responsable,
    colaboradoras, fecha límite, kanban y dependencias (que bloquean solas); y recursos de cada proyecto.
    """

    name = "proyectos"
    verbose_name = "Proyectos"
    capa = Capa.FUNCIONAL
    descripcion = (
        "Proyectos de los grupos y personales, con subproyectos a cualquier profundidad, su tipología, objetivos, "
        "alcance, riesgos, fechas y estado; cometidos de coordinación, documentación y comunicación; y tareas con "
        "responsable, colaboradoras y fecha límite, en lista y en kanban."
    )
    datos_de_ejemplo = DatosDeEjemplo(crear="proyectos.ejemplos.crear", borrar="proyectos.ejemplos.borrar")
    anclas = (Ancla("proyectos.proyecto", "proyectos.Proyecto", "Un proyecto (o subproyecto)"),)
    permisos = (
        Permiso("proyectos.crear", "Crear proyectos y tareas sueltas en el grupo", roles=("usuario", "admin_grupo", "admin_org")),
    )
    cometidos = (
        Cometido("proyectos.coordinacion", "Coordinación", "Coordina el proyecto: lo gestiona (y sus subproyectos) igual que quien lo creó."),
        Cometido("proyectos.documentacion", "Documentación", "Recoge y ordena la documentación del proyecto."),
        Cometido("proyectos.comunicacion", "Comunicación", "Cuenta hacia fuera cómo va el proyecto."),
    )
    emite = (
        Emision("proyectos.tarea_asignada", "Se ha encargado una tarea a alguien. Datos: tarea_id."),
        Emision("proyectos.tarea_desbloqueada", "Una tarea ya no espera a nada (todas sus dependencias están hechas). Datos: tarea_id."),
    )
    avisos = (
        TipoDeAviso("proyectos.tarea_asignada", "Me encargan una tarea", "proyectos", "proyectos.tarea_asignada", "proyectos.avisos.tarea_asignada"),
        TipoDeAviso(
            "proyectos.tarea_desbloqueada", "Una tarea mía ya no espera a nada", "proyectos", "proyectos.tarea_desbloqueada",
            "proyectos.avisos.tarea_desbloqueada",
        ),
    )
    limpiables = (
        Limpiable(
            "proyectos.proyecto", "proyectos.Proyecto", "Proyectos finalizados (con sus subproyectos y tareas)",
            terminados="proyectos.limpieza.proyectos", ficha="proyectos:proyecto",
        ),
        Limpiable(
            "proyectos.tarea", "proyectos.Tarea", "Tareas hechas (sueltas y personales)",
            terminados="proyectos.limpieza.tareas", ficha="proyectos:tarea",
        ),
    )
    fuentes_de_calendario = (
        FuenteDeCalendario("proyectos.proyectos", "Proyectos", "proyectos.calendario.proyectos", color="#4338ca", mover="proyectos.calendario.mover_proyecto"),
        FuenteDeCalendario("proyectos.tareas", "Tareas", "proyectos.calendario.tareas", color="#0f766e", mover="proyectos.calendario.mover_tarea"),
    )
    menu = (
        EntradaDeMenu(
            codigo="proyectos.seccion",
            nombre="Proyectos",
            url="proyectos:proyectos",
            icono="◆",
            color="#4338ca",
            otras_rutas=("proyectos:proyecto", "proyectos:editar", "proyectos:kanban", "proyectos:tarea"),
            subsecciones=(
                EntradaDeMenu(
                    codigo="proyectos.proyectos", nombre="Proyectos", url="proyectos:proyectos", icono="❏", color="#6d28d9",
                    vistas=(
                        Vista("De mis grupos", "proyectos:proyectos"), Vista("Personales", "proyectos:personales"),
                        Vista("Nuevo", "proyectos:nuevo"),
                    ),
                ),
                EntradaDeMenu(
                    codigo="proyectos.tareas", nombre="Mis tareas", url="proyectos:tareas", icono="☑", color="#b91c1c",
                    vistas=(Vista("Lista", "proyectos:tareas"), Vista("Kanban", "proyectos:tareas_kanban"), Vista("Nueva", "proyectos:nueva_tarea")),
                ),
            ),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="proyectos.seccion",
            titulo="Proyectos",
            texto=(
                "Lo que se proponen hacer tus grupos, y tus proyectos personales. Cada proyecto puede tener "
                "subproyectos (y estos los suyos), y tareas con una persona responsable."
            ),
        ),
        Ayuda(
            seccion="proyectos.proyectos",
            titulo="Proyectos",
            texto=(
                "Los proyectos que puedes ver, en árbol: debajo de cada uno, sus subproyectos. Los personales "
                "(«privado e individual») solo los ves tú, ni el superadmin. Pulsa uno para ver su ficha, sus "
                "tareas y su kanban."
            ),
        ),
        Ayuda(
            seccion="proyectos.tareas",
            titulo="Mis tareas",
            texto=(
                "Las tareas de las que eres responsable o en las que colaboras. En el kanban, arrastra una tarea "
                "de columna para cambiar su estado: pendiente, en curso, bloqueada, hecha."
            ),
        ),
    )
