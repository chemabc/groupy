"""
Pruebas en un navegador de verdad (ver base/pruebas_navegador.py) de lo que lleva JavaScript en
«Participación»: la vista previa de un documento, que se pone al día mientras se escribe (htmx), y en una
consulta nueva, la fecha de publicación y el aviso de «tiempo real», que salen según lo elegido (Alpine).
"""

from base.pruebas_navegador import PruebaEnElNavegador
from documentos import servicios
from documentos.models import Documento
from grupos.models import Pertenencia
from grupos.servicios import admitir, crear_organizacion


class PruebasDeParticipacionEnElNavegador(PruebaEnElNavegador):
    """El usuario de la prueba administra GRU Tajo."""

    # Crea la organización y lo hace admin de su grupo.
    def preparar(self):
        _tajo, self.grupo = crear_organizacion("ORG Tajo", "GRU Tajo")
        admitir(self.usuario, self.grupo, rol=Pertenencia.ADMIN_GRUPO)

    # Al escribir, la vista previa de la derecha muestra el texto convertido, sin guardar ni recargar.
    def test_vista_previa(self):
        self.preparar()
        documento = servicios.crear(self.usuario, Documento.LIBRE, "Notas", grupo=self.grupo, visibilidad="grupo:0")
        self.abrir(f"/documentos/{documento.pk}/escribir/")
        cuadro = self.pagina.locator('textarea[name="texto"]')
        cuadro.fill("## Huerto\n\n- **Regar** los martes")
        self.pagina.locator("#vista-previa h2:has-text('Huerto')").wait_for()
        self.assertEqual(self.pagina.locator("#vista-previa strong").inner_text(), "Regar")
        self.assertEqual(self.errores, [])

    # En una consulta nueva, «En una fecha» enseña la fecha de publicación y «En tiempo real», el aviso.
    def test_consulta_nueva(self):
        self.preparar()
        self.abrir("/consultas/nueva/")
        publicar = self.pagina.locator('input[name="publicar_el"]')
        self.assertFalse(publicar.is_visible())
        self.pagina.locator('select[name="resultados"]').select_option("fecha")
        publicar.wait_for(state="visible")
        self.pagina.locator('select[name="resultados"]').select_option("tiempo_real")
        self.pagina.get_by_text("influye en quien aún no ha votado.").last.wait_for(state="visible")
        self.assertEqual(self.errores, [])
