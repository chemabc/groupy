"""
Configuración y contrato del módulo «documentos».
"""

from base.contrato import (
    Ancla,
    Ayuda,
    Capa,
    Colgante,
    Cometido,
    DatosDeEjemplo,
    Emision,
    EntradaDeMenu,
    Limpiable,
    ModuloConfig,
    Permiso,
    TextoEditable,
    Vista,
)


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
        # Sin roles: solo el superadmin.
        Permiso("documentos.espacio", "Poner cuánto pueden ocupar los archivos de cada organización"),
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
            comentarios="documentos.servicios.guardar_comentarios_del_editor",
        ),
    )
    colgantes = (
        Colgante(
            "documentos.documentos", "Documentos",
            ("eventos.evento", "proyectos.proyecto", "proyectos.tarea", "debates.debate", "consultas.consulta"),
            "documentos.servicios.colgantes", crear="documentos:nuevo", texto_crear="+ Documento, archivo o enlace",
        ),
    )
    # Lo que lleva 30 días en la papelera se borra de verdad, con sus archivos (ver documentos/servicios.py).
    limpiables = (
        Limpiable(
            "documentos.papelera", "documentos.Documento", "Documentos en la papelera (días desde que se eliminaron)",
            borrar="documentos.servicios.vaciar_papelera", borrar_a=30,
        ),
    )
    menu = (
        EntradaDeMenu(
            codigo="documentos.documentos", nombre="Documentos", url="documentos:lista", icono="✍", color="#4d7c10",
            otras_rutas=("documentos:nuevo", "documentos:subir", "documentos:enlazar", "documentos:documento", "documentos:escribir", "documentos:version"),
            vistas=(
                Vista("Todos", "documentos:lista"),
                Vista("Nuevo", "documentos:nuevo"),
                Vista("Papelera", "documentos:papelera"),
            ),
        ),
        # La biblioteca del editor (ver documentos/views.py, biblioteca). Sus pestañas, en config/menu.py.
        EntradaDeMenu(codigo="documentos.biblioteca", nombre="Plantillas de documentos", url="documentos:plantillas", icono="⎘", color="#3d6b12"),
        EntradaDeMenu(codigo="documentos.plantillas", nombre="Plantillas", url="documentos:plantillas", icono="⊞", color="#4a5d23"),
        EntradaDeMenu(codigo="documentos.membretes", nombre="Cabeceras y pies", url="documentos:membretes", icono="⊤", color="#556b2f"),
        EntradaDeMenu(codigo="documentos.imagenes", nombre="Imágenes", url="documentos:imagenes", icono="⛶", color="#6b8e23"),
        EntradaDeMenu(codigo="documentos.fragmentos", nombre="Enciclopedia de fragmentos", url="documentos:fragmentos", icono="⧉", color="#2f5d0a"),
        EntradaDeMenu(
            codigo="documentos.espacio", nombre="Espacio para archivos", url="documentos:espacio", icono="⛁", color="#365314",
            permiso="documentos.espacio", vistas=(Vista("Por organización", "documentos:espacio"),),
        ),
        EntradaDeMenu(
            codigo="documentos.limites", nombre="Documentos", url="documentos:limites", icono="✐", color="#5b6c1f", permiso="documentos.limitar",
        ),
    )
    ayuda = (
        Ayuda(
            seccion="documentos.documentos",
            titulo="Documentos",
            texto=(
                "Todo lo que guardan tus grupos: textos (órdenes del día, actas y otros), archivos subidos (PDF, "
                "imágenes, documentos abiertos) y enlaces (a Drive u otras webs, o a otro documento). La lista se "
                "filtra por nombre, tipo, de dónde cuelga, grupo, estado y fechas.\n\n"
                "Los archivos guardan todas sus versiones. No se admiten formatos de Microsoft (docx, xlsx…): "
                "guárdalos como PDF o en formato abierto (odt, ods). Cada archivo pasa por el antivirus. "
                "«Eliminar» lo lleva a la papelera, de donde se recupera durante 30 días. Lo que cuelga de una "
                "votación queda congelado desde que se abre.\n\n"
                "Los órdenes del día y las actas de las reuniones los escriben "
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
            seccion="documentos.espacio",
            titulo="Espacio para archivos",
            texto=(
                "Cuánto pueden ocupar los archivos subidos de cada organización, con todas sus versiones y lo que "
                "hay en la papelera. El de «Toda la plataforma» vale para las organizaciones que no tienen el suyo. "
                "Al llegar al máximo, no se pueden subir más archivos hasta liberar espacio o ampliarlo."
            ),
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
