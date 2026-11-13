"""
Configuración y contrato del módulo «eventos».
"""

from base.contrato import (
    Ancla,
    Ayuda,
    Capa,
    Cometido,
    Emision,
    EntradaDeMenu,
    FuenteDeCalendario,
    ModuloConfig,
    Permiso,
    TipoDeAviso,
    TipoDeSolicitud,
    Vista,
)


class EventosConfig(ModuloConfig):
    """
    Contrato del módulo «eventos»: actividades con fecha que convoca un grupo (reuniones, acciones,
    recaudatorios…), con «¿Vas a ir?», cometidos y cartel. Las reuniones se convocan con una solicitud con
    apoyos (2 en el propio grupo, 5 en el padre, 10 en el abuelo).
    """

    name = "eventos"
    verbose_name = "Eventos"
    capa = Capa.FUNCIONAL
    descripcion = (
        "Eventos de los grupos: reuniones (con solicitud de apoyos), acciones, recaudatorios y genéricos, con "
        "los campos de su tipología, quién lo ve, modalidad y lugar, cartel, texto para las redes, «¿Vas a "
        "ir?» y cometidos."
    )
    anclas = (Ancla("eventos.evento", "eventos.Evento", "Un evento (reunión, acción…)"),)
    permisos = (
        Permiso("eventos.convocar", "Convocar eventos del grupo (las reuniones, además, con apoyos)", roles=("usuario", "admin_grupo", "admin_org")),
    )
    cometidos = (
        Cometido("eventos.facilitacion", "Facilitación", "Modera la reunión: da la palabra, cuida los tiempos y el orden del día."),
        Cometido("eventos.toma_de_acta", "Toma de acta", "Escribe el acta de la reunión."),
        Cometido("eventos.promocion", "Promoción y comunicación", "Difunde el evento: cartel, redes, avisos."),
        Cometido("eventos.logistica", "Logística", "Material, transporte, montaje y desmontaje."),
        Cometido("eventos.cuidados", "Cuidados", "Atiende a las personas: accesibilidad, bienestar, conflictos."),
        Cometido("eventos.oveja", "Oveja", "Hace de enlace y vigila que nadie se quede atrás en una acción."),
    )
    emite = (
        Emision("eventos.convocado", "Se ha convocado un evento (o una reunión ha conseguido sus apoyos). Datos: evento_id."),
        Emision("eventos.cancelado", "Se ha cancelado un evento. Datos: evento_id."),
    )
    avisos = (
        TipoDeAviso("eventos.convocado", "Nuevos eventos que puedo ver", "eventos", "eventos.convocado", "eventos.avisos.convocado"),
        TipoDeAviso("eventos.cancelado", "Se cancela un evento al que iba", "eventos", "eventos.cancelado", "eventos.avisos.cancelado"),
    )
    # Convocar una reunión necesita apoyos (docs/diseno.md, apartado 6): 2 en el propio grupo, 5 en el padre,
    # 10 en el abuelo o más arriba. Para los primeros usuarios, el sí del superadmin basta.
    solicitudes = (
        TipoDeSolicitud(
            "eventos.reunion", "Convocar una reunión", resolver="eventos.servicios.convocar_reunion",
            apoyos_por_altura=(2, 5, 10), dias=7, basta_el_superadmin=True,
        ),
    )
    # En el calendario común: cada evento con el color de su tipo; quien lo gestiona puede arrastrarlo.
    fuentes_de_calendario = (
        FuenteDeCalendario("eventos.eventos", "Eventos", "eventos.calendario.fechas", color="#e11d78", mover="eventos.calendario.mover"),
    )
    menu = (
        EntradaDeMenu(
            codigo="eventos.eventos",
            nombre="Eventos",
            url="eventos:proximos",
            icono="✷",
            color="#e11d78",
            orden=120,
            otras_rutas=("eventos:evento", "eventos:editar", "eventos:cartel"),
            subsecciones=(
                EntradaDeMenu(
                    codigo="eventos.lista", nombre="Próximos", url="eventos:proximos", icono="➤", color="#0284d9",
                    vistas=(Vista("Próximos", "eventos:proximos"), Vista("Pasados", "eventos:pasados")),
                ),
                EntradaDeMenu(
                    codigo="eventos.mios", nombre="Mis eventos", url="eventos:mios", icono="★", color="#166534",
                    vistas=(Vista("Mis eventos", "eventos:mios"), Vista("Convocar", "eventos:convocar")),
                ),
            ),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="eventos.eventos",
            titulo="Eventos",
            texto=(
                "Las actividades con fecha de tus grupos: reuniones, acciones, recaudatorios… Cada una dice quién "
                "la convoca, de qué tipo es, quién puede verla, dónde y cuándo es, y si cuesta algo."
            ),
        ),
        Ayuda(
            seccion="eventos.lista",
            titulo="Próximos y pasados",
            texto=(
                "Los eventos que puedes ver, del más cercano al más lejano. Pulsa uno para ver sus datos, decir "
                "si vas a ir y apuntarte a un cometido (facilitación, logística…). Cuántas personas van lo ve "
                "todo el mundo; quiénes, solo quien convoca y quien tiene un cometido."
            ),
        ),
        Ayuda(
            seccion="eventos.mios",
            titulo="Mis eventos",
            texto=(
                "Los que has convocado y aquellos a los que has dicho que vas o quizá. Con «Convocar» creas uno. "
                "Una reunión necesita apoyos: queda pendiente (solo la ves tú) hasta que la apoyan 2 personas de "
                "tu grupo (5 si es para el grupo padre, 10 para el abuelo); entonces se convoca sola."
            ),
        ),
    )
