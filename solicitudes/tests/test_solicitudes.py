"""
Pruebas de «solicitudes» con el tipo «Entrar en un grupo» (de «grupos»): pedir, apoyar, rechazar, el sí de
la administración y del superadmin, cancelar, caducar, ajustes, quién ve qué y número de consultas.

Estructura: ORG Tajo (GRU Tajo ⊃ GRU Henares ⊃ GRU Sorbe) con Lince admin de GRU Henares, Nutria en GRU
Henares y Garza en GRU Sorbe; Pato, sin grupo, pide entrar en GRU Henares. ORG Ebro con Erizo.
"""

from datetime import timedelta

from django.apps import apps

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from eventos_sw.servicios import procesar_bandeja
from grupos.models import Pertenencia
from grupos.servicios import admitir, crear_grupo, crear_organizacion, nombrar_admin_de_organizacion
from solicitudes.models import Solicitud
from solicitudes.servicios import aprobar, caducar_vencidas, pedir, responder


# Tabla de notificaciones de «comunicaciones», buscada por su nombre: «solicitudes» está en una capa
# inferior y no puede importarlo (ni en las pruebas).
Notificacion = apps.get_model("comunicaciones", "Notificacion")


class PruebaDeSolicitudes(PruebaDePantalla):
    """Base con la estructura del principio del fichero; la sesión es de Nutria."""

    # Crea la estructura.
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
        cls.pato = crear_usuario_de_prueba("Pato")
        admitir(cls.lince, cls.henares, rol=Pertenencia.ADMIN_GRUPO)
        admitir(cls.nutria, cls.henares)
        admitir(cls.garza, cls.sorbe)
        admitir(cls.erizo, cls.gru_ebro)
        cls.usuario = cls.nutria

    # Inicia sesión como otra persona.
    def como(self, usuario):
        cache.clear()
        self.client.force_login(usuario)

    # Pato pide entrar en GRU Henares. Devuelve la solicitud.
    def pide_pato(self):
        return pedir(self.pato, "grupos.entrar", self.henares, "Quiero entrar", "Vivo en el barrio")


class PruebasDeEntrar(PruebaDeSolicitudes):
    """El recorrido de «Entrar en un grupo»."""

    # Con 2 apoyos y el sí de Lince, Pato entra (y GRU Henares pasa a ser su asamblea base) y se le avisa.
    def test_apoyos_y_si_de_la_administracion(self):
        solicitud = self.pide_pato()
        self.assertEqual((solicitud.apoyos_necesarios, solicitud.necesita_aprobacion), (2, True))
        # El trabajador avisa a Lince de que necesita su sí (mientras sigue pendiente).
        procesar_bandeja()
        self.assertTrue(Notificacion.objects.filter(usuario=self.lince, texto__contains="Necesita el sí de la administración").exists())
        responder(solicitud, self.nutria, True)
        responder(solicitud, self.garza, True)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, Solicitud.PENDIENTE)
        aprobar(solicitud, self.lince)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, Solicitud.ACEPTADA)
        self.assertTrue(Pertenencia.objects.filter(usuario=self.pato, grupo=self.henares, es_base=True).exists())
        procesar_bandeja()
        self.assertTrue(Notificacion.objects.filter(usuario=self.pato, texto__startswith="Se ha aceptado tu solicitud").exists())

    # El sí del superadmin basta, sin apoyos.
    def test_basta_el_superadmin(self):
        solicitud = self.pide_pato()
        aprobar(solicitud, crear_usuario_de_prueba("superadmin", es_superadmin=True))
        solicitud.refresh_from_db()
        self.assertEqual((solicitud.estado, solicitud.por_el_superadmin), (Solicitud.ACEPTADA, True))

    # Los rechazos no vetan; quien no es del grupo no puede responder; no se puede pedir dos veces ni pedir
    # entrar donde ya se está; un miembro normal no da el sí de la administración.
    def test_reglas(self):
        solicitud = self.pide_pato()
        responder(solicitud, self.nutria, False)
        with self.assertRaises(ValidationError):
            responder(solicitud, self.erizo, True)
        with self.assertRaises(ValidationError):
            self.pide_pato()
        with self.assertRaises(ValidationError):
            pedir(self.garza, "grupos.entrar", self.henares, "Entrar")
        with self.assertRaises(ValidationError):
            aprobar(solicitud, self.nutria)
        responder(solicitud, self.nutria, True)
        responder(solicitud, self.garza, True)
        aprobar(solicitud, self.lince)
        solicitud.refresh_from_db()
        self.assertEqual((solicitud.estado, solicitud.rechazos), (Solicitud.ACEPTADA, 0))

    # Si pasa la fecha, caduca y se avisa; quien la pidió puede cancelarla antes.
    def test_caducar_y_cancelar(self):
        solicitud = self.pide_pato()
        Solicitud.objects.filter(pk=solicitud.pk).update(caduca_el=timezone.localdate() - timedelta(days=1))
        self.assertEqual(caducar_vencidas(), 1)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, Solicitud.CADUCADA)
        procesar_bandeja()
        self.assertTrue(Notificacion.objects.filter(usuario=self.pato, texto__startswith="Ha caducado").exists())
        otra = self.pide_pato()
        self.como(self.pato)
        self.client.post(f"/solicitudes/{otra.pk}/", {"accion": "cancelar"})
        otra.refresh_from_db()
        self.assertEqual(otra.estado, Solicitud.CANCELADA)


class PruebasDePantallas(PruebaDeSolicitudes):
    """Las pantallas."""

    # Pedir desde la pantalla, apoyar y ver «1 de 2» con el alias de quien apoya; los rechazos, solo el número.
    def test_pedir_y_apoyar(self):
        self.como(self.pato)
        datos = {"tipo": "grupos.entrar", "grupo": self.henares.pk, "descripcion": "Quiero entrar", "justificacion": ""}
        respuesta = self.client.post("/solicitudes/nueva/", datos)
        solicitud = Solicitud.objects.get()
        self.assertRedirects(respuesta, f"/solicitudes/{solicitud.pk}/")
        self.como(self.nutria)
        self.assertContains(self.client.get("/solicitudes/"), "data-contador>(1)</span>")
        self.client.post(f"/solicitudes/{solicitud.pk}/", {"accion": "apoyar"})
        self.como(self.garza)
        self.client.post(f"/solicitudes/{solicitud.pk}/", {"accion": "rechazar"})
        respuesta = self.client.get(f"/solicitudes/{solicitud.pk}/")
        self.assertContains(respuesta, "<strong>1 de 2</strong> apoyos (Nutria)", html=False)
        self.assertContains(respuesta, "1 rechazo")
        self.assertNotContains(respuesta, "(Garza)")

    # Quien no es del grupo no la ve; el superadmin ve todas con «Aceptar como superadmin».
    def test_quien_ve(self):
        solicitud = self.pide_pato()
        self.como(self.erizo)
        self.assertEqual(self.client.get(f"/solicitudes/{solicitud.pk}/").status_code, 404)
        self.assertContains(self.client.get("/solicitudes/"), "No hay nada pendiente de apoyar en tus grupos.")
        self.como(crear_usuario_de_prueba("superadmin", es_superadmin=True))
        self.assertContains(self.client.get("/solicitudes/por-aprobar/"), "Aceptar como superadmin")
        self.assertNotContains(self.client.get("/solicitudes/"), "Aceptar como superadmin")

    # El admin de la organización cambia los apoyos de su organización; las nuevas solicitudes los usan.
    def test_ajustes(self):
        zorro = crear_usuario_de_prueba("Zorro")
        admitir(zorro, self.general)
        nombrar_admin_de_organizacion(zorro, self.tajo)
        self.como(zorro)
        respuesta = self.client.post("/solicitudes/ajustes/", {"tipo": "grupos.entrar", "organizacion": self.tajo.pk, "apoyos": 4, "dias": 7})
        self.assertRedirects(respuesta, "/solicitudes/ajustes/")
        self.assertEqual(self.client.post("/solicitudes/ajustes/", {"tipo": "grupos.entrar", "organizacion": "", "apoyos": 1, "dias": 7}).status_code, 403)
        solicitud = self.pide_pato()
        self.assertEqual(solicitud.apoyos_necesarios, 4)
        self.assertEqual(solicitud.caduca_el, timezone.localdate() + timedelta(days=7))

    # Lo que cuestan las listas (con más solicitudes y apoyos) y una solicitud.
    def test_consultas(self):
        solicitud = self.pide_pato()

        def mas():
            persona = crear_usuario_de_prueba(f"Persona {Solicitud.objects.count()}")
            otra = pedir(persona, "grupos.entrar", self.henares, "Yo también")
            responder(otra, self.garza, True)

        self.comprobar_consultas("/solicitudes/", 8, mas)
        self.comprobar_consultas("/solicitudes/pasadas/", 6, mas)
        self.comprobar_consultas(f"/solicitudes/{solicitud.pk}/", 8, None)
        # «Por aprobar», como Lince (admin de GRU Henares): ahí está lo que espera su sí.
        self.como(self.lince)
        respuesta = self.comprobar_consultas("/solicitudes/por-aprobar/", 8, mas)
        self.assertContains(respuesta, "Dar el sí de la administración")
