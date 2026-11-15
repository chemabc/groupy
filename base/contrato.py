"""
Contrato de módulo: la forma única en que cada módulo dice lo que aporta a la aplicación.

Cada módulo del proyecto tiene en su apps.py una clase que hereda de ModuloConfig y rellena sus
apartados: permisos, cometidos, anclas, huecos en fichas, fuentes del calendario, eventos_sw que emite y
que escucha, grupos de etiquetas, elementos que se pueden limpiar, datos de ejemplo, entradas de menú y
textos de ayuda «?». Ver docs/diseno.md, apartado 3.3.

Al arrancar, el registro (base/registro.py) lee todas esas clases una sola vez y las comprobaciones
(base/comprobaciones.py) avisan si algo está mal declarado.

Cada apartado se declara con una de las «fichas» de este fichero (clases pequeñas de solo datos). Son
inmutables (frozen=True): una vez leídas al arrancar, nadie puede cambiarlas por accidente.
"""

from dataclasses import dataclass, field
from enum import IntEnum

from django.apps import AppConfig


class Capa(IntEnum):
    """
    Capas de la aplicación, de abajo arriba. Un módulo solo puede depender de las capas inferiores, y un
    módulo funcional nunca de otro funcional (ver docs/diseno.md, apartado 3.2). El número sirve para
    comparar: cuanto más alto, más arriba está la capa.
    """

    # Piezas comunes que no dependen de nada: base, eventos_sw, anclas, etiquetas, tipologías, ejemplos.
    BASE = 1
    # Quién es cada cual: bóveda (identidad real) y usuarios (seudónimos).
    IDENTIDAD = 2
    # Cómo se organiza la gente: lugares, grupos, permisos, audiencias, solicitudes, moderación.
    ORGANIZACION = 3
    # Las herramientas de trabajo: eventos, proyectos, debates, consultas, documentos…
    FUNCIONAL = 4


class Modo(IntEnum):
    """
    Cuándo se ejecuta quien escucha un eventos_sw (ver docs/diseno.md, apartado 3.7).
    """

    # Dentro de la misma transacción que lo emite: si falla, se deshace todo. Para lo que debe ocurrir sí
    # o sí a la vez (invalidar la caché, copiar una audiencia).
    SINCRONO = 1
    # Después, por un trabajador aparte, a partir de una bandeja de salida. Para lo que puede esperar unos
    # segundos (notificaciones, correos, Telegram).
    ASINCRONO = 2


# Roles que existen siempre (ver docs/diseno.md, apartado 5). Los contratos solo pueden nombrar estos al
# decir qué roles tienen un permiso por defecto; los roles personalizados los crea el superadmin después.
#   - usuario: cualquier miembro de un grupo (y, por herencia, de los grupos que lo contienen).
#   - admin_grupo: admin de un grupo concreto (no se hereda).
#   - admin_org: admin de una organización (en todos sus grupos).
ROLES_DEL_SISTEMA = ("usuario", "admin_grupo", "admin_org")


@dataclass(frozen=True)
class Permiso:
    """
    Algo que se puede o no se puede hacer, declarado por el módulo al que pertenece. El módulo
    «permisos» los reúne para asignarlos a roles y calcular qué puede hacer cada persona.
    """

    # Código único, empezando por la etiqueta del módulo. Ejemplo: «eventos.convocar_reunion».
    codigo: str
    # Explicación en lenguaje llano que se ve en la pantalla de roles y permisos. Conviene que empiece
    # por un verbo: «Convocar una reunión del grupo».
    descripcion: str
    # Roles que lo tienen por defecto, de ROLES_DEL_SISTEMA. Solo se aplica la primera vez que aparece
    # el permiso: después, el superadmin puede ponerlo o quitarlo a cada rol. El superadmin lo tiene
    # siempre, aunque no se diga.
    roles: tuple[str, ...] = ()


@dataclass(frozen=True)
class Cometido:
    """
    Función de una persona en algo concreto (facilitación de un debate, toma de acta de una reunión…).
    No confundir con el rol, que es el nivel fijo de poder (ver docs/diseno.md, apartado 5).
    """

    # Código único, empezando por la etiqueta del módulo. Ejemplo: «debates.facilitacion».
    codigo: str
    # Nombre visible. Ejemplo: «Facilitación».
    nombre: str
    # Qué hace quien lo asume, en lenguaje llano.
    descripcion: str
    # Permisos que da sobre aquello en lo que se tiene (por ejemplo, la facilitación de un debate da
    # «debates.moderar» en ese debate). Deben estar declarados en algún contrato.
    permisos: tuple[str, ...] = ()


@dataclass(frozen=True)
class Ancla:
    """
    Tipo de objeto del que se pueden colgar cosas de otros módulos (un debate que cuelga de una tarea,
    un chat que cuelga de un evento). Se guarda como «tipo + id», sin clave ajena entre módulos.
    """

    # Nombre del tipo que se guarda en ancla_tipo. Ejemplo: «proyectos.tarea».
    tipo: str
    # Modelo de Django al que apunta, como «app.Modelo». Ejemplo: «proyectos.Tarea».
    modelo: str
    # Qué es, en lenguaje llano. Ejemplo: «Una tarea de un proyecto».
    descripcion: str


@dataclass(frozen=True)
class Hueco:
    """
    Sitio dentro de una ficha donde otros módulos pueden mostrar lo que cuelga de ella. Por ejemplo, la
    ficha de un proyecto tiene el hueco «proyectos.ficha_proyecto.lateral», donde aparecen sus debates.
    """

    # Código único, empezando por la etiqueta del módulo.
    codigo: str
    # Dónde está y para qué sirve, en lenguaje llano.
    descripcion: str


@dataclass(frozen=True)
class FuenteDeCalendario:
    """
    Algo con fecha que el módulo aporta al calendario común (eventos, fechas límite de tareas, cierres
    de consultas…). El calendario pide los datos a la función indicada, sin importar el módulo.
    """

    # Código único, empezando por la etiqueta del módulo. Ejemplo: «proyectos.fechas_limite».
    codigo: str
    # Nombre visible en los filtros del calendario.
    nombre: str
    # Ruta de la función que devuelve las fechas, como texto. Ejemplo: «proyectos.calendario.fechas».
    # Recibe (usuario, desde, hasta) y devuelve una lista de FechaDeCalendario: solo lo que esa persona
    # puede ver entre esas dos fechas. Debe hacer siempre las mismas consultas, haya lo que haya.
    funcion: str
    # Color con el que se pinta en el calendario, como color de CSS («#e11d78»). Cada fecha puede
    # traer el suyo (por ejemplo, uno por tipo de evento).
    color: str = "#64748b"
    # Ruta de la función que cambia la fecha de una de sus cosas al arrastrarla en el calendario. Recibe
    # (usuario, id, inicio, fin) y lanza ValidationError si no se puede. Vacío: no se arrastra nada.
    mover: str = ""


@dataclass(frozen=True)
class FechaDeCalendario:
    """
    Una cosa con fecha que una fuente del calendario entrega para pintarla (un evento, un recordatorio…).
    """

    # Identificador dentro de su fuente (el número de la fila). Sirve para moverla al arrastrar.
    id: int
    # Título que se ve en el calendario.
    titulo: str
    # Cuándo empieza (fecha y hora, con su zona horaria).
    inicio: object
    # Cuándo termina. None: no tiene fin (se pinta como un punto en el tiempo, o un solo día). En las de
    # día entero, el último día que ocupa (a las 00:00).
    fin: object = None
    # Si ocupa días enteros (sin hora). Entonces «inicio» es el primer día a las 00:00.
    todo_el_dia: bool = False
    # Dirección de su ficha, para abrirla al pulsarla. Vacío: no se abre nada.
    enlace: str = ""
    # Nombre con el que se filtra («Reunión», «Acción», «Recordatorio»). Vacío: el nombre de la fuente.
    categoria: str = ""
    # Color de CSS con el que se pinta. Vacío: el de la fuente.
    color: str = ""
    # Dónde es, en texto (para la suscripción .ics). Opcional.
    lugar: str = ""
    # Si esta persona puede arrastrarla para cambiarle la fecha (la fuente necesita «mover»).
    se_puede_mover: bool = False


@dataclass(frozen=True)
class TarjetaDeInicio:
    """
    Un recuadro que el módulo aporta a la portada, «Inicio» (el panel o «Mis datos»): un resumen de lo
    suyo, con un botón que lleva a su sección. Inicio no importa el módulo: pide el resumen a la función
    indicada. Dónde sale cada tarjeta (en qué pantalla, en qué fila y en qué orden) lo decide un solo
    fichero, config/inicio.py.
    """

    # Código único, empezando por la etiqueta del módulo. Ejemplo: «solicitudes.pendientes».
    codigo: str
    # Título del recuadro: «Solicitudes».
    titulo: str
    # Ruta de la función que hace el resumen, como texto. Recibe el usuario y devuelve un
    # ResumenDeTarjeta, o None si a esa persona no le toca ver la tarjeta. Debe hacer siempre las mismas
    # consultas, haya lo que haya.
    funcion: str
    # Icono y color del título, como en el menú (un símbolo de texto y un color de CSS).
    icono: str = ""
    color: str = "#64748b"


@dataclass(frozen=True)
class FilaDeResumen:
    """
    Una línea de una tarjeta de Inicio: una solicitud, una notificación, un proyecto, un dato…
    """

    # Lo principal, en pocas palabras: «Entrar en GRU Henares», «Huerto del barrio».
    texto: str
    # Dirección (ya resuelta) a la que lleva al pulsarla. Vacía: no se pulsa.
    enlace: str = ""
    # Una aclaración más pequeña, a la derecha o debajo: «1 de 2 apoyos», «Empezado».
    detalle: str = ""
    # Fecha u hora de la que se habla, si la hay (se pinta como «hace 2 días»).
    fecha: object = None
    # Si pide atención (algo sin ver, o que espera respuesta de quien mira): sale resaltada.
    destacada: bool = False


@dataclass(frozen=True)
class ApartadoDeTarjeta:
    """
    Una parte de una tarjeta de Inicio, con su título pequeño: por ejemplo, «Recibidas» y «Enviadas»
    dentro de «Solicitudes». Una tarjeta sencilla tiene uno solo, sin título.
    """

    # Título pequeño del apartado: «Recibidas». Vacío: sin título.
    titulo: str = ""
    # Las líneas que se enseñan (lo normal: las 5 más recientes).
    filas: tuple[FilaDeResumen, ...] = ()
    # Cuántas hay en total; si son más que las filas, sale «Ver todas (N)».
    total: int = 0
    # Dirección (ya resuelta) de la lista completa, para «Ver todas».
    enlace: str = ""
    # Lo que se dice si no hay nada: «Nada pendiente.».
    vacio: str = "Nada por aquí."


@dataclass(frozen=True)
class ResumenDeTarjeta:
    """
    Lo que devuelve la función de una TarjetaDeInicio: sus apartados y adónde lleva su botón. Si la tarjeta
    necesita un dibujo propio (por ejemplo, el árbol de grupos), da una plantilla y su contexto en lugar
    de (o además de) los apartados.
    """

    # Las partes de la tarjeta.
    apartados: tuple[ApartadoDeTarjeta, ...] = ()
    # Dirección (ya resuelta) del botón del título: la sección donde se ve todo o donde se cambia.
    enlace: str = ""
    # Texto de ese botón: «Ir», «Editar»…
    boton: str = "Ir"
    # Plantilla propia que se pinta debajo de los apartados, con su contexto. Vacía: ninguna.
    plantilla: str = ""
    contexto: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Colgante:
    """
    Algo de este módulo que puede colgar de un elemento de otro (sus debates, sus actas, sus consultas…) y
    que sale en la ficha de ese elemento, en su recuadro «Cuelga de aquí», con un enlace para crear uno
    nuevo. La ficha no importa el módulo: lo pinta la etiqueta {% colgantes %} de base (ver
    base/templatetags/colgantes.py), que pide las filas a la función indicada.
    """

    # Código único, empezando por la etiqueta del módulo. Ejemplo: «debates.debates».
    codigo: str
    # Nombre visible del grupo de cosas: «Debates».
    nombre: str
    # Tipos de ancla de los que puede colgar: («eventos.evento», «proyectos.proyecto»).
    anclas: tuple[str, ...]
    # Ruta de la función que devuelve lo que cuelga y ve una persona: recibe (usuario, ancla_tipo,
    # ancla_id) y devuelve una lista de FilaDeResumen. Debe hacer siempre las mismas consultas.
    funcion: str
    # Nombre de la dirección para crear uno nuevo; se le añade «?ancla=<tipo>:<id>». Vacío: sin enlace.
    crear: str = ""
    # Texto de ese enlace: «+ Debate».
    texto_crear: str = ""


@dataclass(frozen=True)
class Emision:
    """
    Un eventos_sw que el módulo emite: un aviso de que algo ha pasado («consultas.cerrada»). Los demás
    módulos lo escuchan por su nombre, sin importar el módulo que lo emite.
    """

    # Nombre único, empezando por la etiqueta del módulo. Ejemplo: «consultas.cerrada».
    nombre: str
    # Qué ha pasado cuando se emite, en lenguaje llano.
    descripcion: str


@dataclass(frozen=True)
class Escucha:
    """
    Un eventos_sw que el módulo escucha, con la función que se ejecuta cuando ocurre.
    """

    # Nombre del eventos_sw escuchado. Ejemplo: «consultas.cerrada».
    evento: str
    # Ruta de la función que se ejecuta, como texto. Ejemplo: «decisiones.receptores.copiar_resultado».
    receptor: str
    # Si se ejecuta en la misma transacción (SINCRONO) o después, desde la bandeja (ASINCRONO).
    modo: Modo = Modo.ASINCRONO
    # Datos fijos que se añaden a los del eventos_sw al llamar al receptor, como pares (nombre, valor).
    # Los usa el registro para decir al repartidor de avisos qué tipo de aviso toca (ver TipoDeAviso).
    extra: tuple = ()


# Orígenes de las notificaciones: las bandejas de «Comunicaciones» (ver docs/diseno.md, apartado 17).
# Pares (código, nombre visible).
ORIGENES_DE_AVISO = (
    ("grupos", "Organización y grupos"),
    ("superadmin", "Superadmin"),
    ("admins", "Admins"),
    ("proyectos", "Proyectos"),
    ("eventos", "Eventos"),
    ("debates", "Debates"),
    ("solicitudes", "Solicitudes"),
    ("sistema", "Sistema"),
)


@dataclass(frozen=True)
class TipoDeAviso:
    """
    Un tipo de notificación que el módulo manda a las personas cuando pasa algo («Han invitado a tu
    grupo»). Cada persona puede desactivar cada tipo en «Comunicaciones → Preferencias». El módulo dice
    cuándo (el eventos_sw) y a quién y qué (la función «preparar»); el módulo «comunicaciones» lo reparte
    sin saber nada del módulo que lo declara.
    """

    # Código único, empezando por la etiqueta del módulo. Ejemplo: «grupos.invitacion_recibida».
    codigo: str
    # Nombre visible en las preferencias. Ejemplo: «Han invitado a uno de tus grupos».
    nombre: str
    # Bandeja en la que aparece: uno de los códigos de ORIGENES_DE_AVISO.
    origen: str
    # Nombre del eventos_sw que lo dispara (declarado en el «emite» de algún módulo).
    evento: str
    # Ruta de la función que recibe los datos del eventos_sw y devuelve una lista de AvisoPreparado.
    # Ejemplo: «grupos.avisos.invitacion_recibida».
    preparar: str


@dataclass(frozen=True)
class TipoDeSolicitud:
    """
    Algo que se pide a un grupo y que necesita apoyos para hacerse (entrar en el grupo, abrir un debate,
    convocar una reunión…). El módulo «solicitudes» gestiona los apoyos, el plazo y el estado; cuando se
    alcanzan, llama a la función «resolver» del módulo que lo declara, que crea lo pedido. Ver
    docs/diseno.md, apartado 6.
    """

    # Código único, empezando por la etiqueta del módulo. Ejemplo: «grupos.entrar».
    codigo: str
    # Nombre visible. Ejemplo: «Entrar en un grupo».
    nombre: str
    # Ruta de la función que crea lo pedido al aceptarse: recibe la solicitud y devuelve el ancla (tipo,
    # id) de lo creado, o None. Ejemplo: «grupos.solicitudes.entrar».
    resolver: str
    # Apoyos de miembros del grupo que hacen falta, si nadie lo ha ajustado (en «Administrar → Mi
    # organización → Apoyos y plazos»). Quien solicita no cuenta.
    apoyos: int = 2
    # Días que tiene para conseguirlos antes de caducar, si nadie lo ha ajustado.
    dias: int = 15
    # Permiso que hace falta en el grupo para dar el sí de la administración; vacío si no hace falta.
    # Ejemplo: «grupos.admitir» (el admin del grupo o el de la organización).
    aprobacion: str = ""
    # Si el sí del superadmin basta por sí solo, sin apoyos (para los primeros usuarios).
    basta_el_superadmin: bool = False
    # Si quien solicita debe ser miembro del grupo (False para «entrar en un grupo»).
    solo_miembros: bool = True
    # Ruta de una función que comprueba, al pedirla, que se puede pedir (recibe usuario y grupo y lanza
    # ValidationError si no). Vacía: no hay más comprobaciones.
    comprobar: str = ""
    # Apoyos según la altura a la que se pide (0: el propio grupo, 1: el padre, 2 o más: el abuelo…), por
    # ejemplo (2, 5, 10) para las reuniones. Si se indica, manda sobre «apoyos» y sobre los ajustes.
    apoyos_por_altura: tuple = ()
    # Si se pide desde «Comunicaciones → Solicitudes → Enviadas → Pedir algo», solo con descripción y
    # justificación. Los tipos que necesitan su propio formulario (un debate, una reunión) se piden desde su
    # módulo.
    generica: bool = False


@dataclass(frozen=True)
class AvisoPreparado:
    """
    Lo que devuelve la función «preparar» de un TipoDeAviso: a quién se avisa y qué se le dice. Cuidado:
    el texto no debe contar nada que esas personas no puedan ver.
    """

    # Ids de los usuarios a los que se avisa.
    usuarios: tuple
    # Texto de la notificación, en una o dos frases.
    texto: str
    # Dirección a la que lleva al pulsarla (vacía si no lleva a ningún sitio).
    enlace: str = ""


@dataclass(frozen=True)
class TareaDiaria:
    """
    Algo que un módulo necesita hacer una vez al día sin que nadie lo pida (caducar solicitudes vencidas,
    crear las siguientes veces de las series de eventos…). El trabajador (la orden procesar_bandeja) las
    ejecuta todas la primera vez que da una vuelta cada día (ver base/tareas.py).
    """

    # Código único, empezando por la etiqueta del módulo. Ejemplo: «eventos.generar_series».
    codigo: str
    # Qué hace, en lenguaje llano.
    descripcion: str
    # Ruta de la función, sin parámetros. Lo que devuelva (por ejemplo, cuántas cosas ha hecho) se apunta.
    funcion: str


@dataclass(frozen=True)
class GrupoDeEtiquetas:
    """
    Conjunto de etiquetas propio de un módulo (por ejemplo, las de los debates), dentro de la base única
    de etiquetas.
    """

    # Código único, empezando por la etiqueta del módulo. Ejemplo: «debates.temas».
    codigo: str
    # Nombre visible.
    nombre: str
    # Para qué sirven estas etiquetas, en lenguaje llano.
    descripcion: str


@dataclass(frozen=True)
class Limpiable:
    """
    Tipo de elemento que el módulo «limpieza» puede archivar y borrar pasado un plazo (ver
    docs/diseno.md, apartado 14.3).
    """

    # Código único, empezando por la etiqueta del módulo. Ejemplo: «proyectos.tarea».
    codigo: str
    # Modelo de Django, como «app.Modelo». Si se archiva, debe tener los campos «titulo», «audiencia»
    # (quién lo ve; a esas personas se les avisa) y «archivado» (fecha y hora, vacía hasta que se archiva;
    # la rellena «limpieza» y el módulo saca de sus listas lo que la tiene).
    modelo: str
    # Nombre visible en la configuración de la limpieza.
    nombre: str
    # Si se archiva: ruta de la función que recibe un momento y devuelve la consulta (QuerySet del
    # modelo) de lo que está sin archivar y terminó antes de ese momento. Lo que va dentro de un proyecto
    # no entra: sigue al proyecto. Ejemplo: «proyectos.limpieza.proyectos».
    terminados: str = ""
    # Si se archiva: nombre de la dirección web de su ficha, que recibe el id. Ejemplo: «proyectos:proyecto».
    ficha: str = ""
    # Si se borra sin archivar antes (sin avisos ni «Conservar», como las notificaciones): ruta de la
    # función que recibe un momento, borra lo que terminó antes y devuelve cuántos ha borrado.
    borrar: str = ""
    # Días de partida tras terminar hasta archivarlo (el superadmin los cambia en «Plataforma →
    # Limpieza»). No se usa si se borra sin archivar.
    archivar_a: int = 30
    # Días de partida tras archivarlo hasta borrarlo (o, si se borra sin archivar, tras terminar).
    borrar_a: int = 365


@dataclass(frozen=True)
class DatosDeEjemplo:
    """
    Funciones que crean y borran los datos de ejemplo del módulo, para probar y medir las pantallas.
    Lo usa el módulo «ejemplos».

    El borrado quita también lo que se haya creado al probar dentro de las organizaciones de ejemplo o a
    nombre de las personas de ejemplo (grupos.ejemplos.organizaciones_de_ejemplo y
    usuarios.ejemplos.usuarios_de_ejemplo): si no, protegería lo de los módulos de abajo y no se podría
    borrar. Por eso un módulo que no crea ejemplos pero guarda contenido (eventos, calendario) declara
    solo el borrado.
    """

    # Ruta de la función que crea los datos de ejemplo. Ejemplo: «proyectos.ejemplos.crear». Vacía: el
    # módulo no crea ejemplos, solo borra (ver arriba).
    crear: str
    # Ruta de la función que los borra, dejando la base como estaba.
    borrar: str


@dataclass(frozen=True)
class Vista:
    """
    Una vista de una sección, que se muestra en el menú superior (por ejemplo, en «Eventos»: lista,
    calendario, mapa).
    """

    # Nombre visible en el menú superior.
    nombre: str
    # Nombre de la dirección web en Django (el «name» de la ruta). Ejemplo: «eventos:lista».
    url: str


@dataclass(frozen=True)
class EntradaDeMenu:
    """
    Una sección o subsección del menú izquierdo, con las vistas que salen arriba cuando se elige.

    El módulo dice qué entradas aporta (y puede anidarlas en «subsecciones»), pero dónde va cada una
    (en qué orden y dentro de qué sección) lo decide un solo fichero, config/menu.py: así reordenar o
    agrupar el menú es mover una línea (ver docs/diseno.md, apartado 4, «Disposición del menú»).
    """

    # Código único, empezando por la etiqueta del módulo. También identifica su texto de ayuda «?».
    codigo: str
    # Nombre visible en el menú.
    nombre: str
    # Nombre de la dirección web a la que lleva al pulsarla.
    url: str
    # Icono que se dibuja a su lado: un símbolo de texto de un solo color («⇄», «✉»), para que tome el
    # color de abajo (los emoji de colores no lo toman). No puede repetirse en todo el menú.
    icono: str = ""
    # Color del icono, como color de CSS («#16a34a»). El icono se pinta con este color sobre un fondo del
    # mismo color, muy claro. Tampoco puede repetirse (13 de noviembre de 2026, a petición de la persona
    # usuaria: cada entrada se reconoce de un vistazo).
    color: str = "#64748b"
    # Permiso que hace falta para verla. Vacío: la ve cualquier persona que haya iniciado sesión.
    permiso: str = ""
    # Ruta de una función que recibe el usuario y dice si puede verla aunque no tenga el permiso (por
    # ejemplo, las guías de desarrollo, abiertas a todo el mundo solo en desarrollo). Vacío: solo el permiso.
    tambien_si: str = ""
    # Vistas de la sección, para el menú superior.
    vistas: tuple[Vista, ...] = ()
    # Subsecciones que cuelgan de ella en el menú izquierdo. Las que declara el módulo solo sirven para
    # agrupar su contrato: el registro las vuelve a colgar donde diga config/menu.py.
    subsecciones: tuple["EntradaDeMenu", ...] = ()
    # Otras direcciones que pertenecen a esta entrada sin salir en el menú superior (por ejemplo, la
    # ficha de un grupo). Al visitarlas, el menú marca esta entrada y la cabecera muestra su nombre.
    otras_rutas: tuple[str, ...] = ()
    # Ruta de una función que recibe el usuario y devuelve un número que se muestra entre paréntesis tras
    # el nombre («Invitaciones (2)»), también cuando es 0. Vacío: sin número. Debe ser barata (se llama
    # en cada página): lo normal es que guarde el resultado en la caché. Ejemplo:
    # «grupos.contadores.invitaciones_pendientes».
    contador: str = ""
    # Si sus subsecciones salen como pestañas arriba en lugar de en el menú de la izquierda. No lo pone el
    # módulo: lo decide la disposición del menú (config/menu.py, con Pestanas).
    en_pestanas: bool = False
    # Si es la entrada de la ayuda: sus subsecciones salen también en el botón «?» rojo de la cabecera,
    # que las abre en el panel de ayuda de la derecha (ver base/templates/base/pagina.html). Solo puede
    # haber una. La declara el módulo «ayuda».
    panel_de_ayuda: bool = False


@dataclass(frozen=True)
class Ayuda:
    """
    Texto de la miniayuda «?» de una sección: la ventana emergente que sale al pulsar el «?» gris junto
    a su título. Explica qué es la sección y para qué se usa, y puede traer un ejemplo. (La ayuda larga,
    paso a paso, está en la sección «Ayuda» y en el panel del «?» rojo.)
    """

    # Código de la sección del menú a la que acompaña.
    seccion: str
    # Título de la ventana de ayuda.
    titulo: str
    # Explicación en lenguaje llano.
    texto: str
    # Un ejemplo de uso, opcional («Lince convoca la asamblea de los jueves…»). Sale aparte, debajo del
    # texto. Vacío: sin ejemplo.
    ejemplo: str = ""


class ModuloConfig(AppConfig):
    """
    Clase común de la que hereda la configuración (apps.py) de cada módulo del proyecto. Además de lo que
    ya pide Django (name, verbose_name), cada módulo rellena aquí los apartados de su contrato.

    Todos los apartados empiezan vacíos: el módulo solo rellena los que usa. Se declaran como tuplas
    (listas que no se pueden modificar), pero el registro también acepta listas normales.
    """

    # Capa a la que pertenece el módulo. Es obligatoria: el registro avisa si falta.
    capa: Capa | None = None
    # Qué hace el módulo, en lenguaje llano. Se ve en «Ayuda y referencias».
    descripcion: str = ""
    # Permisos que el módulo define.
    permisos: tuple[Permiso, ...] = ()
    # Cometidos que se pueden asumir en las cosas de este módulo.
    cometidos: tuple[Cometido, ...] = ()
    # Tipos de objeto de este módulo de los que pueden colgar cosas de otros módulos.
    anclas: tuple[Ancla, ...] = ()
    # Sitios de sus fichas donde otros módulos pueden mostrar lo que cuelga de ellas.
    huecos: tuple[Hueco, ...] = ()
    # Lo que aporta al calendario común.
    fuentes_de_calendario: tuple[FuenteDeCalendario, ...] = ()
    # Sus recuadros de la portada («Inicio → Panel» y «Mis datos»).
    tarjetas_de_inicio: tuple[TarjetaDeInicio, ...] = ()
    # Lo suyo que puede colgar de elementos de otros módulos (sale en sus fichas, «Cuelga de aquí»).
    colgantes: tuple[Colgante, ...] = ()
    # Los eventos_sw que emite.
    emite: tuple[Emision, ...] = ()
    # Los eventos_sw que escucha, con su función.
    escucha: tuple[Escucha, ...] = ()
    # Sus grupos de etiquetas.
    grupos_de_etiquetas: tuple[GrupoDeEtiquetas, ...] = ()
    # Los tipos de elemento que se pueden archivar y borrar.
    limpiables: tuple[Limpiable, ...] = ()
    # Los tipos de notificación que manda a las personas.
    avisos: tuple[TipoDeAviso, ...] = ()
    # Lo que se puede pedir con apoyos a un grupo.
    solicitudes: tuple[TipoDeSolicitud, ...] = ()
    # Lo que hace una vez al día (el trabajador lo ejecuta solo).
    tareas_diarias: tuple[TareaDiaria, ...] = ()
    # Solo el módulo que reparte las notificaciones («comunicaciones»): ruta de la función que recibe
    # cada aviso. El registro le añade una escucha asíncrona por cada TipoDeAviso de cualquier módulo.
    reparte_avisos: str = ""
    # Cómo crear y borrar sus datos de ejemplo. Vacío si no tiene.
    datos_de_ejemplo: DatosDeEjemplo | None = None
    # Sus secciones del menú izquierdo.
    menu: tuple[EntradaDeMenu, ...] = ()
    # Sus textos de ayuda «?».
    ayuda: tuple[Ayuda, ...] = ()
