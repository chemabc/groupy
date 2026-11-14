"""
Prueba del mapa de lugares en un navegador de verdad (ver base/pruebas_navegador.py): la isla «mapa»
carga Leaflet sola, también al llegar navegando con htmx, y agrupa las chinchetas cercanas. Las teselas
del mapa vienen de OpenStreetMap: sin conexión no se ven, pero las chinchetas sí.
"""

from base.pruebas_navegador import PruebaEnElNavegador
from grupos.servicios import admitir, crear_organizacion
from lugares.models import Lugar


class PruebasDelMapaEnElNavegador(PruebaEnElNavegador):
    """Tres lugares: dos juntos en Alcalá (se agrupan) y uno en Zaragoza."""

    # Al entrar en «Mapa» con el menú (htmx), sale el mapa con un grupo de 2 y una chincheta suelta; al
    # pulsar la suelta, su ventanita muestra el nombre con enlace a la ficha.
    def test_mapa(self):
        _tajo, grupo = crear_organizacion("ORG Tajo", "GRU Tajo")
        admitir(self.usuario, grupo)
        for nombre, url in (
            ("IES Uno", "https://www.openstreetmap.org/#map=18/40.4820/-3.3640"),
            ("IES Dos", "https://www.openstreetmap.org/#map=18/40.4821/-3.3641"),
            ("IES Ebro", "https://www.openstreetmap.org/#map=18/41.6600/-0.8700"),
        ):
            Lugar(nombre=nombre, direccion="C/ X", url_localizacion=url).save()
        self.abrir("/organizaciones/")
        self.pagina.locator('nav[aria-label="Secciones"] a[data-codigo="lugares.mapa"]').first.click()
        self.pagina.wait_for_selector(".marker-cluster")
        self.assertEqual(self.pagina.locator(".marker-cluster").inner_text(), "2")
        self.pagina.locator('.leaflet-marker-icon[title="IES Ebro"]').click()
        enlace = self.pagina.locator(".leaflet-popup-content a")
        self.assertEqual(enlace.inner_text(), "IES Ebro")
        self.assertIn("/lugares/lugar/", enlace.get_attribute("href"))
        self.assertEqual(self.errores, [])
