"""
Configuración y contrato del módulo «decisiones».
"""

from base.contrato import Ayuda, Capa, DatosDeEjemplo, EntradaDeMenu, Escucha, Modo, ModuloConfig, Permiso, Vista


class DecisionesConfig(ModuloConfig):
    """
    Contrato del módulo «decisiones»: el registro común de lo que deciden los grupos (docs/diseno.md,
    apartado 16). Se llena solo: escucha los acuerdos de las actas, el cierre de los debates y el de las
    consultas, que llegan como eventos_sw con todos los datos (así no importa esos módulos).
    """

    name = "decisiones"
    verbose_name = "Decisiones"
    capa = Capa.FUNCIONAL
    datos_de_ejemplo = DatosDeEjemplo(crear="", borrar="decisiones.ejemplos.borrar")
    descripcion = (
        "Registro común de las decisiones de los grupos: acuerdos de las actas, debates cerrados y resultados "
        "de las consultas, cada una con su origen. Si una decisión se vuelve a tomar, la antigua queda "
        "«sustituida por…» y nunca se borra."
    )
    permisos = (
        Permiso("decisiones.sustituir", "Marcar una decisión del grupo como sustituida por otra", roles=("admin_grupo", "admin_org")),
    )
    # Las tres llegan con los mismos datos (ver decisiones/servicios.py, registrar), en la misma
    # transacción que las provoca.
    escucha = (
        Escucha("documentos.acuerdo_tomado", "decisiones.servicios.registrar", Modo.SINCRONO),
        Escucha("debates.cerrado", "decisiones.servicios.registrar", Modo.SINCRONO),
        Escucha("consultas.cerrada", "decisiones.servicios.registrar", Modo.SINCRONO),
    )
    menu = (
        # La sección «Participación» del menú, que junta debates, consultas, órdenes del día y actas y
        # decisiones (ver config/menu.py). Al pulsarla se abren los debates.
        EntradaDeMenu(codigo="decisiones.participacion", nombre="Participación", url="debates:lista", icono="⚘", color="#be123d"),
        EntradaDeMenu(
            codigo="decisiones.decisiones", nombre="Decisiones", url="decisiones:lista", icono="⚐", color="#854d0e",
            otras_rutas=("decisiones:decision",),
            vistas=(Vista("Vigentes", "decisiones:lista"), Vista("Todas", "decisiones:todas")),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="decisiones.participacion",
            titulo="Participación",
            texto=(
                "Donde los grupos deciden: «Debates» (una pregunta con varias opciones, con argumentos y votos), "
                "«Consultas» (votaciones secretas), «Órdenes del día y actas» (de las reuniones) y «Decisiones» (el "
                "registro común de lo decidido, que se llena solo)."
            ),
        ),
        Ayuda(
            seccion="decisiones.decisiones",
            titulo="Decisiones",
            texto=(
                "Lo que han decidido tus grupos, en un solo sitio: los acuerdos de las actas aprobadas, los debates "
                "cerrados y los resultados de las consultas. Cada decisión lleva a su origen.\n\n"
                "«Vigentes» esconde las que se han sustituido por otra más nueva; «Todas» las enseña también. Nada "
                "se borra nunca."
            ),
            ejemplo="En el acta del jueves se acordó cambiar el local; la decisión antigua sobre el local queda «sustituida por» la nueva.",
        ),
    )
