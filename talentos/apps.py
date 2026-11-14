"""
Configuración y contrato del módulo «talentos».
"""

from base.contrato import Ayuda, Capa, DatosDeEjemplo, Emision, EntradaDeMenu, ModuloConfig, Permiso, TipoDeAviso, Vista, TarjetaDeInicio


class TalentosConfig(ModuloConfig):
    """
    Contrato del módulo «talentos»: el catálogo común de talentos (recursos y habilidades), los de cada
    persona y con qué grupos los comparte, los recuentos (nunca quiénes) y las peticiones de talentos.
    Va en la capa de organización, y no dentro de «usuarios» como decía el diseño, porque necesita los
    grupos.
    """

    name = "talentos"
    verbose_name = "Talentos"
    capa = Capa.ORGANIZACION
    descripcion = (
        "Talentos de las personas (recursos y habilidades) de un catálogo común. Cada persona decide con qué "
        "grupos comparte cada uno; los demás solo ven cuántas personas lo comparten. Las administraciones "
        "piden talentos a un grupo y quien quiere se ofrece; solo entonces se revela su alias."
    )
    datos_de_ejemplo = DatosDeEjemplo(crear="talentos.ejemplos.crear", borrar="talentos.ejemplos.borrar")
    emite = (
        Emision("talentos.peticion", "Una administración ha pedido talentos a un grupo. Datos: peticion_id."),
        Emision("talentos.ofrecimiento", "Alguien se ha ofrecido para una petición de talentos. Datos: ofrecimiento_id."),
    )
    avisos = (
        TipoDeAviso("talentos.peticion", "Piden un talento que compartes", "admins", "talentos.peticion", "talentos.avisos.peticion"),
        TipoDeAviso("talentos.ofrecimiento", "Alguien se ofrece en una petición de talentos tuya", "admins", "talentos.ofrecimiento", "talentos.avisos.ofrecimiento"),
    )
    permisos = (
        Permiso("talentos.pedir", "Pedir talentos al grupo (cuáles y cuántos) y ver quién se ofrece", roles=("admin_grupo", "admin_org")),
        # Sin roles por defecto: solo el superadmin.
        Permiso("talentos.catalogo", "Ordenar el catálogo de talentos: renombrar, poner relacionadas y fusionar repetidos"),
    )
    # Sus recuadros de la portada (Inicio); dónde sale cada uno lo decide config/inicio.py.
    tarjetas_de_inicio = (
        TarjetaDeInicio("talentos.mios", "Mis talentos", "talentos.inicio.mios", icono="❀", color="#86198f"),
    )
    menu = (
        # Las entradas de talentos van en sitios distintos (ver config/menu.py): los míos, en «Configuración de
        # mi cuenta»; las peticiones, en «Comunicaciones → Solicitudes»; los del grupo, en «Mis grupos»; pedir,
        # en «Administrar»; el catálogo, en «Plataforma».
        EntradaDeMenu(
            codigo="talentos.mios", nombre="Talentos", url="talentos:mis_talentos", icono="❀", color="#86198f",
            vistas=(Vista("Mis talentos", "talentos:mis_talentos"),),
        ),
        EntradaDeMenu(
            codigo="talentos.peticiones", nombre="Peticiones de talentos", url="talentos:peticiones", icono="☘", color="#4d7c0f",
            contador="talentos.servicios.peticiones_para",
            otras_rutas=("talentos:peticion",),
        ),
        EntradaDeMenu(
            codigo="talentos.del_grupo", nombre="Talentos de mis grupos", url="talentos:del_grupo", icono="⁂", color="#0c4a6e",
        ),
        EntradaDeMenu(
            codigo="talentos.pedir", nombre="Pedir talentos", url="talentos:nueva_peticion", icono="✿", color="#c2410c",
            permiso="talentos.pedir",
        ),
        EntradaDeMenu(
            codigo="talentos.catalogo", nombre="Talentos", url="talentos:catalogo", icono="▤", color="#831843",
            permiso="talentos.catalogo",
            vistas=(Vista("Catálogo", "talentos:catalogo"),),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="talentos.mios",
            titulo="Mis talentos",
            texto=(
                "Lo que puedes aportar: recursos (una furgoneta, un local) y habilidades (trabajos verticales, "
                "diseño). Es un dato tuyo: decides con qué grupos compartes cada talento, y en esos grupos solo se "
                "ve cuántas personas lo comparten, nunca quiénes.\n\n"
                "Añade tus talentos (el catálogo te propone los que ya existen, para no repetirlos) y marca con qué "
                "grupos compartes cada uno. Si no lo compartes con ningún grupo, nadie sabrá que lo tienes y no te "
                "llegarán peticiones."
            ),
        ),
        Ayuda(
            seccion="talentos.peticiones",
            titulo="Peticiones de talentos",
            texto=(
                "Lo que piden las administraciones de tus grupos: qué talentos hacen falta y cuántos. Si tienes uno, "
                "pulsa «Lo ofrezco»: tu alias lo verán solo quien hizo la petición y la administración del grupo. Si "
                "tienes dudas, abre una conversación con la administración. El número del menú son las que piden "
                "algo que compartes y aún no has respondido."
            ),
        ),
        Ayuda(
            seccion="talentos.del_grupo",
            titulo="Talentos de mis grupos",
            texto=(
                "Cuántas personas comparten cada talento con el grupo (o con sus subgrupos). Nunca quiénes. Si "
                "administras el grupo, puedes pedir talentos en «Administrar → Eventos y talentos»."
            ),
        ),
        Ayuda(
            seccion="talentos.pedir",
            titulo="Pedir talentos",
            texto=(
                "Pide a un grupo que administras los talentos que hacen falta (por ejemplo, «2 furgonetas» para una "
                "mudanza). Les llega a quienes comparten ese talento con el grupo, y quien lo tiene responde «Lo "
                "ofrezco». Tú ves su alias; el resto del grupo, no."
            ),
        ),
        Ayuda(
            seccion="talentos.catalogo",
            titulo="Catálogo de talentos",
            texto="Para el superadmin: renombrar talentos, ponerles palabras relacionadas y fusionar los repetidos.",
        ),
    )
