"""
Configuración y contrato del módulo «publico».
"""

from base.contrato import (
    Ancla,
    Ayuda,
    Capa,
    DatosDeEjemplo,
    Emision,
    EnlaceDeCabecera,
    EntradaDeMenu,
    ModuloConfig,
    Permiso,
    TextoEditable,
    TipoDeAviso,
    Vista,
)


class PublicoConfig(ModuloConfig):
    """
    Contrato del módulo «publico»: la portada pública (de la plataforma y de cada organización, sin sesión) y
    las miniwebs de los grupos, que ve cada grupo y lo que cuelga de él, más los grupos que reciben sus
    páginas por una relación de publicación y consumo (docs/diseno.md, apartado 15).
    """

    name = "publico"
    verbose_name = "Webs y portada pública"
    capa = Capa.FUNCIONAL
    descripcion = (
        "Portada pública de la plataforma y de cada organización (sin sesión, con pestañas y «Entrar»), y miniwebs "
        "de los grupos y organizaciones: páginas en Markdown escritas en el editor y publicadas como una foto en "
        "HTML seguro, que ve el grupo y lo que cuelga de él. Con relaciones de publicación y consumo entre grupos, "
        "novedades y un visor con barra de camino («🌐 Webs», arriba, fuera del menú de la izquierda)."
    )
    datos_de_ejemplo = DatosDeEjemplo(crear="publico.ejemplos.crear", borrar="publico.ejemplos.borrar")
    anclas = (Ancla("publico.pagina", "publico.Pagina", "Una página de una web (portada o miniweb)"),)
    permisos = (
        Permiso("publico.publicar", "Crear, escribir y publicar las páginas de la web del grupo u organización", roles=("admin_grupo", "admin_org")),
    )
    emite = (
        Emision("publico.publicada", "Se ha publicado por primera vez una página interna. Datos: pagina_id, autor_id."),
        Emision("publico.relacion_propuesta", "Un grupo propone publicar sus páginas para otro. Datos: relacion_id."),
    )
    avisos = (
        TipoDeAviso("publico.publicada", "Un grupo ha publicado una página nueva en su web", "grupos", "publico.publicada", "publico.avisos.publicada"),
        TipoDeAviso(
            "publico.relacion_propuesta", "Un grupo quiere publicar sus páginas para uno que administro", "grupos",
            "publico.relacion_propuesta", "publico.avisos.relacion_propuesta",
        ),
    )
    # El borrador de cada página se escribe en el editor en tiempo real, si lo hay.
    textos_editables = (
        TextoEditable(
            "publico.pagina", permiso="publico.servicios.permiso_en_editor", texto="publico.servicios.texto_para_editor",
            guardar="publico.servicios.guardar_desde_editor", opciones="publico.servicios.opciones_para_editor",
        ),
    )
    # El botón «🌐 Webs» de la cabecera, con el número de novedades.
    enlaces_de_cabecera = (
        EnlaceDeCabecera(
            "publico.webs", "Webs", "publico:webs", icono="🌐", titulo="Las webs de tus grupos y organizaciones",
            contador="publico.servicios.novedades_sin_ver",
        ),
    )
    menu = (
        # En «Administrar» (dónde, lo decide config/menu.py): las páginas que gestiono y las relaciones.
        EntradaDeMenu(codigo="publico.administrar", nombre="Webs", url="publico:paginas", icono="⌂", color="#155e75", permiso="publico.publicar"),
        EntradaDeMenu(
            codigo="publico.paginas", nombre="Páginas", url="publico:paginas", icono="▭", color="#0891b2", permiso="publico.publicar",
            otras_rutas=("publico:editar", "publico:escribir"), vistas=(Vista("Mis páginas", "publico:paginas"),),
        ),
        EntradaDeMenu(
            codigo="publico.relaciones", nombre="Publicación y consumo", url="publico:relaciones", icono="⇶", color="#075985",
            permiso="publico.publicar", vistas=(Vista("Relaciones", "publico:relaciones"),),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="publico.paginas",
            titulo="Páginas de las webs",
            texto=(
                "Las páginas de las webs que administras: la de cada grupo (la ven el grupo y los que cuelgan de "
                "él), la de tu organización (interna, para todos sus grupos, o pública: sale en su portada, sin "
                "sesión) y, si eres superadmin, la portada de la plataforma.\n\n"
                "Cada página es una pestaña de su web. Se escribe en Markdown («## Título», «- punto», "
                "«**negrita**», «[enlace](dirección)») como borrador; nadie la ve hasta que pulsas «Publicar». "
                "Después puedes seguir cambiando el borrador: lo publicado no cambia hasta volver a publicar. Para "
                "poner una imagen, súbela en la página y copia lo que sale a su lado en el texto."
            ),
        ),
        Ayuda(
            seccion="publico.relaciones",
            titulo="Publicación y consumo",
            texto=(
                "Para que un grupo (por ejemplo, uno de actividad que no está en las asambleas) publique para otro: "
                "su administración lo propone y la del grupo que recibe lo acepta. Desde entonces, sus páginas las "
                "ven también ese grupo y los que cuelgan de él, y les salen en «Novedades». Cualquiera de las dos "
                "administraciones puede cortarla."
            ),
        ),
    )
