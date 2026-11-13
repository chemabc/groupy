"""
Pruebas del selector de etiquetas en un navegador de verdad (ver base/pruebas_navegador.py), en el
formulario de demostración de «Inicio → Componentes».
"""

from base.pruebas_navegador import PruebaEnElNavegador
from etiquetas.models import Etiqueta


class PruebasDelSelectorEnElNavegador(PruebaEnElNavegador):
    """Sugerencias, añadir y quitar palabras."""

    # Escribir «par» sugiere «Huelga» (por su relacionada «paro»); elegirla y escribir otra con Intro
    # las añade como pastillas; la × quita una. Lo que se enviaría son campos ocultos con cada palabra.
    def test_selector(self):
        Etiqueta.objects.create(nombre="huelga", relacionadas="paro")
        self.abrir("/componentes/")
        cuadro = self.pagina.locator("#id_etiquetas")
        cuadro.fill("par")
        self.pagina.get_by_role("option", name="Huelga").click()
        cuadro.fill("local nuevo")
        cuadro.press("Enter")
        valores = self.pagina.locator('input[type="hidden"][name="etiquetas"]')
        self.assertEqual([valores.nth(i).input_value() for i in range(valores.count())], ["Acogida", "Huelga", "Local nuevo"])
        self.pagina.get_by_role("button", name="Quitar Acogida").click()
        self.assertEqual(valores.count(), 2)
        # Repetir una que ya está (con otras mayúsculas) no la duplica.
        cuadro.fill("HUELGA")
        cuadro.press("Enter")
        self.assertEqual(valores.count(), 2)
        # Lo escrito se pasa a la forma de las etiquetas al añadirlo: sin tildes y solo la primera en mayúscula.
        cuadro.fill("REUNIÓN de AÑO")
        cuadro.press("Enter")
        self.assertEqual(valores.nth(2).input_value(), "Reunion de año")
        self.assertEqual(self.errores, [])
