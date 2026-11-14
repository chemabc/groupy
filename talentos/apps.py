"""
Configuración y contrato del módulo «talentos».
"""

from base.contrato import Ayuda, Capa, DatosDeEjemplo, Emision, EntradaDeMenu, ModuloConfig, Permiso, TipoDeAviso, Vista


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
    menu = (
        EntradaDeMenu(
            codigo="talentos.talentos",
            nombre="Talentos",
            url="talentos:mis_talentos",
            icono="✿",
            color="#c2410c",
            otras_rutas=("talentos:peticion",),
            subsecciones=(
                EntradaDeMenu(
                    codigo="talentos.mios", nombre="Mis talentos", url="talentos:mis_talentos", icono="❀", color="#86198f",
                    vistas=(Vista("Mis talentos", "talentos:mis_talentos"),),
                ),
                EntradaDeMenu(
                    codigo="talentos.peticiones", nombre="Peticiones", url="talentos:peticiones", icono="☘", color="#4d7c0f",
                    contador="talentos.servicios.peticiones_para",
                    vistas=(Vista("Peticiones", "talentos:peticiones"), Vista("Pedir talentos", "talentos:nueva_peticion")),
                ),
                EntradaDeMenu(
                    codigo="talentos.del_grupo", nombre="Talentos de mis grupos", url="talentos:del_grupo", icono="⁂", color="#0c4a6e",
                    vistas=(Vista("Cuántos hay", "talentos:del_grupo"),),
                ),
                EntradaDeMenu(
                    codigo="talentos.catalogo", nombre="Catálogo", url="talentos:catalogo", icono="▤", color="#831843",
                    permiso="talentos.catalogo",
                    vistas=(Vista("Catálogo", "talentos:catalogo"),),
                ),
            ),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="talentos.talentos",
            titulo="Talentos",
            texto=(
                "Lo que cada persona puede aportar: recursos (una furgoneta, un local) y habilidades (trabajos "
                "verticales, diseño). Es un dato tuyo: decides con qué grupos compartes cada talento, y en esos "
                "grupos solo se ve cuántas personas lo comparten, nunca quiénes."
            ),
        ),
        Ayuda(
            seccion="talentos.mios",
            titulo="Mis talentos",
            texto=(
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
                "administras el grupo, desde aquí puedes pedir talentos."
            ),
        ),
        Ayuda(
            seccion="talentos.catalogo",
            titulo="Catálogo de talentos",
            texto="Para el superadmin: renombrar talentos, ponerles palabras relacionadas y fusionar los repetidos.",
        ),
    )
