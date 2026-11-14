"""
Configuración y contrato del módulo «calendario».
"""

from base.contrato import Ayuda, Capa, DatosDeEjemplo, EntradaDeMenu, FuenteDeCalendario, Limpiable, ModuloConfig, Permiso, Vista


class CalendarioConfig(ModuloConfig):
    """
    Contrato del módulo «calendario»: junta en un calendario todo lo que tiene fecha (cada módulo lo
    aporta con su FuenteDeCalendario), con un color por tipo, filtros y arrastrar lo propio; los
    recordatorios (anotaciones libres de cada grupo) y la suscripción .ics con una clave secreta.
    """

    name = "calendario"
    verbose_name = "Calendario"
    capa = Capa.FUNCIONAL
    descripcion = (
        "Calendario común con todo lo que tiene fecha (eventos y, más adelante, fechas de proyectos y consultas), "
        "con un color por tipo y filtros; recordatorios libres que se ven en el grupo (y, si lo decide su "
        "administración, en el padre y el abuelo); y suscripción .ics para verlo en el móvil."
    )
    # No crea ejemplos, pero al borrarlos quita los recordatorios apuntados al probar en los grupos de
    # ejemplo o por las personas de ejemplo.
    datos_de_ejemplo = DatosDeEjemplo(crear="", borrar="calendario.ejemplos.borrar")
    permisos = (
        Permiso(
            "calendario.ampliar_recordatorios", "Hacer visibles los recordatorios del grupo a los grupos padre y abuelo",
            roles=("admin_grupo", "admin_org"),
        ),
    )
    limpiables = (
        Limpiable(
            "calendario.recordatorio", "calendario.Recordatorio", "Recordatorios pasados",
            terminados="calendario.limpieza.recordatorios", ficha="calendario:recordatorio",
        ),
    )
    fuentes_de_calendario = (
        FuenteDeCalendario("calendario.recordatorios", "Recordatorios", "calendario.fuentes.recordatorios", color="#ca8a04", mover="calendario.fuentes.mover"),
    )
    menu = (
        # La sección «Calendario y eventos»: sus pestañas (el calendario y las de «eventos») las coloca
        # config/menu.py.
        EntradaDeMenu(
            codigo="calendario.calendario",
            nombre="Calendario y eventos",
            url="calendario:calendario",
            icono="▦",
            color="#0e7490",
        ),
        # El calendario. Los recordatorios y la suscripción se abren con sus botones, desde el propio
        # calendario.
        EntradaDeMenu(
            codigo="calendario.ver", nombre="Calendario", url="calendario:calendario", icono="◫", color="#0ea5e9",
            otras_rutas=("calendario:recordatorio", "calendario:recordatorios", "calendario:nuevo", "calendario:suscripcion"),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="calendario.calendario",
            titulo="Calendario y eventos",
            texto=(
                "Todo lo que tiene fecha y puedes ver. «Calendario»: los eventos, los recordatorios y las fechas "
                "límite juntos. «Eventos de mis grupos»: las actividades de tus grupos (reuniones, acciones, "
                "recaudatorios…). «Mis eventos»: los que convocas o a los que vas. «Convocar»: crear uno."
            ),
        ),
        Ayuda(
            seccion="calendario.ver",
            titulo="Calendario",
            texto=(
                "Todo lo que tiene fecha y puedes ver: eventos, recordatorios, fechas límite… Cada tipo tiene su "
                "color y con las casillas de arriba lo ocultas o lo muestras. Cambia entre mes, semana, día y lista "
                "con los botones. Pulsa algo para abrir su ficha. Lo que gestionas (tus eventos, tus "
                "recordatorios) se puede arrastrar a otro día u hora. Pulsa un hueco para apuntar un recordatorio.\n\n"
                "«+ Recordatorio»: una anotación libre («llevar las pancartas»); decides si la ves solo tú o tu "
                "grupo. «Mis recordatorios»: los próximos.\n\n"
                "«Suscripción»: una dirección secreta para ver tu calendario en el móvil. Quien la tenga ve tus "
                "fechas sin entrar: no la compartas. Si se te escapa, cámbiala y la anterior deja de funcionar."
            ),
            ejemplo="Apuntas «llevar las pancartas» el viernes para tu grupo, y le sale a todo el grupo en su calendario.",
        ),
    )
