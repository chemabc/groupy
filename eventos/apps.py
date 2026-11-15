"""
Configuración y contrato del módulo «eventos».
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
    TareaDiaria,
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
        "Eventos de los grupos (sueltos o en series que se repiten): reuniones (con solicitud de apoyos), acciones, recaudatorios y genéricos, con "
        "los campos de su tipología, quién lo ve, modalidad y lugar, cartel, texto para las redes, «¿Vas a "
        "ir?» y cometidos."
    )
    anclas = (Ancla("eventos.evento", "eventos.Evento", "Un evento (reunión, acción…)"),)
    # No crea ejemplos, pero al borrarlos quita los eventos convocados al probar en los grupos de ejemplo.
    datos_de_ejemplo = DatosDeEjemplo(crear="", borrar="eventos.ejemplos.borrar")
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
        # Una serie de reuniones pide los apoyos una sola vez, para toda la serie.
        TipoDeSolicitud(
            "eventos.serie_de_reuniones", "Convocar una serie de reuniones", resolver="eventos.series.activar_serie",
            apoyos_por_altura=(2, 5, 10), dias=7, basta_el_superadmin=True,
        ),
    )
    # Cada día se crean las siguientes veces de las series (hasta su antelación, 90 días por defecto).
    tareas_diarias = (
        TareaDiaria("eventos.generar_series", "Crea las siguientes veces de las series de eventos y termina las que han llegado a su final.", "eventos.series.generar_todas"),
    )
    # En el calendario común: cada evento con el color de su tipo; quien lo gestiona puede arrastrarlo.
    limpiables = (
        Limpiable("eventos.evento", "eventos.Evento", "Eventos pasados", terminados="eventos.limpieza.eventos", ficha="eventos:evento"),
    )
    fuentes_de_calendario = (
        FuenteDeCalendario("eventos.eventos", "Eventos", "eventos.calendario.fechas", color="#e11d78", mover="eventos.calendario.mover"),
    )
    menu = (
        # Van como pestañas de «Calendario y eventos» (ver config/menu.py).
        EntradaDeMenu(
            codigo="eventos.lista", nombre="Eventos de mis grupos", url="eventos:proximos", icono="➤", color="#0284d9",
            otras_rutas=("eventos:evento", "eventos:editar", "eventos:cartel"),
            vistas=(Vista("Próximos", "eventos:proximos"), Vista("Pasados", "eventos:pasados")),
        ),
        EntradaDeMenu(
            codigo="eventos.mios", nombre="Mis eventos", url="eventos:mios", icono="★", color="#166534",
            otras_rutas=("eventos:serie",),
            vistas=(Vista("Próximos", "eventos:mios"), Vista("Pasados", "eventos:mios_pasados"), Vista("Series", "eventos:series")),
        ),
        # «Administrar → Eventos y talentos → Eventos de mis grupos» (ver config/menu.py).
        EntradaDeMenu(
            codigo="eventos.administrados", nombre="Eventos de mis grupos", url="eventos:administrados", icono="✶", color="#b91c1d",
            permiso="grupos.ver_arbol",
            vistas=(
                Vista("Próximos", "eventos:administrados"), Vista("Esperan apoyos", "eventos:administrados_pendientes"),
                Vista("Pasados", "eventos:administrados_pasados"), Vista("Cancelados", "eventos:administrados_cancelados"),
            ),
        ),
        EntradaDeMenu(
            codigo="eventos.convocar", nombre="Convocar", url="eventos:convocar", icono="✷", color="#e11d78",
            permiso="eventos.convocar",
        ),
    )
    ayuda = (
        Ayuda(
            seccion="eventos.lista",
            titulo="Eventos de mis grupos",
            texto=(
                "Las actividades con fecha de tus grupos: reuniones, acciones, recaudatorios… Cada una dice quién "
                "la convoca, de qué tipo es, quién puede verla, dónde y cuándo es, y si cuesta algo.\n\n"
                "Arriba, «Próximos» y «Pasados»: los eventos que puedes ver, del más cercano al más lejano. Pulsa uno para ver sus datos, decir "
                "si vas a ir y apuntarte a un cometido (facilitación, logística…). Cuántas personas van lo ve "
                "todo el mundo; quiénes, solo quien convoca y quien tiene un cometido."
            ),
        ),
        Ayuda(
            seccion="eventos.administrados",
            titulo="Eventos de mis grupos (administración)",
            texto=(
                "Los eventos de los grupos que administras y de sus subgrupos, para seguirlos y ayudar. Arriba, "
                "«Próximos», «Esperan apoyos» (las reuniones que aún no tienen los apoyos, con cuántos llevan), "
                "«Pasados» y «Cancelados». Filtra por tipo, grupo o estado, busca por palabra u ordena por "
                "cualquier columna.\n\n"
                "Desde la ficha de cada uno puedes editarlo o cancelarlo (por ejemplo, si quien lo convocó no "
                "está). Ves cuántas personas van, pero no quiénes: eso solo lo ven quien convoca y quien tiene un "
                "cometido."
            ),
            ejemplo="Lince administra GRU Henares: en «Esperan apoyos» ve que la reunión de vecinos lleva 1 de 2 apoyos y avisa al grupo.",
        ),
        Ayuda(
            seccion="eventos.mios",
            titulo="Mis eventos",
            texto=(
                "Los que has convocado y aquellos a los que has dicho que vas o quizá, en «Próximos» y «Pasados», con tu "
                "papel en cada uno (Convoco, Voy, Quizá); se filtran por cualquier columna. Con la pestaña «Convocar» creas uno. "
                "Una reunión necesita apoyos: queda pendiente (solo la ves tú) hasta que la apoyan 2 personas de "
                "tu grupo (5 si es para el grupo padre, 10 para el abuelo); entonces se convoca sola. Al convocar "
                "puedes hacer que se repita (cada semana, cada mes…): en «Series» ves y cambias las tuyas. Cada vez "
                "es un evento propio; si cambias una a mano, los cambios de la serie ya no le afectan."
            ),
        ),
    )
