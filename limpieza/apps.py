"""
Configuración y contrato del módulo «limpieza».
"""

from base.contrato import Ayuda, Capa, Emision, EntradaDeMenu, ModuloConfig, Permiso, TareaDiaria, TipoDeAviso, Vista


class LimpiezaConfig(ModuloConfig):
    """
    Contrato del módulo «limpieza»: cada día archiva lo terminado hace tiempo (sale de las listas), avisa
    quince días antes de borrarlo, deja conservarlo y lo borra pasado el plazo, con un registro visible
    de lo borrado. Los tipos de elemento los declaran los demás módulos (Limpiable) y los plazos los
    elige el superadmin. Ver docs/diseno.md, apartado 14.3.
    """

    name = "limpieza"
    verbose_name = "Limpieza"
    capa = Capa.FUNCIONAL
    descripcion = (
        "Archiva lo terminado hace tiempo (proyectos finalizados, tareas hechas, eventos y recordatorios pasados) y lo "
        "borra pasado un plazo, avisando antes a quienes lo ven, que pueden conservarlo; borra las notificaciones "
        "viejas; y guarda un registro visible de lo borrado. El superadmin elige los plazos y puede podar a mano."
    )
    # Sin roles por defecto: solo el superadmin.
    permisos = (Permiso("limpieza.configurar", "Elegir los plazos de la limpieza (cuándo se archiva y cuándo se borra cada cosa)"),)
    tareas_diarias = (
        TareaDiaria(
            "limpieza.limpiar",
            "Archivar lo terminado, avisar de lo que se va a borrar y borrar lo que ha cumplido su plazo.",
            "limpieza.servicios.limpiar",
        ),
    )
    emite = (
        Emision("limpieza.archivados", "Se han archivado elementos. Datos: archivados (ids de Archivado)."),
        Emision("limpieza.se_borraran", "Unos elementos archivados se borrarán dentro de 15 días. Datos: archivados (ids de Archivado)."),
    )
    avisos = (
        TipoDeAviso("limpieza.archivados", "Se archiva algo que veo", "sistema", "limpieza.archivados", "limpieza.avisos.archivados"),
        TipoDeAviso("limpieza.se_borraran", "Se va a borrar algo archivado que veo", "sistema", "limpieza.se_borraran", "limpieza.avisos.se_borraran"),
    )
    menu = (
        EntradaDeMenu(
            codigo="limpieza.archivo",
            nombre="Archivo",
            url="limpieza:archivados",
            icono="⌸",
            color="#44403c",
            orden=190,
            subsecciones=(
                EntradaDeMenu(
                    codigo="limpieza.archivados", nombre="Archivados", url="limpieza:archivados", icono="⊟", color="#713f12",
                    vistas=(Vista("Archivados", "limpieza:archivados"),),
                ),
                EntradaDeMenu(
                    codigo="limpieza.borrados", nombre="Borrados", url="limpieza:borrados", icono="⊘", color="#9f1239",
                    vistas=(Vista("Registro de borrados", "limpieza:borrados"),),
                ),
            ),
        ),
        EntradaDeMenu(
            codigo="limpieza.plazos",
            nombre="Limpieza",
            url="limpieza:plazos",
            icono="♺",
            color="#115e59",
            permiso="limpieza.configurar",
            dentro_de="tipologias.configuracion",
            orden=80,
            vistas=(Vista("Plazos", "limpieza:plazos"),),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="limpieza.archivo",
            titulo="Archivo",
            texto=(
                "Lo terminado hace tiempo (proyectos finalizados, tareas hechas, eventos y recordatorios pasados) sale de "
                "las listas y queda aquí. Pasado un plazo se borra, pero antes se avisa a quienes lo ven."
            ),
        ),
        Ayuda(
            seccion="limpieza.archivados",
            titulo="Archivados",
            texto=(
                "Lo archivado que puedes ver, con el día aproximado en que se borrará. Lo sigues abriendo por su enlace. "
                "Si algo merece quedarse, pulsa «Conservar»: seguirá archivado, pero no se borrará solo."
            ),
        ),
        Ayuda(
            seccion="limpieza.borrados",
            titulo="Borrados",
            texto="El registro de lo que se ha borrado de lo que veías: qué era, cuándo se archivó y cuándo y por qué se borró.",
        ),
        Ayuda(
            seccion="limpieza.plazos",
            titulo="Limpieza",
            texto=(
                "Cuántos días pasan desde que algo termina hasta archivarlo, y desde que se archiva hasta borrarlo, para "
                "cada tipo. Las notificaciones se borran sin archivar. Desmarca «Activo» para que un tipo no se limpie."
            ),
        ),
    )
