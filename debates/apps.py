"""
Configuración y contrato del módulo «debates».
"""

from base.contrato import Ancla, Ayuda, Capa, Colgante, Cometido, DatosDeEjemplo, Emision, EntradaDeMenu, ModuloConfig, Permiso, TipoDeSolicitud


class DebatesConfig(ModuloConfig):
    """
    Contrato del módulo «debates»: una pregunta con varias opciones en columnas, argumentos con alias, votos
    que solo se ven como recuentos, opciones nuevas que se abren con apoyos, límites en cascada y facilitación
    (docs/diseno.md, apartado 11). Se abre con una solicitud con apoyos; al cerrarse, su conclusión pasa al
    registro de decisiones.
    """

    name = "debates"
    verbose_name = "Debates"
    capa = Capa.FUNCIONAL
    datos_de_ejemplo = DatosDeEjemplo(crear="debates.ejemplos.crear", borrar="debates.ejemplos.borrar")
    descripcion = (
        "Debates de los grupos: una pregunta con dos o más opciones que se discuten en paralelo, argumentos a favor "
        "y en contra (con alias), votos que solo se ven como recuentos (⭐ 👍 👎 ⛔ y, en los argumentos, 🔁 🚫), "
        "«todas me valen», opciones nuevas que se abren con apoyos, límites blandos y duros, y facilitación."
    )
    anclas = (Ancla("debates.debate", "debates.Debate", "Un debate"),)
    permisos = (
        Permiso("debates.abrir", "Proponer debates en el grupo (se abren con apoyos)", roles=("usuario", "admin_grupo", "admin_org")),
        Permiso("debates.limitar", "Poner los límites de los debates de la organización o del grupo", roles=("admin_org", "admin_grupo")),
    )
    cometidos = (
        Cometido("debates.facilitacion", "Facilitación", "Cuida el debate: amplía quién participa, da la facilitación a otras personas y lo cierra con una conclusión."),
    )
    solicitudes = (
        TipoDeSolicitud("debates.abrir", "Abrir un debate", resolver="debates.servicios.abrir", apoyos=2, dias=15, basta_el_superadmin=True),
    )
    emite = (
        Emision(
            "debates.cerrado",
            "Se ha cerrado un debate con su conclusión. Datos: texto, forma, detalle, grupo_id, audiencia_id, origen_tipo, origen_id, enlace, tomada.",
        ),
    )
    # Un debate puede colgar de una reunión, de un proyecto, de un acta (un tema pendiente) o de otro debate.
    colgantes = (
        Colgante(
            "debates.debates", "Debates", ("eventos.evento", "proyectos.proyecto", "documentos.documento", "debates.debate"),
            "debates.servicios.colgantes", crear="debates:nuevo", texto_crear="+ Debate",
        ),
    )
    menu = (
        EntradaDeMenu(
            codigo="debates.debates", nombre="Debates", url="debates:lista", icono="❞", color="#a21caf",
            otras_rutas=("debates:nuevo", "debates:debate"),
        ),
        EntradaDeMenu(
            codigo="debates.limites", nombre="Debates", url="debates:limites", icono="⚟", color="#86198e", permiso="debates.limitar",
        ),
    )
    ayuda = (
        Ayuda(
            seccion="debates.debates",
            titulo="Debates",
            texto=(
                "Una pregunta con varias opciones, cada una en su columna. En cada opción y en cada argumento puedes "
                "votar ⭐ muy importante, 👍 apoyo, 👎 en contra o ⛔ oposición total (⭐ y ⛔ con una justificación breve, "
                "que sale sin tu nombre); en los argumentos, también 🔁 repetitivo y 🚫 no tiene que ver. Los argumentos "
                "llevan tu alias; los votos solo se ven como recuentos.\n\n"
                "Puedes proponer otra opción: se abre cuando la apoyan otras personas. Si todas te parecen bien, pulsa "
                "🤝. Quien facilita lo amplía a más gente y lo cierra con una conclusión, que pasa al registro de "
                "decisiones."
            ),
            ejemplo="«¿Dónde hacemos el huerto?»: tres columnas (el solar, la azotea, el parque), cada una con sus argumentos.",
        ),
        Ayuda(
            seccion="debates.limites",
            titulo="Límites de los debates",
            texto=(
                "Palabras por intervención, intervenciones por persona, opciones nuevas por persona y apoyos para abrir "
                "una opción. Al pasar el límite blando se permite una intervención más, muy marcada; al llegar al duro, "
                "ya no. Los pone el superadmin (toda la plataforma), la administración de cada organización y de cada "
                "grupo (vale también en sus subgrupos) y quien facilita cada debate; vale siempre el más estricto."
            ),
        ),
    )
