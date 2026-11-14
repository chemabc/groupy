"""
Pruebas del selector de etiquetas en un navegador de verdad (ver base/pruebas_navegador.py), en el
formulario de demostración de «Desarrollo y mantenimiento → Componentes → Componentes».
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


class PruebasDeLaPantallaDeEtiquetasEnElNavegador(PruebaEnElNavegador):
    """«Administrar → Mi organización → Etiquetas» como admin de ORG Tajo, con otra organización (ORG Ebro) que también administra."""

    # Cambiar el desplegable «De» lleva a la otra organización sin pulsar nada (se envía solo, con htmx);
    # marcar dos etiquetas en la tabla y pulsar «Fusionar las marcadas» (un formulario aparte, al que
    # pertenecen las casillas por su atributo «form») las fusiona.
    def test_cambiar_de_organizacion_y_fusionar(self):
        from etiquetas.servicios import crear_etiqueta
        from grupos.servicios import admitir, crear_organizacion, nombrar_admin_de_organizacion

        tajo, general = crear_organizacion("ORG Tajo", "GRU Tajo")
        ebro, gru_ebro = crear_organizacion("ORG Ebro", "GRU Ebro")
        for organizacion, grupo in ((tajo, general), (ebro, gru_ebro)):
            admitir(self.usuario, grupo)
            nombrar_admin_de_organizacion(self.usuario, organizacion)
        huelga = crear_etiqueta("Huelga", tajo)
        crear_etiqueta("Huelgas", tajo)
        crear_etiqueta("Riego", ebro)

        self.abrir(f"/etiquetas/?de={tajo.pk}")
        self.pagina.locator('select[name="de"]').select_option(str(ebro.pk))
        self.pagina.wait_for_selector("td:has-text('Riego')")
        self.pagina.locator('select[name="de"]').select_option(str(tajo.pk))
        self.pagina.wait_for_selector("td:has-text('Huelgas')")
        self.pagina.get_by_label("Marcar «Huelga» para fusionar").check()
        self.pagina.get_by_label("Marcar «Huelgas» para fusionar").check()
        self.pagina.locator('select[name="destino"]').select_option(str(huelga.pk))
        self.pagina.get_by_role("button", name="Fusionar las marcadas").click()
        # «Huelgas» desaparece como etiqueta (queda como palabra relacionada de «Huelga»).
        self.pagina.wait_for_selector("td.font-medium:text-is('Huelgas')", state="detached")
        self.assertEqual(list(Etiqueta.objects.filter(organizacion=tajo).values_list("nombre", "relacionadas")), [("Huelga", "Huelgas")])
        self.assertEqual(self.errores, [])
