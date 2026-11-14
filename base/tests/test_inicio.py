"""
Pruebas de la portada, «Inicio» (base/inicio.py), con módulos de mentira: las tarjetas salen en el orden
de la disposición, se saltan las que no tocan y las filas vacías, y la comprobación avisa de los errores
de la disposición. (Las pantallas con los módulos de verdad se prueban en proyectos/tests/test_inicio.py y
comunicaciones/tests/test_inicio.py.)
"""

from django.test import RequestFactory, SimpleTestCase, override_settings

from base.contrato import ApartadoDeTarjeta, FilaDeResumen, ResumenDeTarjeta, TarjetaDeInicio
from base.inicio import filas_de, problemas_de_la_disposicion
from base.pruebas import contratos_de_prueba, modulo_falso

# Disposición de mentira: dos filas en el panel; la segunda, con una tarjeta que no toca.
DISPOSICION = {"panel": (("alfa.uno", "alfa.dos"), ("alfa.nada",)), "mis_datos": ()}


# Función de mentira de la tarjeta «alfa.uno»: una línea con el alias de quien mira.
def resumen_uno(usuario):
    return ResumenDeTarjeta(apartados=(ApartadoDeTarjeta(filas=(FilaDeResumen(f"Hola, {usuario}"),)),))


# Función de mentira de la tarjeta «alfa.dos»: sin apartados.
def resumen_dos(usuario):
    return ResumenDeTarjeta(enlace="/dos/", boton="Ir")


# Función de mentira de la tarjeta «alfa.nada»: a nadie le toca.
def resumen_nada(usuario):
    return None


ALFA = modulo_falso(
    "alfa",
    tarjetas_de_inicio=(
        TarjetaDeInicio("alfa.uno", "Uno", "base.tests.test_inicio.resumen_uno"),
        TarjetaDeInicio("alfa.dos", "Dos", "base.tests.test_inicio.resumen_dos"),
        TarjetaDeInicio("alfa.nada", "Nada", "base.tests.test_inicio.resumen_nada"),
    ),
)


class PruebasDeInicio(SimpleTestCase):
    """Cómo junta base/inicio.py las tarjetas."""

    # Las tarjetas salen en el orden de la disposición; la fila que solo tenía «alfa.nada» desaparece.
    @override_settings(DISPOSICION_DEL_INICIO="base.tests.test_inicio.DISPOSICION")
    def test_filas(self):
        peticion = RequestFactory().get("/")
        peticion.user = "Nutria"
        with contratos_de_prueba(ALFA):
            filas = filas_de("panel", peticion)
        self.assertEqual([[pintada.tarjeta.codigo for pintada in fila] for fila in filas], [["alfa.uno", "alfa.dos"]])
        self.assertEqual(filas[0][0].resumen.apartados[0].filas[0].texto, "Hola, Nutria")

    # La comprobación avisa de lo declarado sin colocar, de lo colocado sin declarar, de lo repetido y de
    # las pantallas que no existen.
    def test_problemas(self):
        problemas = problemas_de_la_disposicion(
            {"panel": (("alfa.uno", "alfa.uno"), ("beta.fantasma",)), "portada": ()},
            declaradas={"alfa.uno", "alfa.dos"},
        )
        self.assertEqual(len(problemas), 4)
        self.assertIn("sale dos veces", problemas[0])
        self.assertTrue(any("beta.fantasma" in problema for problema in problemas))
        self.assertTrue(any("«alfa.dos» no está colocada" in problema for problema in problemas))
        self.assertTrue(any("pantalla desconocida" in problema for problema in problemas))

    # La disposición de verdad (config/inicio.py) está bien con los módulos de verdad.
    def test_disposicion_real(self):
        self.assertEqual(problemas_de_la_disposicion(), [])
