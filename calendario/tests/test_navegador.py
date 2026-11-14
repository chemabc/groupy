"""
Prueba del calendario en un navegador de verdad (ver base/pruebas_navegador.py): la isla «calendario»
carga FullCalendar sola (también al llegar navegando con htmx por el menú), pinta las fechas del mes,
oculta un tipo con su casilla y guarda lo que se arrastra a otro día.
"""

from datetime import datetime

from django.utils import timezone

from base.pruebas_navegador import PruebaEnElNavegador
from calendario.models import Recordatorio
from calendario.servicios import crear_recordatorio
from grupos.servicios import admitir, crear_organizacion


class PruebasDelCalendarioEnElNavegador(PruebaEnElNavegador):
    """Un recordatorio del usuario de la prueba el día 10 de este mes."""

    # Desde «Recordatorios», entra en «Ver el calendario» con el menú (htmx), ve el recordatorio, lo
    # oculta y lo vuelve a mostrar con su casilla, y lo arrastra al día 12: se guarda en la base de datos.
    def test_calendario(self):
        _tajo, grupo = crear_organizacion("ORG Tajo", "GRU Tajo")
        admitir(self.usuario, grupo)
        hoy = timezone.localdate()
        dia = timezone.make_aware(datetime(hoy.year, hoy.month, 10))
        recordatorio = crear_recordatorio(self.usuario, grupo, {"titulo": "Pancartas", "inicio": dia, "todo_el_dia": True}, "grupo:0")

        self.abrir("/calendario/recordatorios/")
        self.pagina.locator('nav[aria-label="Secciones"] a[data-codigo="calendario.calendario"]').first.click()
        evento = self.pagina.locator(".fc-event", has_text="Pancartas")
        evento.wait_for()
        casilla = self.pagina.locator("label", has_text="Recordatorios").locator("input")
        casilla.uncheck()
        self.pagina.wait_for_selector(".fc-event", state="detached")
        casilla.check()
        evento.wait_for()

        destino = self.pagina.locator(f'td.fc-daygrid-day[data-date="{hoy.year}-{hoy.month:02d}-12"]')
        with self.pagina.expect_response(lambda respuesta: "/calendario/mover/" in respuesta.url) as respuesta:
            evento.drag_to(destino)
        self.assertEqual(respuesta.value.json(), {"ok": True})
        recordatorio.refresh_from_db()
        self.assertEqual(timezone.localtime(recordatorio.inicio).day, 12)
        self.assertEqual(Recordatorio.objects.count(), 1)
        self.assertEqual(self.errores, [])
