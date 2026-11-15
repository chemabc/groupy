"""
Configuración y contrato del módulo «documentos».
"""

from base.contrato import Ancla, Ayuda, Capa, Colgante, Cometido, DatosDeEjemplo, Emision, EntradaDeMenu, ModuloConfig, Permiso, TextoEditable


class DocumentosConfig(ModuloConfig):
    """
    Contrato del módulo «documentos»: órdenes del día, actas y documentos libres en Markdown, con la autoría
    de cada párrafo, el registro de cambios que nadie borra, comentarios y aprobación (docs/diseno.md,
    apartado 13). Al aprobar un acta, sus acuerdos se anuncian para el registro de decisiones.
    """

    name = "documentos"
    verbose_name = "Documentos"
    capa = Capa.FUNCIONAL
    datos_de_ejemplo = DatosDeEjemplo(crear="documentos.ejemplos.crear", borrar="documentos.ejemplos.borrar")
    descripcion = (
        "Órdenes del día y actas de las reuniones (y documentos libres), escritos en Markdown por quien tiene la "
        "redacción o la toma de acta, con quién ha escrito cada párrafo y un registro de cambios que nadie puede "
        "borrar. El acta parte de su orden del día y, al aprobarse, sus acuerdos pasan al registro de decisiones."
    )
    anclas = (Ancla("documentos.documento", "documentos.Documento", "Un orden del día, un acta o un documento"),)
    permisos = (
        Permiso("documentos.crear", "Crear órdenes del día, actas y documentos del grupo", roles=("usuario", "admin_grupo", "admin_org")),
        Permiso("documentos.limitar", "Poner cuántas personas escriben y comentan a la vez (organización, grupo o documento)", roles=("admin_grupo", "admin_org")),
    )
    cometidos = (
        Cometido("documentos.redaccion", "Redacción", "Escribe el documento (tantas personas como digan sus límites; de partida, 10); las demás lo comentan."),
    )
    emite = (
        Emision(
            "documentos.acuerdo_tomado",
            "Un acta aprobada lleva un acuerdo. Datos: texto, forma, detalle, grupo_id, audiencia_id, origen_tipo, origen_id, enlace, tomada.",
        ),
    )
    # Los documentos pueden colgar de una reunión (sus órdenes del día y actas) o de un proyecto.
    # El texto de cada documento se escribe en el editor colaborativo en tiempo real, si lo hay.
    textos_editables = (
        TextoEditable(
            "documentos.documento", permiso="documentos.servicios.permiso_en_editor", texto="documentos.servicios.texto_para_editor",
            guardar="documentos.servicios.guardar_desde_editor", opciones="documentos.servicios.opciones_para_editor",
        ),
    )
    colgantes = (
        Colgante(
            "documentos.documentos", "Órdenes del día y actas", ("eventos.evento", "proyectos.proyecto"), "documentos.servicios.colgantes",
            crear="documentos:nuevo", texto_crear="+ Documento",
        ),
    )
    menu = (
        EntradaDeMenu(
            codigo="documentos.documentos", nombre="Órdenes del día y actas", url="documentos:lista", icono="✍", color="#4d7c10",
            otras_rutas=("documentos:nuevo", "documentos:documento", "documentos:escribir"),
        ),
        EntradaDeMenu(
            codigo="documentos.limites", nombre="Documentos", url="documentos:limites", icono="✐", color="#5b6c1f", permiso="documentos.limitar",
        ),
    )
    ayuda = (
        Ayuda(
            seccion="documentos.documentos",
            titulo="Órdenes del día y actas",
            texto=(
                "Los órdenes del día y las actas de las reuniones de tus grupos, y otros documentos. Los escriben "
                "quienes tienen la redacción (o la toma de acta de la reunión); quien los ve puede comentarlos hasta "
                "que se aprueban.\n\n"
                "El acta se crea desde su orden del día: copia los puntos y añade «Acuerdos alcanzados» y «Temas a "
                "discutir en la próxima reunión». Detrás de cada párrafo sale quién lo ha escrito, y arriba el "
                "registro de cambios, que nadie puede borrar. Al aprobar el acta, sus acuerdos pasan al registro de "
                "decisiones."
            ),
            ejemplo="Lince tiene la toma de acta de la asamblea: abre su orden del día, pulsa «Crear el acta» y la completa durante la reunión.",
        ),
        Ayuda(
            seccion="documentos.limites",
            titulo="Límites de los documentos",
            texto=(
                "Cuántas personas pueden tener la redacción de un documento y escribir a la vez, y cuántas pueden estar "
                "comentando a la vez en el editor en tiempo real. Los pone el superadmin (toda la plataforma), la "
                "administración de cada organización y de cada grupo (vale también en sus subgrupos) y, en las «Opciones» "
                "de cada documento, la administración de su grupo. Vale siempre el más estricto. Quien llega de más entra "
                "a leer."
            ),
        ),
    )
