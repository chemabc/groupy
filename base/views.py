"""
Pantallas del módulo «base». De momento, las de la sección «Inicio», que sirven para ver funcionando la
plantilla general (menús, vistas, ayuda y tema) mientras no hay otros módulos.
"""

from django.shortcuts import render


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


# Pantalla «Inicio → Componentes»: escaparate de las piezas comunes de la interfaz. En la pieza 5 de la
# fase 0 mostrará la tabla filtrable y el botón «copiar».
def componentes(request):
    return render(request, "base/componentes.html")
