"""
Registro de módulos: reúne en un solo sitio lo que declara el contrato de cada módulo.

Se carga una sola vez al arrancar Django (desde BaseConfig.ready, en base/apps.py). A partir de ahí,
cualquier parte de la aplicación pregunta aquí en lugar de recorrer los módulos: el menú lee
«registro.menu», eventos_sw lee «registro.escuchas», la pantalla de permisos lee «registro.permisos»…

Mientras carga, el registro apunta los errores de declaración que encuentra (códigos repetidos, un
módulo que escucha un eventos_sw que nadie emite…). No los lanza: las comprobaciones de Django
(base/comprobaciones.py) los muestran todos juntos al arrancar o al ejecutar «manage.py check».
"""

from pathlib import Path

from .contrato import ROLES_DEL_SISTEMA, Capa, ModuloConfig

# Apartados del contrato que son listas de fichas con un código único, y el nombre del campo que hace de
# código en cada una. El registro los recorre todos igual: comprueba el prefijo y que no se repitan.
APARTADOS_CON_CODIGO = {
    "permisos": "codigo",
    "cometidos": "codigo",
    "anclas": "tipo",
    "huecos": "codigo",
    "fuentes_de_calendario": "codigo",
    "emite": "nombre",
    "grupos_de_etiquetas": "codigo",
    "limpiables": "codigo",
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
        # Datos de ejemplo de cada módulo, por su etiqueta.
        self.datos_de_ejemplo = {}
        # Secciones del menú izquierdo, ya ordenadas.
        self.menu = []
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
    def cargar(self, configuraciones, raiz=None):
        self._vaciar()
        for config in configuraciones:
            if isinstance(config, ModuloConfig):
                self._cargar_modulo(config)
            elif raiz is not None and _esta_dentro(config.path, raiz):
                self.errores.append(
                    f"El módulo «{config.label}» es del proyecto pero su apps.py no hereda de "
                    "ModuloConfig, así que no declara su contrato."
                )
        self._comprobar_escuchas()
        self._comprobar_ayuda()
        self._comprobar_permisos()
        # Ordena el menú por su número de orden y, a igualdad, por nombre.
        self.menu.sort(key=lambda entrada: (entrada.orden, entrada.nombre))
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
        if config.datos_de_ejemplo is not None:
            self.datos_de_ejemplo[etiqueta] = config.datos_de_ejemplo
        # Menú: se comprueba el prefijo de cada entrada y de sus subsecciones.
        for entrada in config.menu:
            for codigo in _codigos_de_menu(entrada):
                self._comprobar_prefijo(etiqueta, "menu", codigo)
            self.menu.append(entrada)
        # Ayuda: un texto por sección.
        for ayuda in config.ayuda:
            if ayuda.seccion in self.ayuda:
                self.errores.append(f"La sección «{ayuda.seccion}» tiene dos textos de ayuda.")
            self.ayuda[ayuda.seccion] = ayuda

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
        for url in (entrada.url, *(vista.url for vista in entrada.vistas)):
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
        secciones = {codigo for entrada in self.menu for codigo in _codigos_de_menu(entrada)}
        for seccion in self.ayuda:
            if seccion not in secciones:
                self.errores.append(f"Hay un texto de ayuda para «{seccion}», pero esa sección no está en el menú.")


# Devuelve el código de una entrada de menú y los de todas sus subsecciones, a cualquier profundidad.
# La usan las comprobaciones de prefijo y de ayuda.
def _codigos_de_menu(entrada):
    yield entrada.codigo
    for subseccion in entrada.subsecciones:
        yield from _codigos_de_menu(subseccion)


# Dice si una ruta de carpeta está dentro de otra. Se usa para saber si una app es del proyecto (está
# dentro de su carpeta) o viene de Django o de una librería instalada.
def _esta_dentro(ruta, raiz):
    return Path(ruta).resolve().is_relative_to(Path(raiz).resolve())


# El registro único de la aplicación. Todo el código lo importa desde aquí:
#   from base.registro import registro
registro = RegistroDeModulos()
