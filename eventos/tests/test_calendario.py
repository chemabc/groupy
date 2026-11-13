"""
Pruebas de lo que «eventos» aporta al calendario común (eventos/calendario.py): qué eventos salen y
con qué color y tipo, la reunión pendiente solo para quien la convoca, los cancelados, arrastrar (solo
quien lo gestiona) y lo que cuesta pedir las fechas. Se usan las direcciones del calendario, sin importar
el módulo «calendario» (los módulos funcionales no se importan entre sí).
"""

from django.utils import timezone

from eventos.models import Evento
from eventos.servicios import cancelar, convocar
from tipologias.servicios import crear_tipologia

from .test_eventos import PruebaDeEventos, datos_del_servicio

# Las fechas de diciembre de 2030 (el mes de las charlas de prueba), para la isla del calendario.
DICIEMBRE = "/calendario/datos/?start=2030-12-01T00:00:00%2B01:00&end=2031-01-01T00:00:00%2B01:00"


class PruebasDelCalendario(PruebaDeEventos):
    """Los eventos en el calendario."""

    # Fechas de diciembre de 2030 que ve la sesión, por título.
    def fechas(self):
        return {fecha["title"]: fecha for fecha in self.client.get(DICIEMBRE).json()["fechas"]}

    # La charla sale con el color y el nombre de «Genérico»; Nutria (quien la convoca) puede arrastrarla y
    # Garza (de un subgrupo) la ve pero no. La reunión pendiente solo la ve Nutria. Erizo, nada.
    def test_que_sale(self):
        self.charla()
        convocar(self.nutria, self.henares, self.reunion, datos_del_servicio(titulo="Asamblea"), "grupo:0")
        fechas = self.fechas()
        self.assertEqual(set(fechas), {"Charla", "Pendiente de apoyos: Asamblea"})
        charla = fechas["Charla"]
        self.assertEqual((charla["categoria"], charla["color"], charla["editable"], charla["fuente"]), ("Genérico", "#0284c7", True, "eventos.eventos"))
        self.assertEqual(charla["start"], "2030-12-01T18:00:00+01:00")
        self.assertEqual(charla["end"], "2030-12-01T19:30:00+01:00")
        self.assertEqual(fechas["Pendiente de apoyos: Asamblea"]["categoria"], "Reunión")
        self.como(self.garza)
        self.assertEqual(self.fechas()["Charla"]["editable"], False)
        self.assertNotIn("Pendiente de apoyos: Asamblea", self.fechas())
        self.como(self.erizo)
        self.assertEqual(self.fechas(), {})

    # Un subtipo de una organización toma el color de su tipo principal; un cancelado sale en gris.
    def test_subtipo_y_cancelado(self):
        asamblea_de_barrio = crear_tipologia("evento", "Asamblea de barrio", padre=self.generico, organizacion=self.tajo)
        convocar(self.nutria, self.henares, asamblea_de_barrio, datos_del_servicio(titulo="Barrio"), "grupo:0")
        cancelar(self.nutria, self.charla(titulo="Suspendida"))
        fechas = self.fechas()
        self.assertEqual((fechas["Barrio"]["categoria"], fechas["Barrio"]["color"]), ("Genérico", "#0284c7"))
        self.assertEqual((fechas["Cancelado: Suspendida"]["color"], fechas["Cancelado: Suspendida"]["editable"]), ("#94a3b8", False))

    # Arrastrar: Nutria la pasa al día 3 y la alarga; Garza no puede; un cancelado no se mueve.
    def test_mover(self):
        evento = self.charla()
        mover = {"fuente": "eventos.eventos", "id": evento.pk, "todo_el_dia": "0", "inicio": "2030-12-03T19:00:00+01:00", "fin": "2030-12-03T21:00:00+01:00"}
        self.assertEqual(self.client.post("/calendario/mover/", mover).json(), {"ok": True})
        evento.refresh_from_db()
        self.assertEqual((timezone.localtime(evento.inicio).day, evento.duracion), (3, 120))
        self.como(self.garza)
        self.assertEqual(self.client.post("/calendario/mover/", mover).status_code, 400)
        self.como(self.nutria)
        cancelar(self.nutria, evento)
        self.assertIn("cancelado", self.client.post("/calendario/mover/", mover).json()["error"])
        self.assertEqual(Evento.objects.get().estado, Evento.CANCELADO)

    # Pedir las fechas cuesta lo mismo con más eventos.
    def test_consultas(self):
        self.charla()
        self.comprobar_consultas(DICIEMBRE, 4, lambda: self.charla(titulo=f"Charla {Evento.objects.count()}"))
