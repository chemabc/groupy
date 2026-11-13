"""
Pruebas de «calendario»: quién ve cada recordatorio (solo yo, mi grupo, hasta el padre solo para la
administración), las fechas en JSON para la isla, mover arrastrando, la suscripción .ics (sin sesión,
con la clave, y que deja de valer al cambiarla), el formato .ics y lo que cuestan las pantallas.

Estructura: ORG Tajo (GRU Tajo ⊃ GRU Henares ⊃ GRU Sorbe) con Lince admin de GRU Henares, Nutria en GRU
Henares (la sesión), Garza en GRU Sorbe y Zorro en GRU Tajo; Erizo en ORG Ebro.
"""

from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.utils import timezone

from audiencias.servicios import guardar_configuracion
from base.contrato import FechaDeCalendario, FuenteDeCalendario
from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from calendario import ics
from calendario.models import ClaveDeCalendario, Recordatorio
from calendario.servicios import crear_recordatorio, opciones_de_recordatorio
from grupos.models import Pertenencia
from grupos.servicios import admitir, crear_grupo, crear_organizacion

# Un día cualquiera del futuro, a las 18:00 de aquí.
DIA = timezone.make_aware(datetime(2030, 3, 14, 18, 0))


# Datos de un recordatorio para el servicio.
def datos(**otros):
    base = {"titulo": "Llevar las pancartas", "inicio": DIA}
    base.update(otros)
    return base


class PruebaDeCalendario(PruebaDePantalla):
    """Base con la estructura del principio del fichero."""

    # Crea la estructura.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        guardar_configuracion(cls.tajo, 3, True, False)
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.general)
        cls.sorbe = crear_grupo(cls.tajo, "GRU Sorbe", padre=cls.henares)
        cls.ebro, cls.gru_ebro = crear_organizacion("ORG Ebro", "GRU Ebro")
        cls.lince = crear_usuario_de_prueba("Lince")
        cls.nutria = crear_usuario_de_prueba("Nutria")
        cls.garza = crear_usuario_de_prueba("Garza")
        cls.zorro = crear_usuario_de_prueba("Zorro")
        cls.erizo = crear_usuario_de_prueba("Erizo")
        admitir(cls.lince, cls.henares, rol=Pertenencia.ADMIN_GRUPO)
        admitir(cls.nutria, cls.henares)
        admitir(cls.garza, cls.sorbe)
        admitir(cls.zorro, cls.general)
        admitir(cls.erizo, cls.gru_ebro)
        cls.usuario = cls.nutria

    # Inicia sesión como otra persona.
    def como(self, usuario):
        self.client.force_login(usuario)

    # Pide las fechas de marzo de 2030 en JSON y devuelve la lista.
    def fechas(self):
        respuesta = self.client.get("/calendario/datos/?start=2030-03-01T00:00:00%2B01:00&end=2030-04-01T00:00:00%2B02:00")
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.json()["fechas"]

    # Títulos de las fechas de marzo de 2030 que ve la sesión.
    def titulos(self):
        return {fecha["title"] for fecha in self.fechas()}


class PruebasDeRecordatorios(PruebaDeCalendario):
    """Quién ve cada recordatorio y quién puede abrirlo más arriba."""

    # «Solo yo» lo ve solo quien lo apunta (ni el superadmin); «Mi grupo», también GRU Sorbe, no GRU Tajo.
    def test_quien_lo_ve(self):
        crear_recordatorio(self.nutria, self.henares, datos(titulo="Mío"), "privado")
        crear_recordatorio(self.nutria, self.henares, datos(titulo="Del grupo"), "grupo:0")
        self.assertEqual(self.titulos(), {"Mío", "Del grupo"})
        self.como(self.garza)
        self.assertEqual(self.titulos(), {"Del grupo"})
        self.como(self.zorro)
        self.assertEqual(self.titulos(), set())
        self.como(crear_usuario_de_prueba("superadmin", es_superadmin=True))
        self.assertEqual(self.titulos(), {"Del grupo"})

    # Nutria no puede abrirlo al padre; Lince (admin de GRU Henares) sí, y entonces lo ve Zorro.
    def test_hasta_el_padre(self):
        self.assertEqual([clave for clave, _ in opciones_de_recordatorio(self.nutria, self.henares)], ["privado", "grupo:0"])
        self.assertEqual([clave for clave, _ in opciones_de_recordatorio(self.lince, self.henares)], ["privado", "grupo:0", "grupo:1"])
        with self.assertRaises(ValidationError):
            crear_recordatorio(self.nutria, self.henares, datos(), "grupo:1")
        crear_recordatorio(self.lince, self.henares, datos(titulo="Para todo Tajo"), "grupo:1")
        self.como(self.zorro)
        self.assertEqual(self.titulos(), {"Para todo Tajo"})

    # Solo se apuntan en los grupos propios.
    def test_solo_en_mis_grupos(self):
        with self.assertRaises(ValidationError):
            crear_recordatorio(self.nutria, self.gru_ebro, datos(), "grupo:0")

    # Desde la pantalla: apuntar uno de día entero (las horas se quitan), verlo en la ficha, cambiarlo y
    # borrarlo. Otra persona del grupo lo ve pero no lo cambia.
    def test_pantallas(self):
        respuesta = self.client.post(
            "/calendario/recordatorios/nuevo/",
            {"grupo": self.henares.pk, "titulo": "Cierra el local", "notas": "", "todo_el_dia": "on", "inicio": "2030-03-14T10:30", "fin": "2030-03-16T00:00", "visibilidad": "grupo:0"},
        )
        recordatorio = Recordatorio.objects.get()
        self.assertRedirects(respuesta, f"/calendario/recordatorios/{recordatorio.pk}/")
        self.assertEqual(timezone.localtime(recordatorio.inicio).hour, 0)
        fecha = next(f for f in self.fechas() if f["title"] == "Cierra el local")
        self.assertEqual((fecha["start"], fecha["end"], fecha["allDay"], fecha["editable"]), ("2030-03-14", "2030-03-17", True, True))
        self.assertContains(self.client.get("/calendario/recordatorios/"), "Cierra el local")
        self.como(self.garza)
        self.assertNotContains(self.client.get(f"/calendario/recordatorios/{recordatorio.pk}/"), "Borrar el recordatorio")
        self.assertEqual(self.client.post(f"/calendario/recordatorios/{recordatorio.pk}/", {"accion": "borrar"}).status_code, 403)
        self.como(self.erizo)
        self.assertEqual(self.client.get(f"/calendario/recordatorios/{recordatorio.pk}/").status_code, 403)
        self.como(self.nutria)
        cambio = {"accion": "guardar", "titulo": "Cierra el local (seguro)", "notas": "", "inicio": "2030-03-14T00:00", "fin": "", "visibilidad": "privado"}
        self.client.post(f"/calendario/recordatorios/{recordatorio.pk}/", cambio)
        recordatorio.refresh_from_db()
        self.assertEqual((recordatorio.titulo, recordatorio.visibilidad, recordatorio.audiencia.personal), ("Cierra el local (seguro)", "privado", True))
        self.assertRedirects(self.client.post(f"/calendario/recordatorios/{recordatorio.pk}/", {"accion": "borrar"}), "/calendario/recordatorios/")
        self.assertFalse(Recordatorio.objects.exists())

    # Al pulsar un hueco del calendario, el formulario llega con el día puesto y «todo el día» marcado.
    def test_nuevo_con_fecha(self):
        respuesta = self.client.get("/calendario/recordatorios/nuevo/?inicio=2030-03-14")
        self.assertContains(respuesta, 'value="2030-03-14T00:00"')
        self.assertContains(respuesta, 'id="id_todo_el_dia" checked')


class PruebasDeMover(PruebaDeCalendario):
    """Arrastrar en el calendario."""

    # Quien lo apuntó lo mueve (y se guarda); otra persona del grupo no; una fuente desconocida, tampoco.
    def test_mover(self):
        recordatorio = crear_recordatorio(self.nutria, self.henares, datos(), "grupo:0")
        mover = {"fuente": "calendario.recordatorios", "id": recordatorio.pk, "todo_el_dia": "0", "inicio": "2030-03-15T19:00:00+01:00", "fin": "2030-03-15T20:00:00+01:00"}
        self.assertEqual(self.client.post("/calendario/mover/", mover).json(), {"ok": True})
        recordatorio.refresh_from_db()
        self.assertEqual((timezone.localtime(recordatorio.inicio).day, timezone.localtime(recordatorio.fin).hour), (15, 20))
        self.como(self.garza)
        respuesta = self.client.post("/calendario/mover/", mover)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("Solo quien lo apuntó", respuesta.json()["error"])
        self.assertEqual(self.client.post("/calendario/mover/", {**mover, "fuente": "nada"}).status_code, 400)

    # Al mover uno de día entero, FullCalendar da como final el día siguiente al último: se guarda el último.
    def test_mover_dias_enteros(self):
        recordatorio = crear_recordatorio(self.nutria, self.henares, datos(todo_el_dia=True, inicio=DIA.replace(hour=0)), "privado")
        mover = {"fuente": "calendario.recordatorios", "id": recordatorio.pk, "todo_el_dia": "1", "inicio": "2030-03-20", "fin": "2030-03-22"}
        self.client.post("/calendario/mover/", mover)
        recordatorio.refresh_from_db()
        self.assertEqual((timezone.localtime(recordatorio.inicio).day, timezone.localtime(recordatorio.fin).day), (20, 21))
        self.client.post("/calendario/mover/", {**mover, "fin": "2030-03-21"})
        recordatorio.refresh_from_db()
        self.assertIsNone(recordatorio.fin)


class PruebasDeSuscripcion(PruebaDeCalendario):
    """La suscripción .ics."""

    # Con la clave se descarga sin sesión; trae los recordatorios que ve esa persona; al cambiar la clave,
    # la anterior da 404.
    def test_ics(self):
        crear_recordatorio(self.nutria, self.henares, datos(titulo="Asamblea, en el local"), "grupo:0")
        Recordatorio.objects.update(inicio=timezone.now() + timedelta(days=3))
        self.assertContains(self.client.get("/calendario/suscripcion/"), "/calendario/ics/")
        clave = ClaveDeCalendario.objects.get(usuario=self.nutria).clave
        self.client.logout()
        respuesta = self.client.get(f"/calendario/ics/{clave}.ics")
        self.assertEqual(respuesta["Content-Type"], "text/calendar; charset=utf-8")
        self.assertContains(respuesta, "SUMMARY:Asamblea\\, en el local")
        self.assertContains(respuesta, "CATEGORIES:Recordatorios")
        self.client.force_login(self.nutria)
        self.client.post("/calendario/suscripcion/", {"accion": "cambiar"})
        self.client.logout()
        self.assertEqual(self.client.get(f"/calendario/ics/{clave}.ics").status_code, 404)
        nueva = ClaveDeCalendario.objects.get(usuario=self.nutria).clave
        self.assertNotEqual(nueva, clave)
        self.assertEqual(self.client.get(f"/calendario/ics/{nueva}.ics").status_code, 200)


class PruebasDelFormatoIcs(SimpleTestCase):
    """El texto .ics: escapar, partir líneas largas y los días enteros."""

    # Las comas, los puntos y coma y los saltos de línea se escapan; ninguna línea pasa de 75 bytes; lo de
    # día entero termina el día siguiente al último.
    def test_formato(self):
        fuente = FuenteDeCalendario("calendario.prueba", "Prueba", "x.y")
        largo = "Asamblea ñ " * 20
        fechas = [
            (fuente, FechaDeCalendario(1, "Uno; dos,\ntres", DIA)),
            (fuente, FechaDeCalendario(2, largo, DIA.replace(hour=0), DIA.replace(hour=0) + timedelta(days=1), todo_el_dia=True)),
        ]
        texto = ics.escribir(fechas, "Asambleas", "ejemplo.org")
        self.assertIn("SUMMARY:Uno\\; dos\\,\\ntres", texto)
        self.assertIn("DTSTART;VALUE=DATE:20300314\r\nDTEND;VALUE=DATE:20300316", texto)
        self.assertTrue(all(len(linea.encode()) <= 75 for linea in texto.split("\r\n")))
        desplegado = texto.replace("\r\n ", "")
        self.assertIn(f"SUMMARY:{largo}", desplegado)


class PruebasDeConsultas(PruebaDeCalendario):
    """Cada pantalla cuesta lo mismo con pocas filas que con muchas."""

    # Añade un recordatorio de Nutria en GRU Henares (en marzo de 2030, o mañana con «pronto»).
    def mas(self, pronto=False):
        inicio = timezone.now() + timedelta(days=1) if pronto else DIA
        crear_recordatorio(self.nutria, self.henares, datos(inicio=inicio), "grupo:0")

    # Lo mismo, mañana.
    def mas_pronto(self):
        self.mas(pronto=True)

    # El calendario (la página) y sus fechas en JSON.
    def test_calendario(self):
        self.comprobar_consultas("/calendario/", 1, None)
        self.mas()
        self.comprobar_consultas("/calendario/datos/?start=2030-03-01&end=2030-04-01", 4, self.mas)

    # Lista de recordatorios, apuntar uno y la ficha.
    def test_recordatorios(self):
        self.mas_pronto()
        self.comprobar_consultas("/calendario/recordatorios/", 2, self.mas_pronto)
        self.comprobar_consultas("/calendario/recordatorios/nuevo/", 2, None)
        self.comprobar_consultas(f"/calendario/recordatorios/{Recordatorio.objects.first().pk}/", 2, None)

    # Suscripción y el .ics.
    def test_suscripcion(self):
        self.comprobar_consultas("/calendario/suscripcion/", 2, None)
        clave = ClaveDeCalendario.objects.get().clave
        self.mas_pronto()
        self.comprobar_consultas(f"/calendario/ics/{clave}.ics", 4, self.mas_pronto)
