"""
Configuración y contrato del módulo «comunicaciones».
"""

from base.contrato import Ayuda, Capa, EntradaDeMenu, ModuloConfig, Vista


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
                    otras_rutas=("comunicaciones:abrir",),
                    vistas=(Vista("Bandeja", "comunicaciones:notificaciones"),),
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
            seccion="comunicaciones.preferencias",
            titulo="Preferencias de aviso",
            texto=(
                "Qué tipos de aviso quieres recibir, agrupados por su origen. Desmarca los que no te interesen: "
                "dejarán de llegarte (los que ya tienes se quedan). De momento solo llegan a la web; más "
                "adelante se podrá elegir también el correo."
            ),
        ),
    )
