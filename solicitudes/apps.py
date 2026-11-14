"""
Configuración y contrato del módulo «solicitudes».
"""

from base.contrato import Ayuda, Capa, Emision, EntradaDeMenu, ModuloConfig, Permiso, TareaDiaria, TipoDeAviso, Vista, TarjetaDeInicio


class SolicitudesConfig(ModuloConfig):
    """
    Contrato del módulo «solicitudes»: pedir a un grupo algo que necesita apoyos (entrar en él, abrir un
    debate, convocar una reunión…). Los tipos de solicitud los declara cada módulo en su contrato; este
    módulo lleva los apoyos, el plazo y el estado, y llama al módulo del tipo cuando se acepta.
    """

    name = "solicitudes"
    verbose_name = "Solicitudes"
    capa = Capa.ORGANIZACION
    descripcion = (
        "Solicitudes con apoyos: lo que se pide a un grupo y necesita que sus miembros lo apoyen (y a veces "
        "el sí de su administración) antes de una fecha. Los rechazos solo se cuentan y no vetan."
    )
    emite = (
        Emision("solicitudes.pedida", "Alguien ha pedido algo a un grupo. Datos: solicitud_id."),
        Emision("solicitudes.aceptada", "Una solicitud ha conseguido lo necesario y se ha hecho. Datos: solicitud_id."),
        Emision("solicitudes.caducada", "Una solicitud ha llegado a su fecha sin lo necesario. Datos: solicitud_id."),
    )
    # Una vez al día, el trabajador cierra las solicitudes cuyo plazo ha pasado.
    tareas_diarias = (TareaDiaria("solicitudes.caducar", "Cierra como caducadas las solicitudes pendientes vencidas.", "solicitudes.servicios.caducar_vencidas"),)
    avisos = (
        TipoDeAviso(
            "solicitudes.necesita_tu_si", "Una solicitud necesita el sí de tu administración", "solicitudes",
            "solicitudes.pedida", "solicitudes.avisos.pedida",
        ),
        TipoDeAviso("solicitudes.aceptada", "Se ha aceptado una solicitud tuya", "solicitudes", "solicitudes.aceptada", "solicitudes.avisos.aceptada"),
        TipoDeAviso("solicitudes.caducada", "Ha caducado una solicitud tuya", "solicitudes", "solicitudes.caducada", "solicitudes.avisos.caducada"),
    )
    permisos = (
        Permiso(
            "solicitudes.ajustar",
            "Ajustar cuántos apoyos y cuántos días tiene cada tipo de solicitud en la organización",
            roles=("admin_org",),
        ),
    )
    # Sus recuadros de la portada (Inicio); dónde sale cada uno lo decide config/inicio.py.
    tarjetas_de_inicio = (
        TarjetaDeInicio("solicitudes.pendientes", "Solicitudes", "solicitudes.inicio.pendientes", icono="☛", color="#7c2d12"),
    )
    menu = (
        # «Solicitudes», con sus pestañas (enviadas, para apoyar, histórico… y las peticiones de talentos):
        # las coloca config/menu.py.
        EntradaDeMenu(
            codigo="solicitudes.solicitudes",
            nombre="Solicitudes",
            url="solicitudes:mias",
            icono="☛",
            color="#7c2d12",
            otras_rutas=("solicitudes:solicitud",),
        ),
        EntradaDeMenu(
            codigo="solicitudes.mias",
            nombre="Enviadas",
            url="solicitudes:mias",
            icono="✎",
            color="#15803d",
            vistas=(Vista("Enviadas", "solicitudes:mias"), Vista("Pedir algo", "solicitudes:nueva")),
        ),
        EntradaDeMenu(
            codigo="solicitudes.pendientes",
            nombre="Para apoyar",
            url="solicitudes:pendientes",
            icono="⧗",
            color="#eab308",
            contador="solicitudes.servicios.para_apoyar_para",
        ),
        EntradaDeMenu(
            codigo="solicitudes.pasadas",
            nombre="Histórico",
            url="solicitudes:pasadas",
            icono="◷",
            color="#78716c",
        ),
        # Para administrar: lo que espera el sí de la administración. La ve quien puede dar el sí a algún
        # tipo de solicitud: de entrada, quien puede admitir en un grupo (y, con aprueba_algo, quien pueda
        # aprobar los tipos que se añadan).
        EntradaDeMenu(
            codigo="solicitudes.por_aprobar",
            nombre="Por aprobar",
            url="solicitudes:por_aprobar",
            icono="✔",
            color="#ca8a05",
            contador="solicitudes.servicios.por_aprobar_para",
            permiso="grupos.admitir",
            tambien_si="solicitudes.servicios.aprueba_algo",
        ),
        # «Administrar → Mi organización → Apoyos y plazos», colocada dentro de «Configuración» en config/menu.py.
        EntradaDeMenu(
            codigo="solicitudes.ajustes",
            nombre="Apoyos y plazos",
            url="solicitudes:ajustes",
            icono="⚖",
            color="#6b21a8",
            permiso="solicitudes.ajustar",
            vistas=(Vista("Apoyos y plazos", "solicitudes:ajustes"),),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="solicitudes.solicitudes",
            titulo="Solicitudes",
            texto=(
                "Algunas cosas se piden a un grupo y necesitan que sus miembros las apoyen: entrar en un grupo y, "
                "más adelante, abrir un debate o convocar una reunión. Quien pide no cuenta como apoyo. Los "
                "rechazos solo se cuentan (no se ve quién rechaza) y no vetan. Algunas necesitan además el sí "
                "de la administración del grupo; para entrar en un grupo, el sí del superadmin basta."
            ),
        ),
        Ayuda(
            seccion="solicitudes.pendientes",
            titulo="Para apoyar",
            texto=(
                "Las solicitudes pendientes de tus grupos (también de los que contienen a los tuyos). Puedes "
                "apoyar, rechazar o retirar tu respuesta mientras está pendiente. «2 de 5» son los apoyos que "
                "tiene y los que necesita. Si llega la fecha sin lo necesario, caduca. El número del menú son las "
                "que aún no has respondido. Si administras un grupo, lo que espera tu sí está en «Administrar → "
                "Por aprobar»."
            ),
            ejemplo="Garza pide entrar en GRU Henares: como miembro de Henares, la apoyas para que llegue a los 2 apoyos.",
        ),
        Ayuda(
            seccion="solicitudes.por_aprobar",
            titulo="Por aprobar",
            texto=(
                "Las solicitudes de los grupos que administras que esperan el sí de la administración (por "
                "ejemplo, entrar en el grupo). Además de tu sí, necesitan los apoyos de los miembros. El "
                "superadmin ve todas y, en algunas, su sí basta."
            ),
        ),
        Ayuda(
            seccion="solicitudes.pasadas",
            titulo="Histórico",
            texto="Las solicitudes ya cerradas de tus grupos y las tuyas: aceptadas, canceladas y caducadas, con quién las pidió.",
        ),
        Ayuda(
            seccion="solicitudes.mias",
            titulo="Enviadas",
            texto=(
                "Lo que has pedido, con cómo va cada cosa. Puedes cancelar las pendientes. Con «Pedir algo» pides, "
                "por ejemplo, entrar en un grupo."
            ),
        ),
        Ayuda(
            seccion="solicitudes.ajustes",
            titulo="Ajustes de las solicitudes",
            texto=(
                "Cuántos apoyos necesita cada tipo de solicitud y cuántos días tiene para conseguirlos. El "
                "superadmin pone los de toda la plataforma; el admin de cada organización puede cambiar los de "
                "la suya. Solo vale para las solicitudes nuevas."
            ),
        ),
    )
