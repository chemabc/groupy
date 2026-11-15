"""
Pruebas de las piezas comunes que usan documentos, debates y consultas: el Markdown seguro
(base/markdown.py), las anclas (base/anclas.py) y la etiqueta {% colgantes %} (base/templatetags), con un
módulo de mentira.
"""

from django.template import Context, Template
from django.test import RequestFactory, TestCase

from base.anclas import leer_ancla
from base.contrato import Colgante, FilaDeResumen
from base.markdown import texto_a_html
from base.pruebas import contratos_de_prueba, crear_usuario_de_prueba, modulo_falso


# Función de mentira del colgante: una fila con el ancla recibida.
def filas_de_mentira(usuario, ancla_tipo, ancla_id):
    return [FilaDeResumen(f"Cuelga de {ancla_tipo} {ancla_id}", "/alfa/1/")]


ALFA = modulo_falso(
    "alfa",
    colgantes=(Colgante("alfa.cosas", "Cosas", ("eventos.evento",), "base.tests.test_colgantes.filas_de_mentira", texto_crear="+ Cosa"),),
)


class PruebasDePiezasComunes(TestCase):
    """Markdown seguro, anclas y colgantes."""

    # El Markdown no deja pasar HTML ni enlaces que ejecuten código, aunque vengan disimulados.
    def test_markdown_seguro(self):
        html = texto_a_html("**hola** <script>x</script> [a](javascript:alert(1)) [b](&#106;avascript:x) [c](https://ejemplo.org)")
        self.assertIn("<strong>hola</strong>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("javascript", html.lower().replace("&#106;", ""))
        self.assertEqual(html.count('href="#"'), 2)
        self.assertIn('href="https://ejemplo.org"', html)

    # «tipo:número» de un ancla declarada; lo demás, nada.
    def test_leer_ancla(self):
        self.assertEqual(leer_ancla("eventos.evento:12"), ("eventos.evento", 12))
        self.assertEqual(leer_ancla("inventado.cosa:1"), (None, None))
        self.assertEqual(leer_ancla("eventos.evento:x"), (None, None))

    # La etiqueta pinta los colgantes que aceptan ese tipo de ancla, y nada si no hay ninguno.
    def test_etiqueta(self):
        peticion = RequestFactory().get("/")
        peticion.user = crear_usuario_de_prueba("Nutria")
        plantilla = Template('{% load colgantes %}{% colgantes tipo 7 %}')
        with contratos_de_prueba(ALFA):
            html = plantilla.render(Context({"request": peticion, "tipo": "eventos.evento"}))
            self.assertIn("Cuelga de eventos.evento 7", html)
            self.assertIn("Cosas", html)
            self.assertNotIn("Cuelga de", plantilla.render(Context({"request": peticion, "tipo": "lugares.lugar"})).replace("Cuelga de aquí", ""))
