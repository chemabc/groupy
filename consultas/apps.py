"""
Configuración y contrato del módulo «consultas».
"""

from base.contrato import (
    Ancla,
    Ayuda,
    Capa,
    Colgante,
    DatosDeEjemplo,
    Emision,
    EntradaDeMenu,
    FuenteDeCalendario,
    ModuloConfig,
    Permiso,
    TareaDiaria,
    TarjetaDeInicio,
    TipoDeSolicitud,
)


class ConsultasConfig(ModuloConfig):
    """
    Contrato del módulo «consultas»: votaciones con un formulario (respuesta única, múltiple o abierta),
    quién vota, fechas, cuándo y quién ve los resultados y si se puede cambiar el voto (docs/diseno.md,
    apartado 12). Una persona, un voto, secreto. Al cerrarse, el resultado pasa al registro de decisiones.
    """

    name = "consultas"
    verbose_name = "Consultas"
    capa = Capa.FUNCIONAL
    datos_de_ejemplo = DatosDeEjemplo(crear="consultas.ejemplos.crear", borrar="consultas.ejemplos.borrar")
    descripcion = (
        "Votaciones de los grupos: un formulario con preguntas de respuesta única, múltiple o abierta, quién vota, "
        "cuándo se abre y se cierra, cuándo y quién ve los resultados y si se puede cambiar el voto. El voto es "
        "secreto. Al cerrarse, el resultado pasa al registro de decisiones."
    )
    # Lo que cuelga de una consulta (sus documentos de contexto) queda congelado desde que se abre la votación.
    anclas = (Ancla("consultas.consulta", "consultas.Consulta", "Una consulta (votación)", congela="consultas.servicios.congela"),)
    permisos = (
        Permiso("consultas.crear", "Crear consultas (votaciones) del grupo sin pedir apoyos", roles=("admin_grupo", "admin_org")),
        Permiso("consultas.proponer", "Proponer consultas al grupo (se abren con apoyos)", roles=("usuario", "admin_grupo", "admin_org")),
    )
    solicitudes = (
        TipoDeSolicitud("consultas.abrir", "Abrir una consulta", resolver="consultas.servicios.aceptar", apoyos=2, dias=15, basta_el_superadmin=True),
    )
    emite = (
        Emision(
            "consultas.cerrada",
            "Se ha cerrado una consulta con su resultado. Datos: texto, forma, detalle, grupo_id, audiencia_id, origen_tipo, origen_id, enlace, tomada.",
        ),
    )
    tareas_diarias = (
        TareaDiaria("consultas.cerrar", "Da por cerradas las consultas cuya fecha de cierre ha pasado (y su resultado pasa a decisiones).", "consultas.servicios.cerrar_vencidas"),
    )
    fuentes_de_calendario = (
        FuenteDeCalendario("consultas.cierres", "Cierres de consultas", "consultas.servicios.fechas", color="#0369a2"),
    )
    tarjetas_de_inicio = (
        TarjetaDeInicio("consultas.por_votar", "Consultas por votar", "consultas.servicios.por_votar", icono="☷", color="#0369a2"),
    )
    colgantes = (
        Colgante(
            "consultas.consultas", "Consultas", ("eventos.evento", "proyectos.proyecto", "debates.debate"), "consultas.servicios.colgantes",
            crear="consultas:nueva", texto_crear="+ Consulta",
        ),
    )
    menu = (
        EntradaDeMenu(
            codigo="consultas.consultas", nombre="Consultas", url="consultas:lista", icono="☷", color="#0369a2",
            otras_rutas=("consultas:nueva", "consultas:consulta"),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="consultas.consultas",
            titulo="Consultas",
            texto=(
                "Las votaciones de tus grupos. La administración las crea directamente; cualquier miembro puede "
                "proponer una: le pone las preguntas, pide apoyos y, cuando los consigue, se abre como las demás.\n\n"
                "Cada una dice quién vota, cuándo se abre y se cierra, cuándo se ven los "
                "resultados y si se puede cambiar el voto (si no se puede, te avisa antes de votar).\n\n"
                "Una persona, un voto. El voto es secreto: se guarda quién ha votado por un lado y qué se ha votado por "
                "otro, sin nada que los una. El desglose por grupos solo sale con 10 votos o más. Al cerrarse, el "
                "resultado pasa al registro de decisiones."
            ),
            ejemplo="La administración de GRU Henares pregunta «¿Qué día hacemos la asamblea?» con tres respuestas; se cierra el domingo.",
        ),
    )
