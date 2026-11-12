"""
Pruebas de «permisos» en un navegador de verdad (ver base/pruebas_navegador.py): al navegar con htmx a
algo sin permiso, la zona central muestra la explicación (htmx no pinta los errores por defecto; la
403 se pinta por el ajuste «responseHandling» de base/templates/base/cabeza.html).
"""

from django.test import override_settings

from base.pruebas_navegador import PruebaEnElNavegador
from grupos.servicios import admitir, crear_organizacion


@override_settings(ROOT_URLCONF="permisos.tests.urls_de_prueba")
class PruebasDePermisosEnElNavegador(PruebaEnElNavegador):
    """La pantalla «sin permiso» en Chromium."""

    # Navegar con htmx a una pantalla sin permiso deja la explicación en la zona central, con el menú
    # en su sitio y sin errores de JavaScript.
    def test_403_con_htmx(self):
        _tajo, grupo = crear_organizacion("ORG Tajo", "GRU Tajo")
        admitir(self.usuario, grupo)
        self.abrir("/")
        self.pagina.evaluate(
            f"htmx.ajax('GET', '/prueba-permiso/{grupo.pk}/', {{target: '#zona', swap: 'outerHTML'}})"
        )
        self.pagina.wait_for_selector("#zona >> text=No tienes permiso para esto")
        self.assertIn("grupos.editar_grupo", self.pagina.locator("#zona").inner_text())
        self.assertTrue(self.pagina.locator('nav[aria-label="Secciones"]').first.is_visible())
        self.assertEqual(self.errores, [])
