"""
Preferencias de presentación que cada persona puede elegir: tema, tamaño de letra y densidad.

Se aplican como atributos de <html> (data-tema, data-letra, data-densidad), que la hoja de estilos
(base/estilos/entrada.css) usa para cambiar colores, tamaños y espacios. Los valores de aquí deben
coincidir con los de esa hoja.

Las usan la pantalla «Configuración de mi cuenta → Usabilidad» (para pintar los botones) y el modelo Usuario (para
guardar la elección de cada persona y comprobar que es una opción válida).
"""

# Cada preferencia: clave (el atributo de <html> y el nombre del campo en el usuario), nombre visible y
# opciones (valor y nombre visible).
PREFERENCIAS = [
    ("tema", "Tema", [("claro", "Claro"), ("dia", "Día (más contraste)"), ("oscuro", "Oscuro")]),
    ("letra", "Letra", [("pequena", "Pequeña"), ("normal", "Normal"), ("grande", "Grande")]),
    ("densidad", "Densidad", [("comoda", "Cómoda"), ("compacta", "Compacta"), ("supercompacta", "Supercompacta")]),
]

# Las claves solas, en orden: «tema», «letra», «densidad».
CLAVES = [clave for clave, _nombre, _opciones in PREFERENCIAS]


# Devuelve las opciones (valor, nombre visible) de una preferencia, para usarlas como «choices» de un
# campo de Django.
#   - clave: «tema», «letra» o «densidad».
def opciones(clave):
    return next(lista for nombre, _titulo, lista in PREFERENCIAS if nombre == clave)


# Dice si un valor es una opción válida de una preferencia. Lo usa la vista que guarda la preferencia,
# para no guardar lo que mande un navegador manipulado.
#   - clave: nombre de la preferencia.
#   - valor: valor recibido.
def es_valida(clave, valor):
    return clave in CLAVES and valor in {valor_valido for valor_valido, _nombre in opciones(clave)}
