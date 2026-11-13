"""
Pruebas de las series de eventos (eventos/series.py): las fechas de cada frecuencia (también al cambiar
la hora en primavera), crear una serie al convocar (con un solo aviso), cambiarla (sin tocar las veces
cambiadas a mano), cambiar cuándo se repite, terminarla, la serie de reuniones con una sola solicitud, la
tarea diaria que añade las siguientes veces y lo que cuestan las pantallas.
"""

from datetime import date, datetime, timedelta

from django.core.cache import cache
from django.test import SimpleTestCase
from django.utils import timezone

from base.pruebas import crear_usuario_de_prueba
from base.tareas import ejecutar_las_de_hoy
from eventos.models import Asistencia, Evento, Serie
from eventos.series import crear_serie, describir, editar_serie, generar_todas, terminar_serie, veces
from eventos.servicios import editar, responder
from eventos_sw.servicios import procesar_bandeja
from solicitudes.models import Solicitud
from solicitudes.servicios import aprobar

from .test_eventos import Notificacion, PruebaDeEventos, datos

# Mañana a las 18:00 de aquí: la primera vez de las series de prueba.
MANANA = timezone.make_aware(datetime.combine(timezone.localdate() + timedelta(days=1), datetime.min.time().replace(hour=18)))


# Una serie de mentira (sin guardar) para calcular fechas.
def serie_de(frecuencia, inicio, hasta=None):
    return Serie(frecuencia=frecuencia, inicio=timezone.make_aware(inicio), hasta=hasta)


# Días (sin hora) de las veces de una serie hasta una fecha.
def dias(serie, hasta):
    return [timezone.localtime(momento).date() for momento in veces(serie, timezone.make_aware(hasta))]


class PruebasDeFechas(SimpleTestCase):
    """Las fechas de cada frecuencia."""

    # Cada semana y cada dos semanas; la hora de aquí se mantiene al pasar al horario de verano.
    def test_semanal(self):
        serie = serie_de(Serie.SEMANAL, datetime(2030, 3, 18, 18, 0))
        momentos = list(veces(serie, timezone.make_aware(datetime(2030, 4, 8, 23, 0))))
        self.assertEqual([timezone.localtime(m).strftime("%d/%m %H:%M") for m in momentos], ["18/03 18:00", "25/03 18:00", "01/04 18:00", "08/04 18:00"])
        self.assertEqual(dias(serie_de(Serie.QUINCENAL, datetime(2030, 3, 18, 18, 0)), datetime(2030, 4, 30)), [date(2030, 3, 18), date(2030, 4, 1), date(2030, 4, 15), date(2030, 4, 29)])
        self.assertEqual(describir(serie), "Cada semana, los lunes a las 18:00")

    # Cada mes el día 31: los meses sin 31 se saltan. Con «hasta», se para.
    def test_mensual_dia(self):
        serie = serie_de(Serie.MENSUAL_DIA, datetime(2030, 1, 31, 10, 0), hasta=date(2030, 6, 1))
        self.assertEqual(dias(serie, datetime(2030, 12, 31)), [date(2030, 1, 31), date(2030, 3, 31), date(2030, 5, 31)])
        self.assertEqual(describir(serie), "Cada mes, el día 31 a las 10:00, hasta el 01/06/2030")

    # El segundo martes y el último viernes de cada mes.
    def test_mensual_semana(self):
        segundo_martes = serie_de(Serie.MENSUAL_SEMANA, datetime(2030, 1, 8, 19, 0))
        self.assertEqual(dias(segundo_martes, datetime(2030, 3, 31)), [date(2030, 1, 8), date(2030, 2, 12), date(2030, 3, 12)])
        self.assertEqual(describir(segundo_martes), "Cada mes, el segundo martes a las 19:00")
        ultimo_viernes = serie_de(Serie.MENSUAL_SEMANA, datetime(2030, 1, 25, 19, 0))
        self.assertEqual(dias(ultimo_viernes, datetime(2030, 3, 31)), [date(2030, 1, 25), date(2030, 2, 22), date(2030, 3, 29)])
        self.assertEqual(describir(ultimo_viernes), "Cada mes, el último viernes a las 19:00")


class PruebasDeSeries(PruebaDeEventos):
    """Crear, cambiar y terminar series."""

    # Una serie semanal de Nutria en GRU Henares que empieza mañana.
    def semanal(self, **otros):
        datos_de_serie = {"titulo": "Taller", "inicio": MANANA, "direccion": "Local", "frecuencia": Serie.SEMANAL, **otros}
        return crear_serie(self.nutria, self.henares, self.generico, datos_de_serie, "grupo:0")

    # Al convocar con «Cada semana» se crea la serie con las veces de los próximos 90 días; a cada persona
    # le llega un solo aviso. La ficha de cada vez lo dice.
    def test_convocar_una_serie(self):
        inicio = timezone.localtime(MANANA).strftime("%Y-%m-%dT%H:%M")
        respuesta = self.client.post(
            f"/eventos/convocar/?grupo={self.henares.pk}&tipologia={self.generico.pk}", datos(titulo="Taller", inicio=inicio, repetir="semanal", repetir_hasta="")
        )
        serie = Serie.objects.get()
        self.assertRedirects(respuesta, f"/eventos/series/{serie.pk}/")
        self.assertEqual(serie.veces.count(), 13)
        procesar_bandeja()
        self.assertEqual(Notificacion.objects.filter(usuario=self.garza, tipo="eventos.convocado").count(), 1)
        primera = serie.veces.order_by("inicio").first()
        self.assertContains(self.client.get(f"/eventos/{primera.pk}/"), "Es una vez de la serie")
        self.assertContains(self.client.get(f"/eventos/series/{serie.pk}/"), "Cada semana")

    # Cambiar el título cambia las próximas veces, salvo la cambiada a mano.
    def test_cambiar_la_serie(self):
        serie = self.semanal()
        segunda = serie.veces.order_by("inicio")[1]
        editar(self.nutria, segunda, {"titulo": "Taller especial"})
        editar_serie(self.nutria, serie, {"titulo": "Taller de pancartas"})
        self.assertEqual(set(serie.veces.values_list("titulo", flat=True)), {"Taller de pancartas", "Taller especial"})
        self.assertEqual(serie.veces.filter(titulo="Taller especial").count(), 1)

    # Pasar a cada dos semanas quita las veces que ya no encajan: la que tenía respuestas se cancela.
    def test_cambiar_cuando_se_repite(self):
        serie = self.semanal()
        segunda = serie.veces.order_by("inicio")[1]
        responder(self.garza, segunda, Asistencia.SI)
        editar_serie(self.nutria, serie, {"frecuencia": Serie.QUINCENAL})
        segunda.refresh_from_db()
        self.assertEqual((segunda.estado, segunda.en_la_serie), (Evento.CANCELADO, None))
        convocadas = serie.veces.filter(estado=Evento.CONVOCADO).order_by("inicio")
        self.assertEqual(convocadas.count(), 7)
        self.assertEqual((convocadas[1].inicio - convocadas[0].inicio).days, 14)

    # Terminar cancela las próximas veces, salvo las cambiadas a mano. Garza (sin permiso) no puede.
    def test_terminar(self):
        serie = self.semanal()
        tocada = serie.veces.order_by("inicio")[2]
        editar(self.nutria, tocada, {"titulo": "Especial"})
        self.como(self.garza)
        self.assertEqual(self.client.post(f"/eventos/series/{serie.pk}/", {"accion": "terminar"}).status_code, 403)
        terminar_serie(self.nutria, serie)
        self.assertEqual(serie.veces.exclude(estado=Evento.CANCELADO).get(), tocada)
        self.assertEqual(generar_todas(), 0)

    # Una serie de reuniones pide una sola solicitud; hasta tenerla no crea veces. Con el sí del
    # superadmin, se activa.
    def test_serie_de_reuniones(self):
        serie = crear_serie(
            self.nutria, self.henares, self.reunion, {"titulo": "Asamblea", "inicio": MANANA, "direccion": "Local", "frecuencia": Serie.MENSUAL_DIA}, "grupo:0"
        )
        self.assertEqual((serie.estado, serie.veces.count()), (Serie.PENDIENTE, 0))
        solicitud = Solicitud.objects.get(tipo="eventos.serie_de_reuniones")
        self.como(self.garza)
        self.assertEqual(self.client.get(f"/eventos/series/{serie.pk}/").status_code, 403)
        aprobar(solicitud, crear_usuario_de_prueba("superadmin", es_superadmin=True))
        serie.refresh_from_db()
        self.assertEqual(serie.estado, Serie.ACTIVA)
        self.assertGreaterEqual(serie.veces.count(), 3)
        self.assertEqual(self.client.get(f"/eventos/series/{serie.pk}/").status_code, 200)

    # La tarea diaria crea las veces nuevas (al pasar los días) y solo se ejecuta una vez al día.
    def test_tarea_diaria(self):
        serie = self.semanal()
        Serie.objects.filter(pk=serie.pk).update(antelacion=120)
        cache.clear()
        resultados = dict(ejecutar_las_de_hoy())
        self.assertEqual(resultados["eventos.generar_series"], 5)
        self.assertIsNone(ejecutar_las_de_hoy())

    # Las pantallas cuestan lo mismo con más series y más veces.
    def test_consultas(self):
        serie = self.semanal()
        self.comprobar_consultas("/eventos/series/", 3, lambda: self.semanal(titulo=f"Taller {Serie.objects.count()}"))
        self.comprobar_consultas(f"/eventos/series/{serie.pk}/", 7, lambda: Serie.objects.filter(pk=serie.pk).update(antelacion=200) and generar_todas())
