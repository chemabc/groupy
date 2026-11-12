"""
Funciones receptoras de mentira para las pruebas de eventos_sw. Se nombran como texto en los contratos
de prueba («eventos_sw.tests.receptores.anotar»), igual que haría un módulo de verdad.
"""

# Lista donde «anotar» deja los datos de cada aviso recibido. Las pruebas la vacían al empezar.
recibidos = []


# Receptor que apunta los datos que recibe, para comprobar que ha llegado y con qué.
def anotar(**datos):
    recibidos.append(datos)


# Receptor que siempre falla, para comprobar los reintentos y que un fallo deshace lo que debe.
def fallar(**datos):
    raise ValueError("Fallo a propósito de la prueba.")
