"""
Configuración y contrato del módulo «grupos».
"""

from base.contrato import Ayuda, Capa, DatosDeEjemplo, Emision, EntradaDeMenu, ModuloConfig, Permiso, TipoDeAviso, TipoDeSolicitud, Vista, TarjetaDeInicio


class GruposConfig(ModuloConfig):
    """
    Contrato del módulo «grupos». Avisa con eventos_sw cuando cambia la estructura de los grupos o lo que
    cada persona es en ellos, para que «permisos» y «audiencias» rehagan sus cálculos, y cuando se
    invita a un grupo de otra organización a algo.
    """

    name = "grupos"
    verbose_name = "Organizaciones y grupos"
    capa = Capa.ORGANIZACION
    # Los ámbitos de cada persona en la biblioteca del editor colaborativo (ver grupos/editor.py).
    ambitos_del_editor = "grupos.editor.ambitos_para_editor"
    descripcion = (
        "Organizaciones, grupos y subgrupos (con su tabla de cierre), pertenencias con su rol y su "
        "asamblea base, admin de cada organización, relaciones libres entre grupos e invitaciones a "
        "grupos de otras organizaciones."
    )
    emite = (
        Emision(
            "grupos.estructura_cambiada",
            "Se ha creado un grupo o ha cambiado de grupo padre. Datos: grupo_id.",
        ),
        Emision(
            "grupos.pertenencias_cambiadas",
            "Una persona ha entrado en un grupo, ha salido, ha cambiado de rol o de asamblea base, o la "
            "han nombrado (o dejado de nombrar) admin de una organización. Datos: usuario_id.",
        ),
        Emision(
            "grupos.admitido",
            "Una persona ha entrado en un grupo. Datos: usuario_id, grupo_id, rol.",
        ),
        Emision(
            "grupos.rol_cambiado",
            "Ha cambiado el rol de una persona en un grupo. Datos: usuario_id, grupo_id, rol (el nuevo).",
        ),
        Emision(
            "grupos.admin_de_organizacion_nombrado",
            "Han nombrado a una persona admin de una organización. Datos: usuario_id, organizacion_id.",
        ),
        Emision(
            "grupos.invitacion_creada",
            "Un grupo ha invitado a un grupo de otra organización a algo (un proyecto). Datos: "
            "invitacion_id, ancla_tipo, ancla_id, grupo_invitado_id.",
        ),
        Emision(
            "grupos.invitacion_aceptada",
            "El grupo invitado ha aceptado la invitación. Datos: los de grupos.invitacion_creada.",
        ),
        Emision(
            "grupos.invitacion_rechazada",
            "El grupo invitado ha rechazado la invitación. Datos: los de grupos.invitacion_creada.",
        ),
        Emision(
            "grupos.invitacion_retirada",
            "El grupo que invitó ha retirado la invitación. Datos: los de grupos.invitacion_creada.",
        ),
    )
    # Notificaciones que manda el módulo (las reparte «comunicaciones»; ver grupos/avisos.py).
    avisos = (
        TipoDeAviso("grupos.admitido", "Te han admitido en un grupo", "grupos", "grupos.admitido", "grupos.avisos.admitido"),
        TipoDeAviso("grupos.rol_cambiado", "Ha cambiado tu rol en un grupo", "grupos", "grupos.rol_cambiado", "grupos.avisos.rol_cambiado"),
        TipoDeAviso(
            "grupos.admin_de_organizacion", "Te han nombrado admin de una organización", "grupos",
            "grupos.admin_de_organizacion_nombrado", "grupos.avisos.admin_de_organizacion",
        ),
        TipoDeAviso(
            "grupos.invitacion_recibida", "Otra organización ha invitado a un grupo que administras", "grupos",
            "grupos.invitacion_creada", "grupos.avisos.invitacion_recibida",
        ),
        TipoDeAviso(
            "grupos.invitacion_aceptada", "Han aceptado una invitación de tu grupo", "grupos",
            "grupos.invitacion_aceptada", "grupos.avisos.invitacion_respondida",
        ),
        TipoDeAviso(
            "grupos.invitacion_rechazada", "Han rechazado una invitación de tu grupo", "grupos",
            "grupos.invitacion_rechazada", "grupos.avisos.invitacion_respondida",
        ),
    )
    # Lo que se puede pedir a un grupo con apoyos (lo gestiona «solicitudes»; ver grupos/solicitudes.py).
    # Entrar en un grupo: el sí de su administración y 2 apoyos de sus miembros en 15 días; o el sí del
    # superadmin, que basta (13 de noviembre de 2026, a petición de la persona usuaria).
    solicitudes = (
        TipoDeSolicitud(
            "grupos.entrar", "Entrar en un grupo", resolver="grupos.solicitudes.entrar", apoyos=2, dias=15,
            aprobacion="grupos.admitir", basta_el_superadmin=True, solo_miembros=False,
            comprobar="grupos.solicitudes.puede_pedir_entrar", generica=True,
        ),
    )
    permisos = (
        # Ver quién está en el grupo (13 de noviembre de 2026, a petición de la persona usuaria). Además,
        # cada organización puede cerrarlo para sus grupos (Organizacion.miembros_ven_miembros).
        Permiso(
            "grupos.ver_miembros",
            "Ver la lista de miembros del grupo y de sus subgrupos",
            roles=("usuario", "admin_grupo", "admin_org"),
        ),
        Permiso(
            "grupos.ver_arbol",
            "Ver el árbol de los grupos que administra, con sus subgrupos, en «Administrar → Grupos que administro → Árbol»",
            roles=("admin_grupo", "admin_org"),
        ),
        Permiso("grupos.editar_grupo", "Editar los datos del grupo", roles=("admin_grupo", "admin_org")),
        Permiso("grupos.crear_subgrupo", "Crear subgrupos dentro del grupo", roles=("admin_grupo", "admin_org")),
        Permiso("grupos.admitir", "Admitir personas en el grupo o sacarlas de él", roles=("admin_grupo", "admin_org")),
        Permiso("grupos.nombrar_admin_grupo", "Nombrar o quitar admins del grupo", roles=("admin_org",)),
        Permiso("grupos.editar_organizacion", "Editar los datos de la organización", roles=("admin_org",)),
        # Cuánto tiempo sin actividad marca a alguien en «Miembros» ([A-55]): solo puede bajar el de la plataforma.
        Permiso(
            "grupos.limitar_inactividad",
            "Bajar el tiempo sin actividad que marca a alguien en «Miembros» (en la organización o el grupo)",
            roles=("admin_grupo", "admin_org"),
        ),
        # Invitar a otra organización abre una puerta entre las dos: solo con privilegios (13 de noviembre
        # de 2026, a petición de la persona usuaria).
        Permiso(
            "grupos.invitar",
            "Invitar a un grupo de otra organización a algo del grupo",
            roles=("admin_grupo", "admin_org"),
        ),
        Permiso(
            "grupos.responder_invitacion",
            "Aceptar o rechazar las invitaciones de otras organizaciones al grupo",
            roles=("admin_grupo",),
        ),
    )
    datos_de_ejemplo = DatosDeEjemplo(crear="grupos.ejemplos.crear", borrar="grupos.ejemplos.borrar")
    # Sección «Organizaciones y grupos» (13 de noviembre de 2026): la ven todas las personas; «Árbol», solo
    # quien administra algo. Las fichas de grupo y de organización cuelgan de la sección principal.
    # Sus recuadros de la portada (Inicio); dónde sale cada uno lo decide config/inicio.py.
    tarjetas_de_inicio = (
        TarjetaDeInicio("grupos.mis_grupos", "Mis grupos", "grupos.inicio.mis_grupos", icono="◉", color="#059669"),
    )
    menu = (
        EntradaDeMenu(
            codigo="grupos.organizaciones",
            nombre="Organizaciones y grupos",
            url="grupos:mis_grupos",
            icono="⬢",
            color="#16a34a",
            otras_rutas=("grupos:grupo", "grupos:organizacion"),
        ),
        # Las demás entradas; dónde va cada una lo decide config/menu.py: las de lo propio, en
        # «Organizaciones y grupos → Mis grupos»; las de administrar, en «Administrar».
        EntradaDeMenu(
            codigo="grupos.mios",
            nombre="Mis grupos",
            url="grupos:mis_grupos",
            icono="◉",
            color="#059669",
        ),
        EntradaDeMenu(
            codigo="grupos.mis_grupos",
            nombre="Árboles",
            url="grupos:mis_grupos",
            icono="⚲",
            color="#047858",
        ),
        EntradaDeMenu(
            codigo="grupos.grafo",
            nombre="Grafo",
            url="grupos:grafo",
            icono="⌘",
            color="#9d174d",
        ),
        EntradaDeMenu(
            codigo="grupos.relaciones",
            nombre="Relaciones",
            url="grupos:relaciones",
            icono="⇄",
            color="#0d9488",
        ),
        EntradaDeMenu(
            codigo="grupos.arbol",
            nombre="Árbol",
            url="grupos:arbol",
            icono="⋔",
            color="#65a30d",
            permiso="grupos.ver_arbol",
        ),
        # «Administrar → Grupos que administro → Miembros» (grupos/miembros.py).
        EntradaDeMenu(
            codigo="grupos.miembros", nombre="Miembros", url="grupos:miembros", icono="☰", color="#c2410d", permiso="grupos.ver_arbol",
        ),
        # «Administrar → Mi organización → Inactividad» (grupos/views.py, inactividad).
        EntradaDeMenu(
            codigo="grupos.inactividad", nombre="Inactividad", url="grupos:inactividad", icono="⧖", color="#78350f",
            permiso="grupos.limitar_inactividad",
        ),
        EntradaDeMenu(
            codigo="grupos.invitaciones",
            nombre="Invitaciones entre grupos",
            url="grupos:invitaciones",
            icono="✉",
            color="#d97706",
            permiso="grupos.invitar",
            contador="grupos.contadores.invitaciones_pendientes",
        ),
        EntradaDeMenu(
            codigo="grupos.mi_organizacion",
            nombre="Datos",
            url="grupos:mis_organizaciones",
            icono="⬡",
            color="#166535",
            permiso="grupos.editar_organizacion",
        ),
    )
    ayuda = (
        Ayuda(
            seccion="grupos.organizaciones",
            titulo="Organizaciones y grupos",
            texto=(
                "Dónde está cada cual. Una organización (ORG) es independiente de las demás; dentro tiene grupos "
                "(GRU), que pueden contener subgrupos a cualquier profundidad. Quien está en un grupo cuenta "
                "también como miembro de los grupos que lo contienen.\n\n"
                "En la ficha de un grupo se ven su camino, sus subgrupos, sus admins y, si la organización lo "
                "permite, la lista de sus miembros. Quien lo administra puede además cambiar sus datos, crear "
                "subgrupos, admitir o sacar personas y cambiar su rol."
            ),
        ),
        Ayuda(
            seccion="grupos.mis_grupos",
            titulo="Mis grupos: árboles",
            texto=(
                "Los grupos en los que estás, por organización y en forma de árbol. Los que salen en gris no los "
                "has elegido tú: contienen a uno de los tuyos, así que también eres miembro de ellos (por "
                "herencia). «Asamblea base» (fondo amarillo) es tu grupo más local, el que te valida; solo hay una por "
                "persona. La organización sale en violeta.\n\n"
                "Pulsa un grupo para ver su ficha: arriba verás el mismo árbol, con ese grupo en un recuadro rojo."
            ),
        ),
        Ayuda(
            seccion="grupos.arbol",
            titulo="Árbol",
            texto=(
                "Los grupos que administras, con todos sus subgrupos: el superadmin ve todos; el admin de una "
                "organización, la suya entera; el admin de un grupo, su rama. «Personas» cuenta a cada persona "
                "una vez, aunque esté en varios subgrupos.\n\n"
                "Arriba están las organizaciones: pulsa una para cambiar sus datos, sus admins y si sus miembros "
                "ven la lista de miembros. El superadmin crea aquí las organizaciones nuevas."
            ),
        ),
        Ayuda(
            seccion="grupos.mi_organizacion",
            titulo="Datos de la organización",
            texto=(
                "Las organizaciones que administras. Pulsa una para cambiar su nombre y su descripción, sus "
                "admins y si sus miembros ven la lista de miembros de sus grupos."
            ),
        ),
        Ayuda(
            seccion="grupos.relaciones",
            titulo="Relaciones",
            texto=(
                "Relaciones libres entre grupos de una misma organización («colabora con», «nació de»…). No dan "
                "ni quitan permisos: solo «contiene» (un grupo dentro de otro) cambia quién ve qué. Ves las de "
                "tus grupos y las de los que administras; las crea o borra quien puede editar uno de los dos "
                "grupos. Más adelante se verán también en un grafo."
            ),
        ),
        Ayuda(
            seccion="grupos.invitaciones",
            titulo="Invitaciones entre grupos",
            texto=(
                "No son solicitudes para entrar en un grupo (eso está en «Comunicaciones → Solicitudes»): son "
                "invitaciones de un grupo a un grupo de otra organización para algo concreto (por ejemplo, un "
                "proyecto conjunto). Aceptarla solo abre eso: nadie cambia de grupo ni de organización.\n\n"
                "El número del menú son las pendientes que puedes responder tú (de entrada, el admin del grupo "
                "invitado). Las invitaciones se hacen desde lo que se comparte (un proyecto…), no desde aquí; "
                "aquí se aceptan, se rechazan o se retiran."
            ),
        ),
    )

    # Al arrancar: conecta las señales que ponen al día el número de invitaciones del menú.
    def ready(self):
        from . import senales  # noqa: F401 (importarlo basta para conectar sus señales)
