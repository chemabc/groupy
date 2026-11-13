"""
Configuración y contrato del módulo «comunicaciones».
"""

from base.contrato import Ayuda, Capa, EntradaDeMenu, ModuloConfig, Permiso, Vista


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
    menu = (
        EntradaDeMenu(
            codigo="comunicaciones.comunicaciones",
            nombre="Comunicaciones",
            url="comunicaciones:notificaciones",
            icono="☏",
            color="#9333ea",
            orden=100,
            subsecciones=(
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
                EntradaDeMenu(
                    codigo="comunicaciones.conversaciones",
                    nombre="Con la administración",
                    url="comunicaciones:conversaciones",
                    icono="❝",
                    color="#0f766e",
                    contador="comunicaciones.servicios.conversaciones_sin_leer",
                    otras_rutas=("comunicaciones:conversacion",),
                    vistas=(
                        Vista("Conversaciones", "comunicaciones:conversaciones"),
                        Vista("Escribir a la administración", "comunicaciones:nueva_conversacion"),
                    ),
                ),
                EntradaDeMenu(
                    codigo="comunicaciones.avisos",
                    nombre="Avisos de la administración",
                    url="comunicaciones:avisos",
                    icono="✪",
                    color="#b45309",
                    permiso="comunicaciones.avisar",
                    vistas=(Vista("Avisar y enviados", "comunicaciones:avisos"),),
                ),
                EntradaDeMenu(
                    codigo="comunicaciones.preferencias",
                    nombre="Preferencias de aviso",
                    url="comunicaciones:preferencias",
                    icono="✓",
                    color="#57534e",
                    vistas=(Vista("Qué quiero recibir", "comunicaciones:preferencias"),),
                ),
            ),
        ),
        # «Configuración → Niveles de aviso», colgada de la sección de «tipologias».
        EntradaDeMenu(
            codigo="comunicaciones.niveles",
            nombre="Niveles de aviso",
            url="comunicaciones:niveles",
            icono="◐",
            color="#a16207",
            permiso="comunicaciones.niveles",
            dentro_de="tipologias.configuracion",
            orden=40,
            vistas=(Vista("Niveles", "comunicaciones:niveles"),),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="comunicaciones.notificaciones",
            titulo="Notificaciones",
            texto=(
                "Avisos de lo que pasa y te afecta: te han admitido en un grupo, han invitado a uno de tus "
                "grupos… Arriba, las bandejas según su origen, con cuántas tienes sin ver.\\n\\n"
                "Pulsa una notificación para ir a lo que cuenta (queda vista), o márcala como vista sin abrirla. "
                "La papelera la borra. «Limpiar las vistas» borra de una vez todas las que ya has visto; las "
                "que no has visto se quedan.\\n\\n"
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
                "Cada conversación tiene un estado (abierta, en proceso, solucionada) que cambian los admins. Si "
                "atiendes alguna administración, debajo salen las conversaciones que le llegan; primero, las que "
                "tienen algo sin leer. El número del menú cuenta las que tienen algo nuevo para ti.\n\n"
                "Con una conversación abierta, los mensajes nuevos aparecen solos (se mira cada 10 segundos)."
            ),
        ),
        Ayuda(
            seccion="comunicaciones.avisos",
            titulo="Avisos de la administración",
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
            titulo="Preferencias de aviso",
            texto=(
                "Qué tipos de aviso quieres recibir, agrupados por su origen. Desmarca los que no te interesen: "
                "dejarán de llegarte (los que ya tienes se quedan). De momento solo llegan a la web; más "
                "adelante se podrá elegir también el correo."
            ),
        ),
    )
