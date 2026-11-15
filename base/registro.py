"""
Registro de módulos: reúne en un solo sitio lo que declara el contrato de cada módulo.

Se carga una sola vez al arrancar Django (desde BaseConfig.ready, en base/apps.py). A partir de ahí,
cualquier parte de la aplicación pregunta aquí en lugar de recorrer los módulos: el menú lee
«registro.menu», eventos_sw lee «registro.escuchas», la pantalla de permisos lee «registro.permisos»…

Mientras carga, el registro apunta los errores de declaración que encuentra (códigos repetidos, un
módulo que escucha un eventos_sw que nadie emite…). No los lanza: las comprobaciones de Django
(base/comprobaciones.py) los muestran todos juntos al arrancar o al ejecutar «manage.py check».
"""

from dataclasses import replace
from pathlib import Path

from django.utils.module_loading import import_string

from .contrato import ORIGENES_DE_AVISO, ROLES_DEL_SISTEMA, Capa, Escucha, Modo, ModuloConfig
from .disposicion import Bloque, Pestanas

# Apartados del contrato que son listas de fichas con un código único, y el nombre del campo que hace de
# código en cada una. El registro los recorre todos igual: comprueba el prefijo y que no se repitan.
APARTADOS_CON_CODIGO = {
    "permisos": "codigo",
    "cometidos": "codigo",
    "anclas": "tipo",
    "huecos": "codigo",
    "fuentes_de_calendario": "codigo",
    "tarjetas_de_inicio": "codigo",
    "colgantes": "codigo",
    "emite": "nombre",
    "grupos_de_etiquetas": "codigo",
    "limpiables": "codigo",
    "avisos": "codigo",
    "solicitudes": "codigo",
    "tareas_diarias": "codigo",
}


class RegistroDeModulos:
    """
    Lo que han declarado todos los módulos, ya ordenado y listo para consultar.
    """

    # Crea un registro vacío. Se rellena después con cargar().
    def __init__(self):
        self._vaciar()

    # Deja el registro sin datos. Se usa al crearlo y al principio de cada carga, para que cargar dos
    # veces (por ejemplo, en las pruebas) no mezcle datos.
    def _vaciar(self):
        # Módulos del proyecto, por su etiqueta (la «label» de Django, p. ej. «eventos»).
        self.modulos = {}
        # Un diccionario por cada apartado con código, de código a ficha. Ejemplo:
        # self.permisos["eventos.convocar_reunion"] → Permiso(...)
        for apartado in APARTADOS_CON_CODIGO:
            setattr(self, apartado, {})
        # Quién escucha cada eventos_sw: de nombre del evento a la lista de escuchas.
        self.escuchas = {}
        # Ruta de la función que reparte las notificaciones (la declara «comunicaciones»), o vacío.
        self.repartidor_de_avisos = ""
        # Datos de ejemplo de cada módulo, por su etiqueta.
        self.datos_de_ejemplo = {}
        # Secciones del menú izquierdo, ya colocadas (con sus subsecciones dentro) según la disposición.
        self.menu = []
        # Todas las entradas del menú tal como las declaran los módulos (secciones y subsecciones, a
        # cualquier profundidad), por su código. Sirve para colocarlas y para preguntar por una concreta.
        self.entradas = {}
        # Los bloques del menú, en orden: pares (Bloque, lista de sus secciones principales ya colocadas). Sin
        # disposición, un solo bloque sin título con todo el menú.
        self.bloques = []
        # La entrada de la ayuda (la que lleva panel_de_ayuda), ya colocada con sus subsecciones, o None.
        # La usa el botón «?» rojo de la cabecera (base/contexto.py).
        self.entrada_de_ayuda = None
        # Textos de ayuda, por código de sección.
        self.ayuda = {}
        # Camino del menú de cada dirección web: del nombre de la ruta («base:inicio») a la tupla de
        # entradas desde la sección principal hasta la subsección a la que pertenece. Sirve para marcar
        # en el menú dónde se está, sin que cada vista tenga que decirlo.
        self.rutas = {}
        # Errores de declaración encontrados durante la carga, como textos.
        self.errores = []
        # Si ya se ha cargado al menos una vez.
        self.cargado = False

    # Lee las configuraciones de los módulos y rellena el registro.
    #   - configuraciones: las AppConfig de Django (todas, también las de Django y de librerías).
    #   - raiz: carpeta del proyecto. Una app de esa carpeta que no use ModuloConfig es un error,
    #     porque todo módulo del proyecto debe declarar su contrato. Si no se indica, no se comprueba.
    #   - disposicion: dónde va cada entrada del menú (la DISPOSICION de config/menu.py). Si no se
    #     indica (las pruebas con módulos de mentira), el menú sale como lo declaran los módulos, en el
    #     orden en que se cargan.
    def cargar(self, configuraciones, raiz=None, disposicion=None):
        self._vaciar()
        for config in configuraciones:
            if isinstance(config, ModuloConfig):
                self._cargar_modulo(config)
            elif raiz is not None and _esta_dentro(config.path, raiz):
                self.errores.append(
                    f"El módulo «{config.label}» es del proyecto pero su apps.py no hereda de "
                    "ModuloConfig, así que no declara su contrato."
                )
        if disposicion is not None:
            self.menu = self._disponer(disposicion)
        else:
            self.bloques = [(Bloque("", "", ()), self.menu)]
        self._buscar_la_entrada_de_ayuda()
        self._conectar_avisos()
        self._comprobar_escuchas()
        self._comprobar_ayuda()
        self._comprobar_permisos()
        for entrada in self.menu:
            self._apuntar_rutas(entrada, ())
        self.cargado = True

    # Añade al registro todo lo que declara un módulo.
    def _cargar_modulo(self, config):
        etiqueta = config.label
        self.modulos[etiqueta] = config
        if not isinstance(config.capa, Capa):
            self.errores.append(
                f"El módulo «{etiqueta}» no dice a qué capa pertenece (atributo «capa» con un valor de Capa)."
            )
        # Apartados con código: comprueba el prefijo y que el código no esté ya usado.
        for apartado, campo in APARTADOS_CON_CODIGO.items():
            destino = getattr(self, apartado)
            for ficha in getattr(config, apartado):
                codigo = getattr(ficha, campo)
                self._comprobar_prefijo(etiqueta, apartado, codigo)
                if codigo in destino:
                    self.errores.append(f"«{codigo}» está declarado dos veces en «{apartado}».")
                destino[codigo] = ficha
        # Escuchas: se agrupan por el nombre del eventos_sw. Pueden ser de eventos de otros módulos, así
        # que no se comprueba el prefijo.
        for escucha in config.escucha:
            self.escuchas.setdefault(escucha.evento, []).append(escucha)
        if config.reparte_avisos:
            if self.repartidor_de_avisos:
                self.errores.append(f"Dos módulos dicen repartir los avisos: «{etiqueta}» y otro.")
            self.repartidor_de_avisos = config.reparte_avisos
        if config.datos_de_ejemplo is not None:
            self.datos_de_ejemplo[etiqueta] = config.datos_de_ejemplo
        # Menú: se comprueba el prefijo de cada entrada y de sus subsecciones, y se apuntan todas por su
        # código (para colocarlas después según la disposición).
        for entrada in config.menu:
            for declarada in _entradas_y_subsecciones(entrada):
                self._comprobar_prefijo(etiqueta, "menu", declarada.codigo)
                if declarada.codigo in self.entradas:
                    self.errores.append(f"«{declarada.codigo}» está declarado dos veces en «menu».")
                self.entradas[declarada.codigo] = declarada
            self.menu.append(entrada)
        # Ayuda: un texto por sección.
        for ayuda in config.ayuda:
            if ayuda.seccion in self.ayuda:
                self.errores.append(f"La sección «{ayuda.seccion}» tiene dos textos de ayuda.")
            self.ayuda[ayuda.seccion] = ayuda

    # Comprueba cada tipo de aviso (origen conocido y eventos_sw que alguien emite) y, si hay un módulo que
    # reparte los avisos, le añade una escucha asíncrona por cada uno, con el código del aviso como dato
    # fijo («aviso»). Así el módulo que declara el aviso no tiene que saber quién lo reparte.
    def _conectar_avisos(self):
        origenes = {codigo for codigo, _nombre in ORIGENES_DE_AVISO}
        for aviso in self.avisos.values():
            if aviso.origen not in origenes:
                self.errores.append(f"El aviso «{aviso.codigo}» tiene un origen desconocido: «{aviso.origen}».")
            if aviso.evento not in self.emite:
                self.errores.append(f"El aviso «{aviso.codigo}» se dispara con «{aviso.evento}», que ningún módulo emite.")
            if self.repartidor_de_avisos:
                escucha = Escucha(aviso.evento, self.repartidor_de_avisos, Modo.ASINCRONO, extra=(("aviso", aviso.codigo),))
                self.escuchas.setdefault(aviso.evento, []).append(escucha)

    # Coloca las entradas del menú según la disposición (config/menu.py) y devuelve las secciones
    # principales, cada una con sus subsecciones dentro. Las subsecciones que declaraba cada módulo se
    # descartan: manda la disposición. Una entrada declarada que la disposición no nombra es un error (se
    # pone al final del menú, sin subsecciones, para que no desaparezca sin más).
    #   - disposicion: tupla de elementos; cada uno es un código («usuarios.cuenta») o un par (código,
    #     tupla de elementos) para una entrada con subsecciones.
    #   La disposición puede ir partida en Bloques (con título); si no, es un solo bloque sin título. Las
    #   secciones de cada bloque quedan en self.bloques.
    def _disponer(self, disposicion):
        colocadas = set()
        if disposicion and all(isinstance(elemento, Bloque) for elemento in disposicion):
            bloques = list(disposicion)
        else:
            if any(isinstance(elemento, Bloque) for elemento in disposicion):
                self.errores.append("La disposición del menú mezcla bloques con entradas sueltas: o todo va en bloques, o nada.")
            bloques = [Bloque("", "", tuple(elemento for elemento in disposicion if not isinstance(elemento, Bloque)))]
        self.bloques = [(bloque, self._colocar(bloque.elementos, colocadas)) for bloque in bloques]
        for codigo, entrada in self.entradas.items():
            if codigo not in colocadas:
                self.errores.append(f"La entrada del menú «{codigo}» no está colocada en la disposición del menú (config/menu.py).")
                self.bloques[-1][1].append(replace(entrada, subsecciones=()))
        return [entrada for _bloque, entradas in self.bloques for entrada in entradas]

    # Convierte un nivel de la disposición en una lista de entradas, con sus subsecciones ya colocadas
    # (se llama a sí misma para cada nivel de más abajo). La usa _disponer.
    #   - elementos: los elementos de este nivel (ver _disponer). Uno con Pestanas lleva sus subsecciones
    #     como pestañas arriba (en_pestanas).
    #   - colocadas: conjunto de códigos ya colocados, que se va rellenando (para avisar de repetidos).
    def _colocar(self, elementos, colocadas):
        entradas = []
        for elemento in elementos:
            en_pestanas = isinstance(elemento, Pestanas)
            if isinstance(elemento, str):
                codigo, hijos = elemento, ()
            elif en_pestanas:
                codigo, hijos = elemento.codigo, tuple(elemento.hijas)
            elif isinstance(elemento, tuple) and len(elemento) == 2 and isinstance(elemento[1], tuple):
                codigo, hijos = elemento
            else:
                self.errores.append(f"En la disposición del menú, «{elemento}» está mal escrito: va un código o un par (código, (subsecciones…)).")
                continue
            entrada = self.entradas.get(codigo)
            if entrada is None:
                self.errores.append(f"La disposición del menú nombra «{codigo}», pero ningún módulo declara esa entrada.")
                continue
            if codigo in colocadas:
                self.errores.append(f"«{codigo}» está dos veces en la disposición del menú.")
                continue
            colocadas.add(codigo)
            entradas.append(replace(entrada, subsecciones=tuple(self._colocar(hijos, colocadas)), en_pestanas=en_pestanas))
        return entradas

    # Busca, ya colocado el menú, la entrada de la ayuda (la que lleva panel_de_ayuda) y la guarda en
    # self.entrada_de_ayuda. Si hay más de una, es un error.
    def _buscar_la_entrada_de_ayuda(self):
        de_ayuda = [entrada for seccion in self.menu for entrada in _entradas_y_subsecciones(seccion) if entrada.panel_de_ayuda]
        if len(de_ayuda) > 1:
            self.errores.append(f"Hay varias entradas del menú con panel_de_ayuda: {', '.join(entrada.codigo for entrada in de_ayuda)}. Solo puede haber una.")
        self.entrada_de_ayuda = de_ayuda[0] if de_ayuda else None

    # Apunta un error si un código no empieza por la etiqueta del módulo que lo declara. Así se sabe
    # siempre de qué módulo es cada cosa y dos módulos no pueden chocar.
    def _comprobar_prefijo(self, etiqueta, apartado, codigo):
        if not codigo.startswith(f"{etiqueta}."):
            self.errores.append(
                f"En «{apartado}» del módulo «{etiqueta}», «{codigo}» debe empezar por «{etiqueta}.»."
            )

    # Apunta en self.rutas la dirección de una entrada de menú y las de sus vistas, y sigue con sus
    # subsecciones. Una subsección puede repetir la dirección de la sección de la que cuelga (gana la
    # subsección, que es más concreta); dos entradas que no cuelgan una de otra, no.
    #   - entrada: la entrada de menú.
    #   - antecesores: las entradas de las que cuelga, desde la sección principal.
    def _apuntar_rutas(self, entrada, antecesores):
        camino = (*antecesores, entrada)
        for url in (entrada.url, *(vista.url for vista in entrada.vistas), *entrada.otras_rutas):
            anterior = self.rutas.get(url)
            if anterior is not None and anterior[-1] not in antecesores and anterior[-1] is not entrada:
                self.errores.append(
                    f"La dirección «{url}» está en dos entradas del menú: «{anterior[-1].codigo}» y «{entrada.codigo}»."
                )
            self.rutas[url] = camino
        for subseccion in entrada.subsecciones:
            self._apuntar_rutas(subseccion, camino)

    # Apunta un error por cada escucha de un eventos_sw que ningún módulo emite (suele ser una errata).
    def _comprobar_escuchas(self):
        for evento in self.escuchas:
            if evento not in self.emite:
                self.errores.append(f"Algún módulo escucha «{evento}», pero ningún módulo lo emite.")

    # Apunta un error por cada permiso que nombra un rol que no es del sistema, y por cada cometido que da
    # un permiso que nadie declara (suele ser una errata).
    def _comprobar_permisos(self):
        for permiso in self.permisos.values():
            for rol in permiso.roles:
                if rol not in ROLES_DEL_SISTEMA:
                    self.errores.append(
                        f"El permiso «{permiso.codigo}» da por defecto el rol «{rol}», que no es de los del sistema "
                        f"({', '.join(ROLES_DEL_SISTEMA)})."
                    )
        for cometido in self.cometidos.values():
            for codigo in cometido.permisos:
                if codigo not in self.permisos:
                    self.errores.append(f"El cometido «{cometido.codigo}» da el permiso «{codigo}», que nadie declara.")

    # Apunta un error por cada texto de ayuda de una sección que no existe en el menú.
    def _comprobar_ayuda(self):
        secciones = {entrada.codigo for seccion in self.menu for entrada in _entradas_y_subsecciones(seccion)}
        for seccion in self.ayuda:
            if seccion not in secciones:
                self.errores.append(f"Hay un texto de ayuda para «{seccion}», pero esa sección no está en el menú.")


# Devuelve una entrada de menú y todas sus subsecciones, a cualquier profundidad. La usa el registro al
# apuntar las entradas, al buscar la de la ayuda y al comprobar los textos de ayuda.
def _entradas_y_subsecciones(entrada):
    yield entrada
    for subseccion in entrada.subsecciones:
        yield from _entradas_y_subsecciones(subseccion)


# Dice si una ruta de carpeta está dentro de otra. Se usa para saber si una app es del proyecto (está
# dentro de su carpeta) o viene de Django o de una librería instalada.
def _esta_dentro(ruta, raiz):
    return Path(ruta).resolve().is_relative_to(Path(raiz).resolve())


# Función que dice si una persona tiene un permiso en alguna parte, para mostrarle o no las entradas del
# menú que piden un permiso. «base» no puede importar el módulo «permisos» (está en una capa superior),
# así que es «permisos» quien la presta al arrancar, con registrar_comprobador_de_permisos(). Mientras no
# haya ninguna, las entradas con permiso no se muestran a nadie.
_comprobador_de_permisos = None


# Guarda la función que comprueba permisos. La llama PermisosConfig.ready().
#   - funcion: recibe (usuario, código del permiso) y devuelve True o False.
def registrar_comprobador_de_permisos(funcion):
    global _comprobador_de_permisos
    _comprobador_de_permisos = funcion


# Dice si una persona puede ver una entrada del menú: si no pide permiso, sí; si su función «tambien_si»
# dice que sí, también; si no, pregunta a la función registrada si tiene el permiso. La usa base/contexto.py al preparar el menú.
#   - usuario: quien mira.
#   - entrada: la EntradaDeMenu.
def puede_ver_entrada(usuario, entrada):
    if not entrada.permiso:
        return True
    if entrada.tambien_si and import_string(entrada.tambien_si)(usuario):
        return True
    return _comprobador_de_permisos is not None and _comprobador_de_permisos(usuario, entrada.permiso)


# El registro único de la aplicación. Todo el código lo importa desde aquí:
#   from base.registro import registro
registro = RegistroDeModulos()
