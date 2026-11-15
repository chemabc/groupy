"""
Pruebas de «eventos»: convocar (y la reunión con su solicitud de apoyos), quién ve el evento y quién ve
quién va, «¿Vas a ir?», cometidos, cancelar con aviso, el cartel (solo para quien ve el evento), editar
y lo que cuestan las pantallas.

Estructura: ORG Tajo (GRU Tajo ⊃ GRU Henares ⊃ GRU Sorbe) con Lince admin de GRU Henares, Nutria en GRU
Henares (la sesión) y Garza en GRU Sorbe; Erizo en ORG Ebro. Tipologías comunes: Reunión y Genérico.
"""

import io
import shutil
import tempfile

from django.apps import apps
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from eventos.models import Asistencia, Evento
from eventos.servicios import apuntar, convocar, responder
from eventos_sw.servicios import procesar_bandeja
from grupos.models import Pertenencia
from grupos.servicios import admitir, crear_grupo, crear_organizacion
from solicitudes.models import Solicitud
from solicitudes.servicios import aprobar, responder as apoyar
from tipologias.servicios import crear_tipologia

# Tabla de notificaciones de «comunicaciones» (otro módulo funcional: se busca por su nombre).
Notificacion = apps.get_model("comunicaciones", "Notificacion")
# Carpeta temporal para los carteles de las pruebas (se borra al terminar).
CARPETA = tempfile.mkdtemp()


# Datos de un evento para el formulario.
def datos(**otros):
    base = {
        "titulo": "Charla", "descripcion": "", "inicio": "2030-12-01T18:00", "duracion": 90, "modalidad": "presencial",
        "direccion": "Plaza Mayor", "url": "", "coste": "gratis", "coste_detalle": "", "texto_para_redes": "Ven", "visibilidad": "grupo:0",
    }
    base.update(otros)
    return base


# Datos de un evento para el servicio convocar().
def datos_del_servicio(**otros):
    base = {"titulo": "Charla", "inicio": "2030-12-01T18:00+01:00", "direccion": "Plaza"}
    base.update(otros)
    return base


@override_settings(MEDIA_ROOT=CARPETA)
class PruebaDeEventos(PruebaDePantalla):
    """Base con la estructura del principio del fichero."""

    # Crea la estructura y las tipologías.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.general)
        cls.sorbe = crear_grupo(cls.tajo, "GRU Sorbe", padre=cls.henares)
        cls.ebro, cls.gru_ebro = crear_organizacion("ORG Ebro", "GRU Ebro")
        cls.lince = crear_usuario_de_prueba("Lince")
        cls.nutria = crear_usuario_de_prueba("Nutria")
        cls.garza = crear_usuario_de_prueba("Garza")
        cls.erizo = crear_usuario_de_prueba("Erizo")
        admitir(cls.lince, cls.henares, rol=Pertenencia.ADMIN_GRUPO)
        admitir(cls.nutria, cls.henares)
        admitir(cls.garza, cls.sorbe)
        admitir(cls.erizo, cls.gru_ebro)
        cls.reunion = crear_tipologia("evento", "Reunión")
        cls.generico = crear_tipologia("evento", "Genérico")
        cls.usuario = cls.nutria

    # Borra la carpeta de los carteles al terminar.
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(CARPETA, ignore_errors=True)

    # Inicia sesión como otra persona.
    def como(self, usuario):
        cache.clear()
        self.client.force_login(usuario)

    # Un evento genérico convocado por Nutria para GRU Henares (lo ven también los de GRU Sorbe).
    def charla(self, **otros):
        return convocar(self.nutria, self.henares, self.generico, datos_del_servicio(**otros), "grupo:0")


class PruebasDeConvocar(PruebaDeEventos):
    """Convocar eventos y reuniones."""

    # Un evento genérico desde la pantalla: lo ven los del grupo (y subgrupos), no los de otra organización,
    # y se les avisa.
    def test_generico(self):
        respuesta = self.client.post(f"/eventos/convocar/?grupo={self.henares.pk}&tipologia={self.generico.pk}", datos())
        evento = Evento.objects.get()
        self.assertRedirects(respuesta, f"/eventos/{evento.pk}/")
        self.assertEqual(evento.estado, Evento.CONVOCADO)
        self.como(self.garza)
        self.assertContains(self.client.get("/eventos/"), "Charla")
        self.como(self.erizo)
        self.assertEqual(self.client.get(f"/eventos/{evento.pk}/").status_code, 403)
        procesar_bandeja()
        self.assertEqual(set(Notificacion.objects.filter(tipo="eventos.convocado").values_list("usuario__alias", flat=True)), {"Lince", "Garza"})

    # Presencial sin dónde, o en línea sin enlace, no se puede.
    def test_donde(self):
        url = f"/eventos/convocar/?grupo={self.henares.pk}&tipologia={self.generico.pk}"
        self.assertContains(self.client.post(url, datos(direccion="")), "Di dónde es")
        self.assertContains(self.client.post(url, datos(modalidad="en_linea", direccion="")), "Pon el enlace")

    # Una reunión queda pendiente (solo la ve quien la convoca) con una solicitud de 2 apoyos en su grupo;
    # para el grupo padre, 5. Con los apoyos se convoca y la ve el grupo.
    def test_reunion_con_apoyos(self):
        url = f"/eventos/convocar/?grupo={self.henares.pk}&tipologia={self.reunion.pk}"
        self.client.post(url, datos(titulo="Asamblea", justificacion="Toca"))
        evento = Evento.objects.get()
        solicitud = Solicitud.objects.get(tipo="eventos.reunion")
        self.assertEqual((evento.estado, solicitud.apoyos_necesarios, solicitud.grupo), (Evento.PENDIENTE, 2, self.henares))
        self.assertContains(self.client.get(f"/eventos/{evento.pk}/"), "Pendiente de apoyos")
        self.como(self.garza)
        self.assertEqual(self.client.get(f"/eventos/{evento.pk}/").status_code, 403)
        apoyar(solicitud, self.garza, True)
        apoyar(solicitud, self.lince, True)
        evento.refresh_from_db()
        self.assertEqual(evento.estado, Evento.CONVOCADO)
        self.assertEqual(self.client.get(f"/eventos/{evento.pk}/").status_code, 200)
        otra = convocar(self.nutria, self.henares, self.reunion, datos_del_servicio(titulo="Grande"), "grupo:1")
        solicitud = Solicitud.objects.get(datos__evento_id=otra.pk)
        self.assertEqual((solicitud.apoyos_necesarios, solicitud.grupo), (5, self.general))

    # El sí del superadmin convoca la reunión sin apoyos.
    def test_reunion_con_el_superadmin(self):
        evento = convocar(self.nutria, self.henares, self.reunion, datos_del_servicio(), "grupo:0")
        aprobar(Solicitud.objects.get(), crear_usuario_de_prueba("superadmin", es_superadmin=True))
        evento.refresh_from_db()
        self.assertEqual(evento.estado, Evento.CONVOCADO)


class PruebasDeLaFicha(PruebaDeEventos):
    """«¿Vas a ir?», cometidos, cancelar, cartel y editar."""

    # Todos ven cuántos van; los alias, solo quien convoca y quien tiene un cometido (3A).
    def test_quien_ve_quien_va(self):
        evento = self.charla()
        responder(self.garza, evento, Asistencia.SI)
        self.como(self.lince)
        respuesta = self.client.get(f"/eventos/{evento.pk}/")
        self.assertContains(respuesta, "Van 1")
        self.assertNotContains(respuesta, "Garza <span")
        apuntar(self.lince, evento, self.lince, "eventos.logistica")
        self.assertContains(self.client.get(f"/eventos/{evento.pk}/"), "Garza <span")
        self.como(self.nutria)
        self.assertContains(self.client.get(f"/eventos/{evento.pk}/"), "Garza <span")

    # Apuntarse y quitarse de un cometido desde la ficha; responder a «¿Vas a ir?».
    def test_cometidos_y_asistencia(self):
        evento = self.charla()
        self.como(self.garza)
        self.client.post(f"/eventos/{evento.pk}/", {"accion": "apuntar", "cometido": "eventos.cuidados"})
        self.assertContains(self.client.get(f"/eventos/{evento.pk}/"), "Quitarme")
        self.client.post(f"/eventos/{evento.pk}/", {"accion": "no_se"})
        self.assertEqual(Asistencia.objects.get(usuario=self.garza).respuesta, Asistencia.NO_SE)
        self.client.post(f"/eventos/{evento.pk}/", {"accion": "desapuntar", "cometido": "eventos.cuidados"})
        self.assertContains(self.client.get(f"/eventos/{evento.pk}/"), "nadie todavía", count=6)

    # Cancelar avisa a quien iba; solo lo hace quien convoca (o la administración).
    def test_cancelar(self):
        evento = self.charla()
        responder(self.garza, evento, Asistencia.SI)
        self.como(self.garza)
        self.client.post(f"/eventos/{evento.pk}/", {"accion": "cancelar"})
        evento.refresh_from_db()
        self.assertEqual(evento.estado, Evento.CONVOCADO)
        self.como(self.nutria)
        self.client.post(f"/eventos/{evento.pk}/", {"accion": "cancelar"})
        evento.refresh_from_db()
        self.assertEqual(evento.estado, Evento.CANCELADO)
        procesar_bandeja()
        self.assertTrue(Notificacion.objects.filter(usuario=self.garza, tipo="eventos.cancelado").exists())

    # El cartel se sube como imagen y solo se entrega a quien ve el evento; un fichero que no es imagen no vale.
    def test_cartel(self):
        imagen = io.BytesIO()
        Image.new("RGB", (20, 20), "red").save(imagen, "PNG")
        url = f"/eventos/convocar/?grupo={self.henares.pk}&tipologia={self.generico.pk}"
        falso = SimpleUploadedFile("cartel.png", b"no es una imagen", content_type="image/png")
        self.assertContains(self.client.post(url, {**datos(), "cartel": falso}), "Envíe una imagen válida")
        bueno = SimpleUploadedFile("cartel.png", imagen.getvalue(), content_type="image/png")
        self.client.post(url, {**datos(), "cartel": bueno})
        evento = Evento.objects.get()
        self.assertEqual(self.client.get(f"/eventos/{evento.pk}/cartel/").status_code, 200)
        self.como(self.erizo)
        self.assertEqual(self.client.get(f"/eventos/{evento.pk}/cartel/").status_code, 404)

    # Editar cambia los datos y la visibilidad (no la de una reunión).
    def test_editar(self):
        evento = self.charla()
        self.client.post(f"/eventos/{evento.pk}/editar/", datos(titulo="Charla nueva", visibilidad="privado"))
        evento.refresh_from_db()
        self.assertEqual((evento.titulo, evento.audiencia.tipo), ("Charla nueva", "privada"))
        self.como(self.garza)
        self.assertEqual(self.client.get(f"/eventos/{evento.pk}/").status_code, 403)

    # Lo que cuestan las listas (con más eventos) y la ficha (con más asistencias y cometidos).
    def test_consultas(self):
        evento = self.charla()

        def mas():
            otro = self.charla(titulo=f"Charla {Evento.objects.count()}")
            responder(self.garza, otro, Asistencia.SI)
            responder(self.lince, evento, Asistencia.NO_SE) if not Asistencia.objects.filter(usuario=self.lince, evento=evento).exists() else None
            persona = crear_usuario_de_prueba(f"Persona {Evento.objects.count()}")
            admitir(persona, self.henares)
            responder(persona, evento, Asistencia.SI)
            apuntar(persona, evento, persona, "eventos.logistica")

        self.comprobar_consultas("/eventos/", 2, mas)
        self.comprobar_consultas("/eventos/mios/", 3, mas)
        self.comprobar_consultas(f"/eventos/{evento.pk}/", 10, mas)


class PruebasDeLaAdministracion(PruebaDeEventos):
    """«Administrar → Eventos de mis grupos»: lo que ve y lo que puede hacer quien administra."""

    # Lince administra GRU Henares: ve los eventos de su grupo y de GRU Sorbe (subgrupo), también la reunión
    # que espera apoyos (con cuántos lleva) y los cancelados; no los de otra organización. Nutria, que no
    # administra nada, no entra.
    def test_pestanas(self):
        self.charla(titulo="Charla de Henares")
        convocar(self.garza, self.sorbe, self.generico, datos_del_servicio(titulo="Huerto de Sorbe"), "grupo:0")
        convocar(self.nutria, self.henares, self.reunion, datos_del_servicio(titulo="Asamblea pendiente"), "grupo:0")
        convocar(self.erizo, self.gru_ebro, self.generico, datos_del_servicio(titulo="Del Ebro"), "grupo:0")
        self.como(self.lince)
        proximos = self.client.get("/eventos/administrados/")
        self.assertContains(proximos, "Charla de Henares")
        self.assertContains(proximos, "Huerto de Sorbe")
        self.assertNotContains(proximos, "Del Ebro")
        self.assertNotContains(proximos, "Asamblea pendiente")
        pendientes = self.client.get("/eventos/administrados/esperan-apoyos/")
        self.assertContains(pendientes, "Asamblea pendiente")
        self.assertContains(pendientes, "0/2")
        self.assertContains(self.client.get("/eventos/administrados/pasados/"), "aún no tienen eventos pasados")
        self.como(self.nutria)
        self.assertEqual(self.client.get("/eventos/administrados/").status_code, 403)

    # Quien administra el grupo de arriba ve la ficha de una reunión que espera apoyos y puede editar y
    # cancelar el evento de un subgrupo; los alias de quien va, no.
    def test_ficha(self):
        pendiente = convocar(self.garza, self.sorbe, self.reunion, datos_del_servicio(titulo="Reunión de Sorbe"), "grupo:0")
        huerto = convocar(self.garza, self.sorbe, self.generico, datos_del_servicio(titulo="Huerto"), "grupo:0")
        responder(self.garza, huerto, Asistencia.SI)
        self.como(self.lince)
        self.assertContains(self.client.get(f"/eventos/{pendiente.pk}/"), "Reunión de Sorbe")
        ficha = self.client.get(f"/eventos/{huerto.pk}/")
        self.assertContains(ficha, "Editar")
        self.assertIsNone(ficha.context["quien_va"])
        self.assertEqual(self.client.get(f"/eventos/{huerto.pk}/editar/").status_code, 200)
        self.client.post(f"/eventos/{huerto.pk}/", {"accion": "cancelar"})
        huerto.refresh_from_db()
        self.assertEqual(huerto.estado, Evento.CANCELADO)
        self.assertContains(self.client.get("/eventos/administrados/cancelados/"), "Huerto")
        # Erizo, de otra organización, ni la ve.
        self.como(self.erizo)
        self.assertEqual(self.client.get(f"/eventos/{pendiente.pk}/").status_code, 403)

    # Lo que cuesta cada pestaña no crece con los eventos.
    def test_consultas(self):
        self.usuario = self.lince
        self.como(self.lince)

        def mas():
            numero = Evento.objects.count()
            convocar(self.garza, self.sorbe, self.generico, datos_del_servicio(titulo=f"Huerto {numero}"), "grupo:0")
            # Cada reunión, de una persona distinta (cada cual solo puede tener una solicitud pendiente).
            persona = crear_usuario_de_prueba(f"Convoca {numero}")
            admitir(persona, self.henares)
            convocar(persona, self.henares, self.reunion, datos_del_servicio(titulo=f"Reunión {numero}"), "grupo:0")

        self.comprobar_consultas("/eventos/administrados/", 3, mas)
        self.comprobar_consultas("/eventos/administrados/esperan-apoyos/", 4, mas)
