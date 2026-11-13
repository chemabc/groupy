"""
Pruebas del selector de etiquetas en un navegador de verdad (ver base/pruebas_navegador.py), en el
formulario de demostración de «Inicio → Componentes».
"""

from base.pruebas_navegador import PruebaEnElNavegador
from etiquetas.models import Etiqueta


class PruebasDelSelectorEnElNavegador(PruebaEnElNavegador):
    """Sugerencias, añadir y quitar palabras."""

    # Escribir «par» sugiere «huelga» (por su relacionada «paro»); elegirla y escribir otra con Intro
    # las añade como pastillas; la × quita una. Lo que se enviaría son campos ocultos con cada palabra.
    def test_selector(self):
        Etiqueta.objects.create(nombre="huelga", relacionadas="paro")
        self.abrir("/componentes/")
        cuadro = self.pagina.locator("#id_etiquetas")
        cuadro.fill("par")
        self.pagina.get_by_role("option", name="huelga").click()
        cuadro.fill("local nuevo")
        cuadro.press("Enter")
        valores = self.pagina.locator('input[type="hidden"][name="etiquetas"]')
        self.assertEqual([valores.nth(i).input_value() for i in range(valores.count())], ["acogida", "huelga", "local nuevo"])
        self.pagina.get_by_role("button", name="Quitar acogida").click()
        self.assertEqual(valores.count(), 2)
        # Repetir una que ya está (con otras mayúsculas) no la duplica.
        cuadro.fill("HUELGA")
        cuadro.press("Enter")
        self.assertEqual(valores.count(), 2)
        self.assertEqual(self.errores, [])
