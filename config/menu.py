"""
Disposición del menú izquierdo: el único sitio donde se decide en qué orden sale cada entrada, dentro de
qué sección va y en qué bloque (ver docs/diseno.md, apartado 4, «Disposición del menú» y «Menú en tres
bloques»).

Cada módulo declara en su contrato (apps.py) las entradas que aporta: nombre, dirección, icono, color,
permiso, vistas… Aquí solo se colocan, por su código. Para reordenar el menú se mueve una línea; para
llevar una subsección a otra sección se mueve dentro de los paréntesis de esa sección.

Cómo se escribe cada elemento:
  - «"usuarios.contrasena"»: una entrada sin subsecciones.
  - «("ayuda.ayuda", ("ayuda.como_se_hace", …))»: una entrada con sus subsecciones en el menú de la
    izquierda, en este orden (y cada una puede tener las suyas, igual, a cualquier profundidad).
  - «Pestanas("calendario.calendario", ("calendario.ver", …))»: una entrada cuyas subsecciones salen como
    pestañas arriba (no en el menú de la izquierda). Sirve para juntar pantallas de módulos distintos.
  - «Bloque("Administrar", "administrar", (…), banda="…")»: un bloque del menú con su título, su color y la
    frase de la banda que sale arriba en sus pantallas. Todo el menú va en bloques.

Las herramientas que aún no existen están en el módulo «proximamente» (proximamente.*): salen en el menú y,
al pulsarlas, dicen que aún están vacías. Cuando se construye una, se cambia aquí su código por el de su
módulo.

Al arrancar (y con «python manage.py check»), el registro avisa si una entrada declarada no está aquí,
si aquí se nombra una que nadie declara o si una sale dos veces. Lo lee base/apps.py a través del ajuste
DISPOSICION_DEL_MENU de config/settings.py.

Quién ve cada entrada no se decide aquí, sino en su contrato (permiso): una sección cuyas subsecciones (o
pestañas) están todas ocultas tampoco se muestra, y un bloque sin nada que ver, tampoco.
"""

from base.disposicion import Bloque, Pestanas

DISPOSICION = (
    # ── Lo propio (todo el mundo) ──────────────────────────────────────────────────────────────────────
    Bloque("", "", (
        "base.inicio",
        Pestanas("calendario.calendario", (
            "calendario.ver",
            "eventos.lista",
            "eventos.mios",
            "eventos.convocar",
        )),
        ("comunicaciones.comunicaciones", (
            "comunicaciones.notificaciones",
            Pestanas("comunicaciones.conversar", (
                "comunicaciones.conversaciones",
                "proximamente.con_grupos",
                "proximamente.con_personas",
            )),
            Pestanas("solicitudes.solicitudes", (
                "solicitudes.mias",
                "solicitudes.pendientes",
                "talentos.peticiones",
                "solicitudes.pasadas",
            )),
        )),
        ("proyectos.seccion", (
            "proyectos.tareas",
            "proyectos.proyectos",
        )),
        ("decisiones.participacion", (
            "debates.debates",
            "consultas.consultas",
            "documentos.documentos",
            Pestanas("documentos.biblioteca", (
                "documentos.plantillas",
                "documentos.membretes",
                "documentos.imagenes",
            )),
            "documentos.fragmentos",
            "decisiones.decisiones",
        )),
        ("grupos.organizaciones", (
            Pestanas("grupos.mios", (
                "grupos.mis_grupos",
                "grupos.grafo",
                "grupos.relaciones",
                "talentos.del_grupo",
            )),
            "lugares.mapa",
        )),
        # «Ayuda» siempre antes que «Configuración de mi cuenta» (a petición de la persona usuaria).
        ("ayuda.ayuda", (
            "ayuda.como_se_hace",
            "ayuda.plataforma",
            "ayuda.guias",
        )),
        ("usuarios.cuenta", (
            "usuarios.usabilidad",
            Pestanas("usuarios.mis_datos", (
                "usuarios.datos",
                "talentos.mios",
                "lugares.mi_lugar",
            )),
            "comunicaciones.preferencias",
            "usuarios.contrasena",
            Pestanas("limpieza.archivo", (
                "limpieza.archivados",
                "limpieza.borrados",
            )),
        )),
    )),
    # ── Administrar (admin de grupo y de organización: cada cual ve solo lo que administra) ───────────
    Bloque("Administrar", "administrar", (
        Pestanas("administracion.grupos", (
            "grupos.arbol",
            "grupos.miembros",
            "grupos.invitaciones",
        )),
        Pestanas("administracion.buzon", (
            "comunicaciones.atendidas",
            "comunicaciones.avisos",
        )),
        "solicitudes.por_aprobar",
        Pestanas("administracion.eventos_y_talentos", (
            "eventos.administrados",
            "talentos.pedir",
        )),
        "proximamente.moderacion",
        Pestanas("administracion.organizacion", (
            "grupos.mi_organizacion",
            "audiencias.visibilidad",
            "tipologias.tipologias",
            "etiquetas.etiquetas",
            "solicitudes.ajustes",
            "debates.limites",
            "documentos.limites",
            "grupos.inactividad",
            "lugares.configuracion",
            "proximamente.web_publica",
        )),
    ), banda="Estás administrando: lo que hagas aquí afecta a los grupos y a las personas que administras."),
    # ── Plataforma (solo el superadmin) ────────────────────────────────────────────────────────────────
    Bloque("Plataforma", "plataforma", (
        ("administracion.usuarios", (
            "administracion.boveda",
            "administracion.alias",
            "administracion.roles",
        )),
        Pestanas("administracion.catalogos", (
            "lugares.gestion",
            "talentos.catalogo",
            "comunicaciones.niveles",
        )),
        "limpieza.plazos",
        ("mantenimiento.desarrollo", (
            "mantenimiento.pruebas",
            "mantenimiento.trastienda",
            "base.componentes",
        )),
    ), banda="Estás en la administración de la plataforma: lo que cambies aquí afecta a todas las organizaciones."),
)
