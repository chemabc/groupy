"""
Pruebas de la propia herramienta de medición: comprobar_consultas() debe aprobar una pantalla bien
hecha y suspender una que crece con las filas o que se pasa del presupuesto.
"""

from django.test import override_settings

from base.pruebas import PruebaDePantalla

from . import pantallas_de_prueba


# Todas las pruebas de esta clase usan las pantallas de mentira como direcciones de la aplicación.
@override_settings(ROOT_URLCONF="base.tests.pantallas_de_prueba")
class PruebasDeComprobarConsultas(PruebaDePantalla):
    """Comprueba que comprobar_consultas() distingue las pantallas buenas de las malas."""

    # Antes de cada prueba, la lista de filas vuelve a tener una sola fila.
    def setUp(self):
        super().setUp()
        pantallas_de_prueba.filas[:] = ["primera"]

    # Una pantalla con un número fijo de consultas pasa la prueba.
    def test_aprueba_la_pantalla_buena(self):
        respuesta = self.comprobar_consultas("/buena/", 2, pantallas_de_prueba.mas_filas)
        self.assertContains(respuesta, "3 filas")

    # Una pantalla que hace una consulta por fila suspende al añadir filas, aunque tenga pocas.
    def test_suspende_si_crece_con_las_filas(self):
        with self.assertRaises(AssertionError):
            self.comprobar_consultas("/mala/", 2, pantallas_de_prueba.mas_filas)

    # Un número esperado por encima del presupuesto suspende antes de visitar la pantalla.
    def test_suspende_si_pasa_del_presupuesto(self):
        with self.assertRaisesMessage(AssertionError, "el presupuesto es de 15"):
            self.comprobar_consultas("/cara/", 16, None)

    # Con las direcciones reales de la aplicación, una pantalla real se mide sin problemas («Mis datos →
    # Datos»: 1 consulta, el usuario de la sesión). Antes se medía la portada, pero ahora junta las tarjetas
    # de los módulos y se mide en sus pruebas (proyectos/tests/test_inicio.py).
    @override_settings(ROOT_URLCONF="config.urls")
    def test_pantalla_real(self):
        self.comprobar_consultas("/cuenta/datos/", 1, None)
