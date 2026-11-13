"""
Pruebas de la sección «Usuarios» en un navegador de verdad (ver base/pruebas_navegador.py): dar de alta a
una persona en la bóveda, abrir su ficha desde la lista y validarla, todo con la navegación de htmx.
"""

from django.contrib.auth import get_user_model

from base.pruebas_navegador import PruebaEnElNavegador
from boveda.models import Persona
from grupos.servicios import crear_organizacion


class PruebasDeUsuariosEnElNavegador(PruebaEnElNavegador):
    """La bóveda en Chromium, como superadmin."""

    databases = {"default", "boveda"}

    # El usuario de la prueba pasa a ser superadmin y existe una organización.
    def setUp(self):
        super().setUp()
        get_user_model().objects.filter(pk=self.usuario.pk).update(es_superadmin=True)
        crear_organizacion("ORG Tajo", "GRU Tajo")

    # Alta → ficha (con el nombre) → lista (sin el nombre, con enlace) → validar.
    def test_alta_y_validacion(self):
        self.abrir("/usuarios/boveda/personas/")
        self.pagina.get_by_text("Dar de alta a una persona").click()
        self.pagina.fill('input[name="nombre"]', "Ana Pérez")
        self.pagina.fill('input[name="correo_oficial"]', "ana@educa.org")
        self.pagina.select_option('select[name="organizacion"]', label="ORG Tajo")
        self.pagina.get_by_role("button", name="Dar de alta").click()
        self.pagina.wait_for_selector("text=Validar (alta por el superadmin)")
        self.assertEqual(self.pagina.locator('input[name="nombre"]').input_value(), "Ana Pérez")
        self.pagina.get_by_role("link", name="← Personas").click()
        persona = Persona.objects.get()
        self.pagina.wait_for_selector(f"text={persona}")
        self.assertNotIn("Ana Pérez", self.pagina.locator("#zona").inner_text())
        self.pagina.get_by_role("link", name=str(persona)).click()
        self.pagina.get_by_role("button", name="Validar (alta por el superadmin)").click()
        self.pagina.wait_for_selector("text=Su correo se ha borrado")
        persona.refresh_from_db()
        self.assertEqual((persona.estado, persona.correo_oficial), (Persona.VALIDADA, ""))
        self.assertEqual(self.errores, [])
