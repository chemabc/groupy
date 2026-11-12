"""
Ayudas para las pruebas de cualquier módulo.

- modulo_falso: crea un módulo de mentira con el contrato que se quiera, sin carpeta ni apps.py.
- contratos_de_prueba: añade módulos de mentira al registro real mientras dura un bloque «with» y
  después lo deja como estaba. Sirve para probar eventos_sw, el menú o los permisos con declaraciones
  inventadas, sin tocar los contratos de los módulos de verdad.
- crear_usuario_de_prueba: crea un usuario con el modelo de usuario de la aplicación, sin importarlo.
- PruebaDePantalla: clase de prueba con la sesión ya iniciada y comprobar_consultas(), la prueba de
  número de consultas que lleva cada pantalla nueva (ver docs/diseno.md, apartado 3.6).
"""

from contextlib import contextmanager

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase

from .contrato import Capa, ModuloConfig
from .registro import registro


# Crea la configuración de un módulo de mentira con la etiqueta y los apartados indicados.
#   - etiqueta: nombre del módulo (p. ej. «alfa»).
#   - apartados: los atributos del contrato que se quieren rellenar (permisos=…, menu=…). Si no se
#     indica la capa, es funcional.
def modulo_falso(etiqueta, **apartados):
    # Clase creada al vuelo que hereda de ModuloConfig. «path» se fija a mano porque el módulo no existe
    # en disco y Django lo pediría.
    clase = type(f"{etiqueta}Config", (ModuloConfig,), {"capa": Capa.FUNCIONAL, "path": "/tmp", **apartados})
    return clase(etiqueta, None)


# Bloque «with» que recarga el registro con los módulos reales más los de mentira y, al salir, devuelve
# el registro a su estado anterior aunque la prueba falle. Ejemplo:
#     with contratos_de_prueba(modulo_falso("alfa", emite=(Emision("alfa.creado", "…"),))):
#         emitir("alfa.creado", id=1)
@contextmanager
def contratos_de_prueba(*modulos_falsos):
    # Copia de todo lo que contiene el registro, para restaurarlo al final.
    copia = dict(registro.__dict__)
    registro.cargar([*apps.get_app_configs(), *modulos_falsos])
    try:
        yield registro
    finally:
        registro.__dict__.clear()
        registro.__dict__.update(copia)


# Contraseña de los usuarios que crean las pruebas.
CONTRASENA_DE_PRUEBA = "contraseña-de-prueba"


# Crea y devuelve un usuario de prueba. Usa get_user_model() en lugar de importar «usuarios», porque
# «base» está en una capa inferior y no puede depender de él.
#   - nombre: su alias (o lo que el modelo use para entrar).
#   - otros: más campos del usuario.
def crear_usuario_de_prueba(nombre="Prueba", **otros):
    modelo = get_user_model()
    return modelo._default_manager.create_user(
        **{modelo.USERNAME_FIELD: nombre}, password=CONTRASENA_DE_PRUEBA, **otros
    )


# Tope de consultas por pantalla del presupuesto de rendimiento (docs/diseno.md, apartado 3.6).
MAXIMO_DE_CONSULTAS = 15


class PruebaDePantalla(TestCase):
    """
    Clase de la que heredan las pruebas de pantalla. Cada prueba empieza con la sesión iniciada como
    self.usuario (como nada se ve sin sesión, si no, todas las pantallas llevarían a la entrada). Añade
    comprobar_consultas(), que mide cuántas consultas a la base de datos hace una pantalla y comprueba el
    presupuesto de rendimiento.

    Si una prueba hija redefine setUpTestData o setUp, debe llamar a super().
    """

    # Una vez para toda la clase: crea el usuario con el que se inicia sesión.
    @classmethod
    def setUpTestData(cls):
        cls.usuario = crear_usuario_de_prueba()

    # Antes de cada prueba: inicia sesión sin pasar por la pantalla de entrada.
    def setUp(self):
        self.client.force_login(self.usuario)

    # Abre la pantalla y comprueba tres cosas:
    #   1. que hace exactamente «consultas» consultas (así, cualquier cambio en su coste se nota);
    #   2. que no pasa del tope de MAXIMO_DE_CONSULTAS;
    #   3. que, después de crear más filas con crear_mas_datos(), sigue haciendo las mismas. Si crece,
    #      es que hay una consulta por cada fila, el error de rendimiento más típico.
    # Antes de medir hace una visita de calentamiento, para que lo que se guarda en la caché tras la
    # primera visita (permisos, audiencias) no cuente: se mide la visita normal, no la primera.
    #   - url: dirección de la pantalla.
    #   - consultas: número exacto de consultas esperado.
    #   - crear_mas_datos: función sin parámetros que añade filas a lo que muestra la pantalla. Solo
    #     puede ser None si la pantalla no muestra ninguna lista.
    # Devuelve la respuesta de la última visita, por si la prueba quiere revisar su contenido.
    def comprobar_consultas(self, url, consultas, crear_mas_datos):
        self.assertLessEqual(
            consultas,
            MAXIMO_DE_CONSULTAS,
            f"{url} hace {consultas} consultas; el presupuesto es de {MAXIMO_DE_CONSULTAS} como mucho.",
        )
        self._visitar(url)
        with self.assertNumQueries(consultas):
            respuesta = self._visitar(url)
        if crear_mas_datos is not None:
            crear_mas_datos()
            # Se mide igual: con más filas, las consultas deben ser las mismas.
            with self.assertNumQueries(consultas):
                respuesta = self._visitar(url)
        return respuesta

    # Pide la pantalla y comprueba que responde bien (código 200). La usa comprobar_consultas.
    def _visitar(self, url):
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200, f"{url} responde con el código {respuesta.status_code}.")
        return respuesta
