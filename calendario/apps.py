"""
Configuración y contrato del módulo «calendario».
"""

from base.contrato import Ayuda, Capa, EntradaDeMenu, FuenteDeCalendario, Limpiable, ModuloConfig, Permiso, Vista


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
        EntradaDeMenu(
            codigo="calendario.calendario",
            nombre="Calendario",
            url="calendario:calendario",
            icono="▦",
            color="#0e7490",
            orden=125,
            otras_rutas=("calendario:recordatorio",),
            subsecciones=(
                EntradaDeMenu(
                    codigo="calendario.ver", nombre="Ver el calendario", url="calendario:calendario", icono="◫", color="#0ea5e9",
                    vistas=(Vista("Calendario", "calendario:calendario"),),
                ),
                EntradaDeMenu(
                    codigo="calendario.recordatorios", nombre="Recordatorios", url="calendario:recordatorios", icono="✐", color="#a855f7",
                    vistas=(Vista("Próximos", "calendario:recordatorios"), Vista("Apuntar uno", "calendario:nuevo")),
                ),
                EntradaDeMenu(
                    codigo="calendario.suscripcion", nombre="Suscripción", url="calendario:suscripcion", icono="⟳", color="#475569",
                    vistas=(Vista("Suscripción .ics", "calendario:suscripcion"),),
                ),
            ),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="calendario.calendario",
            titulo="Calendario",
            texto=(
                "Todo lo que tiene fecha y puedes ver, en un mismo calendario: eventos, recordatorios… Cada tipo "
                "tiene su color y con las casillas de arriba lo ocultas o lo muestras."
            ),
        ),
        Ayuda(
            seccion="calendario.ver",
            titulo="Ver el calendario",
            texto=(
                "Cambia entre mes, semana, día y lista con los botones. Pulsa algo para abrir su ficha. Lo que "
                "gestionas (tus eventos, tus recordatorios) se puede arrastrar a otro día u hora. Pulsa un hueco "
                "para apuntar un recordatorio ese día."
            ),
        ),
        Ayuda(
            seccion="calendario.recordatorios",
            titulo="Recordatorios",
            texto=(
                "Anotaciones libres en el calendario («llevar las pancartas», «cierra el local»). Decides si lo ves "
                "solo tú o tu grupo; la administración del grupo puede abrirlo también al grupo padre y al abuelo."
            ),
        ),
        Ayuda(
            seccion="calendario.suscripcion",
            titulo="Suscripción",
            texto=(
                "Una dirección secreta para ver tu calendario en el móvil o en otro programa de calendario. Quien "
                "la tenga ve tus fechas sin entrar: no la compartas. Si se te escapa, cámbiala y la anterior deja "
                "de funcionar."
            ),
        ),
    )
