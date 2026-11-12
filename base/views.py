"""
Pantallas del módulo «base». De momento, las de la sección «Inicio», que sirven para ver funcionando la
plantilla general (menús, vistas, ayuda y tema) mientras no hay otros módulos.
"""

from django.shortcuts import render

from .demostracion import FormularioDeDemostracion, tabla_de_demostracion


# Preferencias de presentación que se pueden elegir en «Inicio → Estructura»: clave (el atributo de
# <html> y el nombre con el que se guarda), nombre visible y opciones (valor y nombre visible). Los
# valores deben coincidir con los de base/estilos/entrada.css.
PREFERENCIAS = [
    ("tema", "Tema", [("claro", "Claro"), ("dia", "Día (más contraste)"), ("oscuro", "Oscuro")]),
    ("letra", "Letra", [("pequena", "Pequeña"), ("normal", "Normal"), ("grande", "Grande")]),
    ("densidad", "Densidad", [("comoda", "Cómoda"), ("compacta", "Compacta"), ("supercompacta", "Supercompacta")]),
]


# Pantalla «Inicio → Estructura»: explica las partes de la plantilla y permite cambiar el tema, el tamaño
# de letra y la densidad. Se llega desde el menú izquierdo o desde el nombre de la aplicación.
def inicio(request):
    return render(request, "base/inicio.html", {"preferencias": PREFERENCIAS})


# Pantalla «Inicio → Componentes»: escaparate de las piezas comunes de la interfaz, con datos inventados.
# Muestra dos tablas filtrables (una pequeña, que se filtra en el navegador, y otra grande, que se filtra
# en el servidor) y un formulario para probar el botón «copiar». Si htmx pide solo una parte de una de las
# tablas (al filtrar en el servidor o con «Mostrar más»), devuelve solo esa parte.
def componentes(request):
    tablas = [
        tabla_de_demostracion(request, "pequena", 200),
        tabla_de_demostracion(request, "grande", 2000),
    ]
    for tabla in tablas:
        plantilla = tabla.plantilla_parcial()
        if plantilla:
            return render(request, plantilla, {"tabla": tabla})
    contexto = {"tabla_pequena": tablas[0], "tabla_grande": tablas[1], "formulario": FormularioDeDemostracion()}
    return render(request, "base/componentes.html", contexto)
