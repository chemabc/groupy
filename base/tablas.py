"""
Tabla filtrable: el componente común para cualquier lista de la aplicación (ver docs/diseno.md,
apartado 3.6, y la premisa 4: «filtrar cualquier tabla al momento»).

Cómo se usa desde una vista:

    tabla = Tabla(
        request,
        identificador="eventos",
        columnas=[Columna("titulo", "Título"), Columna("fecha", "Fecha")],
        fuente=FuenteDeConsulta(Evento.objects.all(), campos_de_busqueda=["titulo", "descripcion"]),
        filtros=[Filtro("tipologia", "Tipología", opciones=[("reunion", "Reunión"), ...])],
    )
    plantilla = tabla.plantilla_parcial()
    if plantilla:
        return render(request, plantilla, {"tabla": tabla})
    return render(request, "eventos/lista.html", {"tabla": tabla})

y en la plantilla: {% include "base/tabla.html" %}.

Dónde se filtra:
- Si hay hasta LIMITE_EN_NAVEGADOR filas (500), van todas a la página y se filtran y ordenan en el
  navegador al instante (componente «tablaLocal» de interfaz.js). Cuesta una sola consulta.
- Si hay más, se filtra en el servidor: htmx manda la búsqueda 300 ms después de dejar de escribir y
  recibe solo el resultado. Se cargan TAMANO_DE_PAGINA filas y un botón «Mostrar más».

Se puede filtrar con el buscador general (todas las palabras, en los campos de búsqueda), con los
desplegables de categoría y con el cuadro de texto bajo el título de cada columna. Nunca importan las
tildes ni las mayúsculas.

Los filtros van en la dirección (con el identificador delante, para que quepan varias tablas en la
misma página): «?eventos-q=asamblea&eventos-c-titulo=jornadas&eventos-tipologia=reunion&eventos-orden=-fecha».
"""

import datetime
import json
import unicodedata
from dataclasses import dataclass
from functools import reduce
from operator import and_, or_

from django.db.models import Q
from django.urls import reverse

# Máximo de filas que se mandan enteras para filtrar en el navegador. El superadmin podrá bajarlo.
LIMITE_EN_NAVEGADOR = 500

# Filas que se cargan de cada vez cuando se filtra en el servidor (y con cada «Mostrar más»).
TAMANO_DE_PAGINA = 100


# Pasa un texto a minúsculas y le quita las tildes y diéresis («Reunión» → «reunion»), para que las
# búsquedas no dependan de ellas. Se usa al preparar el texto de búsqueda de cada fila; interfaz.js hace
# lo mismo con lo que escribe la persona.
def normalizar(texto):
    descompuesto = unicodedata.normalize("NFD", str(texto))
    return "".join(letra for letra in descompuesto if not unicodedata.combining(letra)).lower()


# Da a un texto la «forma de frase» con la que se guardan las etiquetas: sin espacios de más, sin
# tildes ni diéresis, todo en minúsculas salvo la primera letra («  REUNIÓN  general» → «Reunion
# general»). La ñ se conserva, porque es otra letra y no una tilde («año» no es «ano»). La usan las
# etiquetas al guardarse y al buscarse; interfaz.js hace lo mismo (formaDeFrase) en el selector.
def forma_de_frase(texto):
    descompuesto = unicodedata.normalize("NFD", " ".join(str(texto).split()))
    letras = []
    for letra in descompuesto:
        # La virgulilla (U+0303) sobre una n es la de la ñ: se queda. Las demás marcas se quitan.
        if unicodedata.combining(letra) and not (letra == "̃" and letras and letras[-1] in "nN"):
            continue
        letras.append(letra)
    minusculas = unicodedata.normalize("NFC", "".join(letras)).lower()
    return minusculas[:1].upper() + minusculas[1:]


@dataclass(frozen=True)
class Columna:
    """Una columna de la tabla."""

    # Nombre del campo del modelo (o clave del diccionario) que se muestra.
    campo: str
    # Título visible de la columna.
    titulo: str
    # Si se puede ordenar pulsando su título.
    ordenable: bool = True
    # Si lleva, bajo el título, un cuadro para filtrarla escribiendo un texto.
    filtrable: bool = True
    # Nombre de la ruta de la ficha de cada fila («administracion:persona»). Si lo hay, el texto de la
    # celda es un enlace a esa ficha, con la clave de la fila (pk) como parámetro.
    enlace: str = ""


@dataclass(frozen=True)
class Filtro:
    """Un desplegable para filtrar por categoría (tipología, grupo, estado…)."""

    # Campo por el que se filtra (debe coincidir exactamente con el valor elegido).
    campo: str
    # Nombre visible del desplegable.
    titulo: str
    # Opciones: pares (valor, nombre visible).
    opciones: tuple


class FuenteDeConsulta:
    """
    Filas que salen de la base de datos (un QuerySet de Django). La búsqueda usa «unaccent» de
    PostgreSQL, que no distingue tildes.
    """

    # Guarda la consulta y los campos en los que se busca el texto escrito.
    def __init__(self, consulta, campos_de_busqueda):
        self.consulta = consulta
        self.campos_de_busqueda = list(campos_de_busqueda)

    # Devuelve una fuente con solo las filas que contienen todas las palabras (cada una en alguno de los
    # campos de búsqueda), que tienen los valores de categoría elegidos y cuyas columnas contienen el texto
    # escrito en su filtro.
    #   - palabras: lista de palabras ya normalizadas.
    #   - categorias: diccionario de campo a valor elegido.
    #   - por_columna: diccionario de campo a texto ya normalizado.
    def filtrar(self, palabras, categorias, por_columna):
        consulta = self.consulta
        for campo, texto in por_columna.items():
            # En los campos de texto se quitan las tildes en la base de datos (unaccent). En los demás
            # (fechas, números), PostgreSQL los compara como texto: las fechas, en formato AAAA-MM-DD.
            tipo = self.consulta.model._meta.get_field(campo).get_internal_type()
            busqueda = "unaccent__icontains" if tipo in ("CharField", "TextField") else "icontains"
            consulta = consulta.filter(**{f"{campo}__{busqueda}": texto})
        for palabra in palabras:
            # Una condición por campo, unidas con «o»: la palabra puede estar en cualquiera de ellos.
            en_algun_campo = [Q(**{f"{campo}__unaccent__icontains": palabra}) for campo in self.campos_de_busqueda]
            consulta = consulta.filter(reduce(or_, en_algun_campo))
        if categorias:
            consulta = consulta.filter(reduce(and_, [Q(**{campo: valor}) for campo, valor in categorias.items()]))
        return FuenteDeConsulta(consulta, self.campos_de_busqueda)

    # Devuelve una fuente ordenada por un campo. Se añade la clave primaria para que el orden sea siempre
    # el mismo entre una carga y la siguiente («Mostrar más» no repite ni salta filas).
    def ordenar(self, campo, descendente):
        signo = "-" if descendente else ""
        return FuenteDeConsulta(self.consulta.order_by(f"{signo}{campo}", f"{signo}pk"), self.campos_de_busqueda)

    # Cuántas filas hay (una consulta COUNT).
    def contar(self):
        return self.consulta.count()

    # Devuelve las filas de la posición «desde» a la «hasta» (sin incluirla), con una sola consulta.
    def cortar(self, desde, hasta):
        return list(self.consulta[desde:hasta])

    # Valor de un campo en una fila.
    @staticmethod
    def valor(fila, campo):
        return getattr(fila, campo)


class FuenteDeLista:
    """
    Filas que están ya en memoria, como lista de diccionarios. Sirve para los datos de demostración y
    para listas calculadas que no salen de una tabla.
    """

    # Guarda las filas y los campos en los que se busca el texto escrito.
    def __init__(self, filas, campos_de_busqueda):
        self.filas = filas
        self.campos_de_busqueda = list(campos_de_busqueda)

    # Igual que FuenteDeConsulta.filtrar, pero recorriendo la lista. Los filtros de columna comparan con
    # el texto tal como se ve en la celda (las fechas, DD/MM/AAAA), igual que el filtro del navegador.
    def filtrar(self, palabras, categorias, por_columna):
        filas = [
            fila
            for fila in self.filas
            if all(any(palabra in normalizar(fila[campo]) for campo in self.campos_de_busqueda) for palabra in palabras)
            and all(str(fila[campo]) == valor for campo, valor in categorias.items())
            and all(texto in normalizar(celda_de(fila[campo]).texto) for campo, texto in por_columna.items())
        ]
        return FuenteDeLista(filas, self.campos_de_busqueda)

    # Igual que FuenteDeConsulta.ordenar.
    def ordenar(self, campo, descendente):
        return FuenteDeLista(sorted(self.filas, key=lambda fila: fila[campo], reverse=descendente), self.campos_de_busqueda)

    # Cuántas filas hay.
    def contar(self):
        return len(self.filas)

    # Filas de la posición «desde» a la «hasta».
    def cortar(self, desde, hasta):
        return self.filas[desde:hasta]

    # Valor de un campo en una fila.
    @staticmethod
    def valor(fila, campo):
        return fila[campo]


@dataclass
class Celda:
    """Una celda ya preparada para pintar."""

    # Texto que se ve.
    texto: str
    # Valor con el que se ordena en el navegador (las fechas, en formato AAAA-MM-DD).
    valor: str
    # Dirección a la que lleva la celda, si es un enlace (ver Columna.enlace).
    enlace: str = ""


@dataclass
class FilaPintada:
    """Una fila ya preparada para pintar: sus celdas y los datos que usa el filtro del navegador."""

    # Celdas, en el orden de las columnas.
    celdas: list
    # Texto de los campos de búsqueda, normalizado, para buscar en el navegador (los mismos campos en los
    # que busca el servidor, para que las dos formas encuentren lo mismo).
    texto: str
    # Pares (campo, valor) de los filtros de categoría, para filtrar en el navegador.
    categorias: list


class Tabla:
    """
    Una tabla filtrable lista para pintar con base/tabla.html. Al crearla, lee los filtros de la
    dirección, decide si se filtra en el navegador o en el servidor y prepara las filas.
    """

    # Prepara la tabla.
    #   - request: la petición (de ella salen los filtros y las cabeceras de htmx).
    #   - identificador: nombre corto y único en la página; va delante de cada parámetro de la dirección.
    #   - columnas: lista de Columna.
    #   - fuente: FuenteDeConsulta o FuenteDeLista.
    #   - filtros: lista de Filtro (desplegables de categoría).
    #   - limite: máximo de filas para filtrar en el navegador.
    #   - tamano_de_pagina: filas por carga cuando se filtra en el servidor.
    def __init__(self, request, identificador, columnas, fuente, filtros=(), limite=LIMITE_EN_NAVEGADOR,
                 tamano_de_pagina=TAMANO_DE_PAGINA):
        self.request = request
        self.identificador = identificador
        self.columnas = list(columnas)
        self.filtros = list(filtros)
        self.limite = limite
        self.tamano_de_pagina = tamano_de_pagina
        self._leer_parametros(request.GET)
        self._preparar(fuente)

    # Nombre de un parámetro de esta tabla en la dirección: «eventos-q», «eventos-orden»…
    def parametro(self, nombre):
        return f"{self.identificador}-{nombre}"

    # Lee de la dirección la búsqueda, el orden, las categorías elegidas y desde qué fila cargar. Descarta
    # lo que no corresponde a esta tabla (un orden por una columna que no existe, una categoría que no
    # está entre las opciones), para que nadie pueda ordenar o filtrar por campos no previstos.
    def _leer_parametros(self, parametros):
        self.busqueda = parametros.get(self.parametro("q"), "").strip()
        self.palabras = normalizar(self.busqueda).split()
        ordenables = {columna.campo for columna in self.columnas if columna.ordenable}
        orden = parametros.get(self.parametro("orden"), "")
        self.orden = orden if orden.lstrip("-") in ordenables else ""
        # Texto escrito en el filtro de cada columna (tal cual, para volver a pintarlo) y normalizado.
        self.textos_de_columna = {}
        for columna in self.columnas:
            texto = parametros.get(self.parametro(f"c-{columna.campo}"), "").strip() if columna.filtrable else ""
            if texto:
                self.textos_de_columna[columna.campo] = texto
        self.por_columna = {campo: normalizar(texto) for campo, texto in self.textos_de_columna.items()}
        self.categorias = {}
        for filtro in self.filtros:
            valor = parametros.get(self.parametro(filtro.campo), "")
            if valor in {str(opcion) for opcion, _nombre in filtro.opciones}:
                self.categorias[filtro.campo] = valor
        try:
            self.desde = max(0, int(parametros.get(self.parametro("desde"), 0)))
        except ValueError:
            self.desde = 0

    # Decide el modo y carga las filas.
    def _preparar(self, fuente):
        self.fuente = fuente
        if self.orden:
            fuente = fuente.ordenar(self.orden.lstrip("-"), self.orden.startswith("-"))
        # Las peticiones de htmx solo llegan cuando ya se filtraba en el servidor: no hace falta tantear.
        if self.plantilla_parcial() is None:
            # Tanteo: se piden una fila más que el límite. Si no llega esa fila de más, caben todas.
            primeras = fuente.cortar(0, self.limite + 1)
            if len(primeras) <= self.limite:
                self.en_navegador = True
                self.filas = primeras
                self.total = len(primeras)
                self.hay_mas = False
                return
        self.en_navegador = False
        filtrada = fuente.filtrar(self.palabras, self.categorias, self.por_columna)
        self.total = filtrada.contar()
        self.filas = filtrada.cortar(self.desde, self.desde + self.tamano_de_pagina)
        self.hay_mas = self.desde + len(self.filas) < self.total

    # Si la petición es de htmx y pide solo una parte de esta tabla, devuelve la plantilla de esa parte:
    #   - «tabla-<id>-cuerpo»: tras escribir en un filtro o cambiar un desplegable, solo las filas y el
    #     recuento (la cabecera no se toca, para no perder el cuadro en el que se está escribiendo);
    #   - «tabla-<id>-resultado»: tras cambiar el orden, la tabla entera con su cabecera;
    #   - «tabla-<id>-mas»: tras pulsar «Mostrar más», las filas siguientes.
    # Si no, devuelve None y la vista pinta la página entera.
    def plantilla_parcial(self):
        if self.request.headers.get("HX-Request") != "true":
            return None
        objetivo = self.request.headers.get("HX-Target", "")
        if objetivo == f"tabla-{self.identificador}-cuerpo":
            return "base/tabla_cuerpo.html"
        if objetivo == f"tabla-{self.identificador}-resultado":
            return "base/tabla_resultado.html"
        if objetivo == f"tabla-{self.identificador}-mas":
            return "base/tabla_filas.html"
        return None

    # Filas preparadas para pintar: texto de cada celda, valor para ordenar, texto de búsqueda y
    # categorías. Así la plantilla solo tiene que recorrerlas.
    def filas_pintadas(self):
        pintadas = []
        for fila in self.filas:
            celdas = [celda_de(self.fuente.valor(fila, columna.campo)) for columna in self.columnas]
            for celda, columna in zip(celdas, self.columnas):
                if columna.enlace:
                    celda.enlace = reverse(columna.enlace, args=[self.fuente.valor(fila, "pk")])
            pintadas.append(
                FilaPintada(
                    celdas=celdas,
                    texto=normalizar(" ".join(str(self.fuente.valor(fila, campo)) for campo in self.fuente.campos_de_busqueda)),
                    categorias=[(filtro.campo, str(self.fuente.valor(fila, filtro.campo))) for filtro in self.filtros],
                )
            )
        return pintadas

    # Columnas preparadas para la cabecera: título, si se puede ordenar, si está ordenada y en qué
    # sentido, y el orden que se pide al pulsarla (la primera vez ascendente; la segunda, descendente).
    def cabeceras(self):
        resultado = []
        for indice, columna in enumerate(self.columnas):
            actual = self.orden.lstrip("-") == columna.campo
            descendente = actual and self.orden.startswith("-")
            resultado.append(
                {
                    "columna": columna,
                    "indice": indice,
                    "actual": actual,
                    "flecha": ("▼" if descendente else "▲") if actual else "",
                    # Filtro de texto de la columna: nombre del parámetro y lo que ya hay escrito.
                    "parametro_filtro": self.parametro(f"c-{columna.campo}"),
                    "texto_filtro": self.textos_de_columna.get(columna.campo, ""),
                    # Sentido para los lectores de pantalla (atributo aria-sort).
                    "sentido": ("descending" if descendente else "ascending") if actual else "",
                    # Parámetro que manda htmx al pulsarla (filtrado en el servidor), ya en JSON.
                    "valores_al_pulsar": json.dumps(
                        {self.parametro("orden"): f"-{columna.campo}" if actual and not descendente else columna.campo}
                    ),
                }
            )
        return resultado

    # Desplegables preparados para pintar: nombre del parámetro, título y opciones con la elegida marcada.
    def desplegables(self):
        return [
            {
                "filtro": filtro,
                "parametro": self.parametro(filtro.campo),
                "opciones": [
                    {"valor": str(valor), "nombre": nombre, "elegida": self.categorias.get(filtro.campo) == str(valor)}
                    for valor, nombre in filtro.opciones
                ],
            }
            for filtro in self.filtros
        ]

    # Nombre del parámetro de la búsqueda en la dirección, para el buscador.
    @property
    def parametro_busqueda(self):
        return self.parametro("q")

    # Nombre del parámetro del orden en la dirección, para el campo oculto que lo guarda.
    @property
    def parametro_orden(self):
        return self.parametro("orden")

    # Posición de la última fila cargada más uno: cuántas se están mostrando, y desde dónde cargará el
    # siguiente «Mostrar más».
    def siguiente_desde(self):
        return self.desde + len(self.filas)

    # Parámetro que manda el botón «Mostrar más»: desde qué fila cargar, ya en JSON para htmx.
    def valores_de_mostrar_mas(self):
        return json.dumps({self.parametro("desde"): self.siguiente_desde()})


# Prepara una celda a partir del valor de un campo: las fechas se ven como DD/MM/AAAA y se ordenan como
# AAAA-MM-DD; lo vacío se ve vacío; lo demás, como texto. La usan Tabla y FuenteDeLista.
def celda_de(valor):
    if valor is None:
        return Celda("", "")
    if isinstance(valor, datetime.date):
        return Celda(valor.strftime("%d/%m/%Y"), valor.isoformat())
    return Celda(str(valor), str(valor))
