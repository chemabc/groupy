"""
Configuración y contrato del módulo «comunicaciones».
"""

from base.contrato import Ayuda, Capa, EntradaDeMenu, Limpiable, ModuloConfig, Permiso, Vista


class ComunicacionesConfig(ModuloConfig):
    """
    Contrato del módulo «comunicaciones»: reparte las notificaciones que declaran los demás módulos (sus
    «avisos») y aporta la sección «Comunicaciones» de cada persona. Más adelante, mensajes,
    conversaciones, chat, correo y Telegram.
    """

    name = "comunicaciones"
    verbose_name = "Comunicaciones"
    capa = Capa.FUNCIONAL
    descripcion = (
        "Notificaciones de cada persona, por bandejas según su origen, con preferencias para activar o "
        "desactivar cada tipo de aviso. Cada módulo declara sus avisos en su contrato y este módulo los "
        "reparte desde la bandeja de eventos_sw."
    )
    permisos = (
        Permiso(
            "comunicaciones.avisar",
            "Mandar avisos de la administración a los grupos y personas que se administran",
            roles=("admin_grupo", "admin_org"),
        ),
        # Sin roles por defecto: solo el superadmin.
        Permiso("comunicaciones.niveles", "Crear y cambiar los niveles de los avisos (nombre y color)"),
    )
    # El registro conecta esta función a cada tipo de aviso de cualquier módulo (ver base/registro.py).
    reparte_avisos = "comunicaciones.servicios.repartir"
    # Las notificaciones viejas se borran sin archivar ni avisar (ver comunicaciones/limpieza.py).
    limpiables = (
        Limpiable(
            "comunicaciones.notificacion_vista", "comunicaciones.Notificacion", "Notificaciones vistas (días desde que se vieron)",
            borrar="comunicaciones.limpieza.borrar_vistas", borrar_a=90,
        ),
        Limpiable(
            "comunicaciones.notificacion_sin_ver", "comunicaciones.Notificacion", "Notificaciones sin ver (días desde que llegaron)",
            borrar="comunicaciones.limpieza.borrar_sin_ver", borrar_a=365,
        ),
    )
    menu = (
        # Las entradas de «Comunicaciones». Dónde va cada una (también las de administrar y la de las
        # preferencias, que van en otros bloques) lo decide config/menu.py.
        EntradaDeMenu(
            codigo="comunicaciones.comunicaciones",
            nombre="Comunicaciones",
            url="comunicaciones:notificaciones",
            icono="☏",
            color="#9333ea",
        ),
        EntradaDeMenu(
            codigo="comunicaciones.notificaciones",
            nombre="Notificaciones",
            url="comunicaciones:notificaciones",
            icono="⚑",
            color="#1e3a8a",
            contador="comunicaciones.servicios.sin_ver",
            otras_rutas=("comunicaciones:abrir", "comunicaciones:aviso"),
            vistas=(Vista("Bandeja", "comunicaciones:notificaciones"),),
        ),
        # «Conversaciones», con sus pestañas (con la administración, con grupos, con personas).
        EntradaDeMenu(
            codigo="comunicaciones.conversar",
            nombre="Conversaciones",
            url="comunicaciones:conversaciones",
            icono="✆",
            color="#0d9489",
        ),
        EntradaDeMenu(
            codigo="comunicaciones.conversaciones",
            nombre="Con la administración",
            url="comunicaciones:conversaciones",
            icono="❝",
            color="#0f766e",
            contador="comunicaciones.servicios.conversaciones_sin_leer",
            otras_rutas=("comunicaciones:conversacion",),
            vistas=(
                Vista("Mis conversaciones", "comunicaciones:conversaciones"),
                Vista("Escribir a la administración", "comunicaciones:nueva_conversacion"),
            ),
        ),
        # Para administrar: lo que llega a las administraciones que se atienden y los avisos.
        EntradaDeMenu(
            codigo="comunicaciones.atendidas",
            nombre="Conversaciones que atiendo",
            url="comunicaciones:atendidas",
            icono="⇋",
            color="#115e5a",
            permiso="comunicaciones.avisar",
            contador="comunicaciones.servicios.atendidas_sin_leer",
        ),
        EntradaDeMenu(
            codigo="comunicaciones.avisos",
            nombre="Avisar",
            url="comunicaciones:avisos",
            icono="✪",
            color="#b45309",
            permiso="comunicaciones.avisar",
            vistas=(Vista("Avisar y enviados", "comunicaciones:avisos"),),
        ),
        EntradaDeMenu(
            codigo="comunicaciones.preferencias",
            nombre="Avisos que recibo",
            url="comunicaciones:preferencias",
            icono="✓",
            color="#57534e",
            vistas=(Vista("Qué quiero recibir", "comunicaciones:preferencias"),),
        ),
        EntradaDeMenu(
            codigo="comunicaciones.niveles",
            nombre="Niveles de aviso",
            url="comunicaciones:niveles",
            icono="◐",
            color="#a16207",
            permiso="comunicaciones.niveles",
            vistas=(Vista("Niveles", "comunicaciones:niveles"),),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="comunicaciones.notificaciones",
            titulo="Notificaciones",
            texto=(
                "Avisos de lo que pasa y te afecta: te han admitido en un grupo, han invitado a uno de tus "
                "grupos… Arriba, las bandejas según su origen, con cuántas tienes sin ver.\n\n"
                "Pulsa una notificación para ir a lo que cuenta (queda vista), o márcala como vista sin abrirla. "
                "La papelera la borra. «Limpiar las vistas» borra de una vez todas las que ya has visto; las "
                "que no has visto se quedan.\n\n"
                "El número del menú son las que tienes sin ver. Se pone al día al cambiar de pantalla."
            ),
        ),
        Ayuda(
            seccion="comunicaciones.conversaciones",
            titulo="Con la administración",
            texto=(
                "Conversaciones con la administración de la plataforma: la de uno de tus grupos (o de uno que "
                "los contiene), la de tu organización o el superadmin. Nunca se escribe a la persona que es "
                "admin, sino a la administración: la atienden todos sus admins, y quien responde firma como "
                "«Admin de GRU Henares (Lince)». Las pueden leer también los admins de la organización y el "
                "superadmin, porque son temas administrativos.\n\n"
                "Cada conversación tiene un estado (abierta, en proceso, solucionada) que cambian los admins. El "
                "número del menú cuenta las que tienen una respuesta nueva para ti. Si atiendes alguna "
                "administración, lo que le llega está aparte, en «Administrar → Buzón de la administración».\n\n"
                "Con una conversación abierta, los mensajes nuevos aparecen solos (se mira cada 10 segundos)."
            ),
        ),
        Ayuda(
            seccion="comunicaciones.atendidas",
            titulo="Conversaciones que atiendo",
            texto=(
                "Lo que llega a las administraciones que atiendes (la de tus grupos, la de tu organización o, si "
                "eres superadmin, todas); primero, lo que tiene algo sin leer. Respondes en nombre de la "
                "administración: tu respuesta se firma como «Admin de GRU Henares (tu alias)». Cambia el estado "
                "(abierta, en proceso, solucionada) según avance."
            ),
            ejemplo="Nutria pregunta a la administración de GRU Henares cómo entrar en GRU Sorbe; Lince responde y la marca como solucionada.",
        ),
        Ayuda(
            seccion="comunicaciones.avisos",
            titulo="Avisar",
            texto=(
                "Para avisar a grupos (cada uno con sus subgrupos) o a personas, en nombre de una administración "
                "que atiendes. Cada aviso tiene un nivel con su color (Información, Atención, Problema…), que "
                "se ve en la bandeja de quien lo recibe. Si marcas «Se puede responder», el aviso lleva un enlace "
                "para abrir una conversación con esa administración. Abajo, los avisos enviados por las "
                "administraciones que atiendes."
            ),
        ),
        Ayuda(
            seccion="comunicaciones.niveles",
            titulo="Niveles de aviso",
            texto=(
                "Cuánta atención pide un aviso de la administración, con su color: «Información», «Atención», "
                "«Problema»… Se pueden cambiar, crear más y ordenar. Uno que ya se ha usado no se puede borrar, "
                "pero sí cambiarle el nombre o el color."
            ),
        ),
        Ayuda(
            seccion="comunicaciones.preferencias",
            titulo="Avisos que recibo",
            texto=(
                "Qué tipos de aviso quieres recibir, agrupados por su origen. Desmarca los que no te interesen: "
                "dejarán de llegarte (los que ya tienes se quedan). De momento solo llegan a la web; más "
                "adelante se podrá elegir también el correo."
            ),
        ),
    )
