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

from dataclasses import dataclass
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
    funcion: str
    # Color con el que se pinta en el calendario (nombre de color de Tailwind). Ejemplo: «amber».
    color: str = "slate"


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
    # Modelo de Django, como «app.Modelo».
    modelo: str
    # Nombre visible en la configuración de la limpieza.
    nombre: str


@dataclass(frozen=True)
class DatosDeEjemplo:
    """
    Funciones que crean y borran los datos de ejemplo del módulo, para probar y medir las pantallas.
    Lo usa el módulo «ejemplos».
    """

    # Ruta de la función que crea los datos de ejemplo. Ejemplo: «eventos.ejemplos.crear».
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
    # Posición en el menú: los números más bajos salen antes.
    orden: int = 100
    # Permiso que hace falta para verla. Vacío: la ve cualquier persona que haya iniciado sesión.
    permiso: str = ""
    # Vistas de la sección, para el menú superior.
    vistas: tuple[Vista, ...] = ()
    # Subsecciones que cuelgan de ella en el menú izquierdo.
    subsecciones: tuple["EntradaDeMenu", ...] = ()
    # Otras direcciones que pertenecen a esta entrada sin salir en el menú superior (por ejemplo, la
    # ficha de un grupo). Al visitarlas, el menú marca esta entrada y la cabecera muestra su nombre.
    otras_rutas: tuple[str, ...] = ()
    # Ruta de una función que recibe el usuario y devuelve un número que se muestra entre paréntesis tras
    # el nombre («Invitaciones (2)»), también cuando es 0. Vacío: sin número. Debe ser barata (se llama
    # en cada página): lo normal es que guarde el resultado en la caché. Ejemplo:
    # «grupos.contadores.invitaciones_pendientes».
    contador: str = ""
    # Código de la entrada de otro módulo dentro de la cual se cuelga esta como subsección (por ejemplo,
    # «tipologias.configuracion» para poner «Etiquetas» dentro de «Configuración»). Vacío: es una
    # sección principal (o ya va en las subsecciones de su madre, si es del mismo módulo). Las
    # subsecciones se ordenan por «orden».
    dentro_de: str = ""


@dataclass(frozen=True)
class Ayuda:
    """
    Texto de la ayuda «?» de una sección: explica para qué sirve y qué significa cada dato.
    """

    # Código de la sección del menú a la que acompaña.
    seccion: str
    # Título de la ventana de ayuda.
    titulo: str
    # Explicación en lenguaje llano.
    texto: str


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
    # Los eventos_sw que emite.
    emite: tuple[Emision, ...] = ()
    # Los eventos_sw que escucha, con su función.
    escucha: tuple[Escucha, ...] = ()
    # Sus grupos de etiquetas.
    grupos_de_etiquetas: tuple[GrupoDeEtiquetas, ...] = ()
    # Los tipos de elemento que se pueden archivar y borrar.
    limpiables: tuple[Limpiable, ...] = ()
    # Cómo crear y borrar sus datos de ejemplo. Vacío si no tiene.
    datos_de_ejemplo: DatosDeEjemplo | None = None
    # Sus secciones del menú izquierdo.
    menu: tuple[EntradaDeMenu, ...] = ()
    # Sus textos de ayuda «?».
    ayuda: tuple[Ayuda, ...] = ()
