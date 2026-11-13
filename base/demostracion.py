"""
Datos y formulario de demostración para la pantalla «Inicio → Componentes».

Sirven para ver funcionando la tabla filtrable (en sus dos modos) y el botón «copiar» mientras no hay
tablas de verdad. Los datos son inventados, se generan en memoria y no tocan la base de datos.
"""

import datetime
import random
from functools import cache

from django import forms
from django.urls import reverse_lazy

from .formularios import CampoDePalabras, SelectorDePalabras
from .tablas import Columna, Filtro, FuenteDeLista, Tabla

# Piezas con las que se inventan las filas. Llevan tildes a propósito, para probar la búsqueda.
TIPOLOGIAS = [("reunion", "Reunión"), ("accion", "Acción"), ("recaudatorio", "Recaudatorio"), ("generico", "Genérico")]
GRUPOS = ["Asamblea de Málaga", "Comisión de Logística", "Asamblea de Córdoba", "Grupo de Comunicación",
          "Asamblea de Ávila", "Comisión de Cuidados"]
TEMAS = ["presupuesto", "campaña de otoño", "local nuevo", "jornadas", "acogida", "difusión", "cartelería"]


# Inventa filas de actividades: título, tipología, grupo, fecha y plazas. Siempre las mismas para el
# mismo número (semilla fija), para que la demostración y las pruebas sean repetibles. Se guarda el
# resultado (@cache) para no generarlas en cada visita.
#   - cuantas: número de filas.
@cache
def filas_inventadas(cuantas):
    azar = random.Random(cuantas)
    inicio = datetime.date(2026, 1, 1)
    filas = []
    for numero in range(1, cuantas + 1):
        tipologia, nombre_de_tipologia = azar.choice(TIPOLOGIAS)
        filas.append(
            {
                "titulo": f"{nombre_de_tipologia}: {azar.choice(TEMAS)} n.º {numero}",
                "tipologia": tipologia,
                "nombre_de_tipologia": nombre_de_tipologia,
                "grupo": azar.choice(GRUPOS),
                "fecha": inicio + datetime.timedelta(days=azar.randrange(365)),
                "plazas": azar.randrange(5, 120),
            }
        )
    return filas


# Crea una tabla de demostración con las filas inventadas.
#   - request: la petición (de ella salen los filtros).
#   - identificador: nombre de la tabla en la página y en la dirección.
#   - cuantas: número de filas inventadas.
def tabla_de_demostracion(request, identificador, cuantas):
    return Tabla(
        request,
        identificador=identificador,
        columnas=[
            Columna("titulo", "Título"),
            Columna("nombre_de_tipologia", "Tipología"),
            Columna("grupo", "Grupo"),
            Columna("fecha", "Fecha"),
            Columna("plazas", "Plazas"),
        ],
        fuente=FuenteDeLista(filas_inventadas(cuantas), campos_de_busqueda=["titulo", "grupo"]),
        filtros=[Filtro("tipologia", "Tipología", opciones=tuple(TIPOLOGIAS))],
    )


class FormularioDeDemostracion(forms.Form):
    """Formulario de ejemplo para probar el botón «copiar» de cada campo. No guarda nada."""

    titulo = forms.CharField(
        label="Título",
        max_length=120,
        initial="Jornadas de acogida",
        help_text="Nombre corto de la actividad, tal como se verá en las listas.",
    )
    descripcion = forms.CharField(
        label="Descripción",
        widget=forms.Textarea(attrs={"rows": 3}),
        initial="Presentación de la asamblea para las personas recién llegadas.",
        help_text="Para qué sirve y qué se va a hacer. Se puede copiar al cartel o a las redes.",
    )
    fecha = forms.DateField(
        label="Fecha",
        # format: <input type="date"> exige la fecha como AAAA-MM-DD.
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        initial=datetime.date(2026, 12, 5),
        help_text="Día en que se celebra.",
    )
    plazas = forms.IntegerField(
        label="Plazas",
        initial=40,
        min_value=1,
        help_text="Número máximo de personas que pueden inscribirse.",
    )
    tipologia = forms.ChoiceField(
        label="Tipología",
        choices=TIPOLOGIAS,
        initial="reunion",
        help_text="Tipo de actividad. Decide qué datos extra se piden.",
    )
    etiquetas = CampoDePalabras(
        label="Etiquetas",
        required=False,
        initial=["acogida"],
        # Sugiere las etiquetas comunes (sin organización). En los módulos de verdad, la dirección lleva la
        # organización: «?organizacion=3».
        widget=SelectorDePalabras(url_de_sugerencias=reverse_lazy("etiquetas:sugerencias")),
        help_text="Palabras para encontrar la actividad. Escribe y pulsa Intro, o elige una sugerencia.",
    )
    publica = forms.BooleanField(
        label="Pública",
        required=False,
        help_text="Si cualquiera puede verla sin iniciar sesión. Una casilla no lleva botón «copiar».",
    )
