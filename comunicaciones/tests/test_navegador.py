"""
Pruebas de «Comunicaciones → Notificaciones» en un navegador de verdad (ver base/pruebas_navegador.py):
el número del menú baja al marcar como vista sin recargar la página, la papelera borra una y «Limpiar las
vistas» pide confirmación y borra solo las vistas.
"""

from django.core.cache import cache

from base.pruebas_navegador import PruebaEnElNavegador
from comunicaciones.models import Notificacion


class PruebasDeNotificacionesEnElNavegador(PruebaEnElNavegador):
    """Tres notificaciones del usuario de la prueba: dos sin ver y una vista."""

    # Marcar una como vista baja el número del menú (de 2 a 1); la papelera borra otra; «Limpiar las
    # vistas», aceptando la confirmación, deja solo la que sigue sin ver.
    def test_bandeja(self):
        Notificacion.objects.bulk_create(
            [
                Notificacion(usuario=self.usuario, tipo="t", origen="grupos", texto="Primera"),
                Notificacion(usuario=self.usuario, tipo="t", origen="grupos", texto="Segunda"),
                Notificacion(usuario=self.usuario, tipo="t", origen="sistema", texto="Ya vista", vista_el="2026-11-13T10:00:00Z"),
            ]
        )
        # Se han creado a mano (no con repartir): se olvida el número sin ver guardado al entrar.
        cache.clear()
        primera = Notificacion.objects.get(texto="Primera")
        self.abrir("/comunicaciones/")
        contador = self.pagina.locator("#contador-comunicacionesnotificaciones")
        self.assertEqual(contador.inner_text(), "(2)")
        self.pagina.locator(f'li[data-notificacion="{primera.pk}"] button[value="vista"]').click()
        self.pagina.wait_for_function("document.querySelector('#contador-comunicacionesnotificaciones').textContent === '(1)'")
        # La papelera de «Segunda».
        segunda = Notificacion.objects.get(texto="Segunda")
        self.pagina.locator(f'li[data-notificacion="{segunda.pk}"] button[value="borrar"]').click()
        self.pagina.wait_for_selector("text=Segunda", state="detached")
        # «Limpiar las vistas» pregunta antes; se acepta.
        self.pagina.once("dialog", lambda dialogo: dialogo.accept())
        self.pagina.get_by_role("button", name="Limpiar las vistas").click()
        self.pagina.wait_for_selector("text=No tienes notificaciones")
        self.assertFalse(Notificacion.objects.exists())
        self.assertEqual(contador.inner_text(), "(0)")
        self.assertEqual(self.errores, [])
