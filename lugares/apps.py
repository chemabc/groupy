"""
Configuración y contrato del módulo «lugares».
"""

from base.contrato import Ayuda, Capa, DatosDeEjemplo, Emision, EntradaDeMenu, ModuloConfig, Permiso, TipoDeAviso, Vista


class LugaresConfig(ModuloConfig):
    """
    Contrato del módulo «lugares»: la lista común de lugares de trabajo, con su mapa; el lugar de cada
    persona (privado); las propuestas de lugares nuevos y de cambios, que revisa el superadmin; y lo que
    muestra cada organización.
    """

    name = "lugares"
    verbose_name = "Lugares"
    capa = Capa.ORGANIZACION
    descripcion = (
        "Lista común de lugares de trabajo con mapa, importación desde hoja de cálculo, propuestas de lugares "
        "nuevos y de cambios (las revisa el superadmin), y el lugar de cada persona, que solo ven ella y el "
        "superadmin. Los recuentos por lugar solo se muestran a partir de 5 personas."
    )
    datos_de_ejemplo = DatosDeEjemplo(crear="lugares.ejemplos.crear", borrar="lugares.ejemplos.borrar")
    emite = (
        Emision("lugares.propuesta", "Alguien ha propuesto un lugar nuevo o un cambio. Datos: propuesta_id."),
        Emision("lugares.propuesta_revisada", "El superadmin ha aceptado o rechazado una propuesta. Datos: propuesta_id."),
        Emision("lugares.recordatorio", "El superadmin pide recordar a quien no ha elegido lugar. Sin datos."),
    )
    avisos = (
        TipoDeAviso("lugares.propuesta", "Propuestas de lugares para revisar (superadmin)", "sistema", "lugares.propuesta", "lugares.avisos.propuesta"),
        TipoDeAviso(
            "lugares.propuesta_revisada", "Han revisado tu propuesta de lugar", "sistema", "lugares.propuesta_revisada",
            "lugares.avisos.propuesta_revisada",
        ),
        TipoDeAviso("lugares.recordatorio", "Recordatorio para elegir tu lugar", "sistema", "lugares.recordatorio", "lugares.avisos.recordatorio"),
    )
    permisos = (
        # Sin roles por defecto: solo el superadmin.
        Permiso("lugares.gestionar", "Gestionar la lista de lugares: crearlos, importarlos y revisar las propuestas"),
        Permiso(
            "lugares.configurar", "Decidir qué ven de los lugares los miembros de la organización y si se publica el mapa",
            roles=("admin_org",),
        ),
    )
    menu = (
        # Van en sitios distintos (ver config/menu.py): mi lugar, en «Configuración de mi cuenta → Mis datos»;
        # el mapa, en «Organizaciones y grupos»; la gestión, en «Plataforma»; lo que se muestra, en
        # «Administrar → Mi organización».
        EntradaDeMenu(
            codigo="lugares.mi_lugar", nombre="Lugar", url="lugares:mi_lugar", icono="⊙", color="#be123c",
            vistas=(Vista("Mi lugar", "lugares:mi_lugar"),),
        ),
        EntradaDeMenu(
            codigo="lugares.mapa", nombre="Mapa de lugares", url="lugares:mapa", icono="◍", color="#047857",
            otras_rutas=("lugares:lugar",),
            vistas=(Vista("Mapa", "lugares:mapa"), Vista("Lista", "lugares:lista")),
        ),
        EntradaDeMenu(
            codigo="lugares.gestion", nombre="Lugares", url="lugares:propuestas", icono="✚", color="#9a3412",
            permiso="lugares.gestionar", contador="lugares.servicios.propuestas_pendientes",
            vistas=(Vista("Propuestas", "lugares:propuestas"), Vista("Nuevo lugar", "lugares:nuevo"), Vista("Importar", "lugares:importar")),
        ),
        # «Administrar → Mi organización → Lugares», colocada dentro de «Configuración» en config/menu.py.
        EntradaDeMenu(
            codigo="lugares.configuracion", nombre="Lugares", url="lugares:configuracion", icono="⌗", color="#3f6212",
            permiso="lugares.configurar",
            vistas=(Vista("Qué se muestra", "lugares:configuracion"),),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="lugares.mi_lugar",
            titulo="Mi lugar",
            texto=(
                "Tu lugar de trabajo (un instituto, un hospital…), de una lista común a toda la plataforma. Solo "
                "lo ves tú y el superadmin; los demás solo ven cuántas personas de su organización hay en cada "
                "lugar, y solo si son 5 o más.\n\n"
                "Elige tu lugar de trabajo de la lista. Si no está, propón uno nuevo con su nombre, su dirección y "
                "el enlace a un mapa (de OpenStreetMap o Google Maps); el superadmin lo revisará. Si algún dato de "
                "tu lugar está mal, pulsa «Proponer un cambio»: el superadmin lo revisa y lo corrige para todos."
            ),
        ),
        Ayuda(
            seccion="lugares.mapa",
            titulo="Mapa de lugares",
            texto=(
                "Todos los lugares de la lista. En el mapa, las chinchetas cercanas se agrupan en un círculo con su "
                "número; pulsa para acercarte o para ver los datos del lugar. Cada organización decide si sus "
                "miembros ven el mapa y los recuentos."
            ),
        ),
        Ayuda(
            seccion="lugares.gestion",
            titulo="Lugares (gestión)",
            texto=(
                "Para el superadmin. «Propuestas»: lugares nuevos y cambios que proponen las personas; en los "
                "cambios se ve qué datos cambian. «Nuevo lugar»: añadir uno a mano. «Importar»: subir muchos desde "
                "una hoja (.ods o .csv), con vista previa antes de confirmar. Desde aquí también se avisa a quienes "
                "aún no han elegido lugar."
            ),
        ),
        Ayuda(
            seccion="lugares.configuracion",
            titulo="Lugares en la organización",
            texto=(
                "Por si la información resulta delicada: si los miembros de la organización ven el mapa y la "
                "lista, si ven los recuentos (siempre a partir de 5 personas, nunca quiénes) y si el mapa se "
                "publica en la web pública de la organización (cuando exista)."
            ),
        ),
    )
