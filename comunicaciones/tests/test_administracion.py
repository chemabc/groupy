"""
Pruebas de los avisos de la administración, las conversaciones con la administración y los niveles de
aviso: número de consultas, quién puede avisar a quién, quién lee cada conversación, la firma de los
admins y el estado.

Estructura: ORG Tajo (GRU Tajo ⊃ GRU Henares ⊃ GRU Sorbe) con Lince admin de GRU Henares, Zorro admin de
ORG Tajo, Nutria en GRU Henares y Garza en GRU Sorbe; ORG Ebro con Erizo admin de GRU Ebro.
"""

from django.core.cache import cache

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from comunicaciones.administraciones import Buzon
from comunicaciones.models import AvisoDeAdministracion, Conversacion, NivelDeAviso, Notificacion
from comunicaciones.servicios import abrir_conversacion, enviar_aviso, escribir
from grupos.models import Pertenencia
from grupos.servicios import admitir, crear_grupo, crear_organizacion, nombrar_admin_de_organizacion


class PruebaDeAdministracion(PruebaDePantalla):
    """Base con la estructura del principio del fichero; la sesión es de Lince."""

    # Crea la estructura.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.general)
        cls.sorbe = crear_grupo(cls.tajo, "GRU Sorbe", padre=cls.henares)
        cls.ebro, cls.gru_ebro = crear_organizacion("ORG Ebro", "GRU Ebro")
        cls.lince = crear_usuario_de_prueba("Lince")
        cls.zorro = crear_usuario_de_prueba("Zorro")
        cls.nutria = crear_usuario_de_prueba("Nutria")
        cls.garza = crear_usuario_de_prueba("Garza")
        cls.erizo = crear_usuario_de_prueba("Erizo")
        admitir(cls.lince, cls.henares, rol=Pertenencia.ADMIN_GRUPO)
        admitir(cls.zorro, cls.general)
        nombrar_admin_de_organizacion(cls.zorro, cls.tajo)
        admitir(cls.nutria, cls.henares)
        admitir(cls.garza, cls.sorbe)
        admitir(cls.erizo, cls.gru_ebro, rol=Pertenencia.ADMIN_GRUPO)
        cls.usuario = cls.lince
        cls.atencion = NivelDeAviso.objects.get(nombre="Atención")

    # Inicia sesión como otra persona.
    def como(self, usuario):
        cache.clear()
        self.client.force_login(usuario)


class PruebasDeAvisos(PruebaDeAdministracion):
    """Avisos de la administración."""

    # Lince avisa a GRU Henares (con su subgrupo): llega a Nutria y a Garza, no a él mismo, con el color del
    # nivel; se puede responder y la respuesta abre una conversación con su administración.
    def test_avisar_y_responder(self):
        datos = {
            "administracion": f"g{self.henares.pk}", "nivel": self.atencion.pk, "asunto": "Asamblea el jueves",
            "texto": "Traed ideas.", "grupos": [self.henares.pk], "alias": "", "permite_responder": "on",
        }
        self.assertRedirects(self.client.post("/comunicaciones/avisos/", datos), "/comunicaciones/avisos/")
        aviso = AvisoDeAdministracion.objects.get()
        self.assertEqual(aviso.numero_de_personas, 2)
        self.assertEqual(set(Notificacion.objects.values_list("usuario__alias", flat=True)), {"Nutria", "Garza"})
        self.como(self.nutria)
        bandeja = self.client.get("/comunicaciones/")
        self.assertContains(bandeja, "Admin de GRU Henares (ORG Tajo): Asamblea el jueves")
        self.assertContains(bandeja, self.atencion.color)
        respuesta = self.client.get(f"/comunicaciones/avisos/{aviso.pk}/")
        self.assertContains(respuesta, "Responder a Admin de GRU Henares")
        datos = {"administracion": f"g{self.henares.pk}", "asunto": "Re: Asamblea el jueves", "texto": "¿A qué hora?"}
        self.client.post(f"/comunicaciones/conversaciones/nueva/?aviso={aviso.pk}", datos)
        conversacion = Conversacion.objects.get()
        self.assertEqual((conversacion.persona, conversacion.grupo, conversacion.aviso), (self.nutria, self.henares, aviso))

    # Lince no puede avisar a grupos de fuera de su rama ni a personas de otra organización; Nutria no puede
    # avisar.
    def test_limites(self):
        datos = {"administracion": f"g{self.henares.pk}", "nivel": self.atencion.pk, "asunto": "A", "texto": "B", "grupos": [self.general.pk]}
        # GRU Tajo ni siquiera se ofrece en la lista de grupos de Lince.
        self.assertContains(self.client.post("/comunicaciones/avisos/", datos), "Escoja una opción válida")
        datos = {**datos, "grupos": [], "alias": "Erizo"}
        self.assertContains(self.client.post("/comunicaciones/avisos/", datos), "Erizo no está en lo que alcanza")
        self.como(self.nutria)
        self.assertEqual(self.client.get("/comunicaciones/avisos/").status_code, 403)

    # Lo que cuesta la pantalla de avisos (con más avisos enviados).
    def test_consultas(self):
        def mas():
            enviar_aviso(self.lince, Buzon(grupo=self.henares), self.atencion, "Aviso", "Texto", grupos=[self.henares])

        self.comprobar_consultas("/comunicaciones/avisos/", 10, mas)


class PruebasDeConversaciones(PruebaDeAdministracion):
    """Conversaciones con la administración."""

    # Nutria escribe a la administración de GRU Henares: la leen Lince (su admin), Zorro (admin de la
    # organización) y el superadmin, no Garza ni Erizo. Lince responde firmando «Admin de GRU Henares
    # (Lince)» y cambia el estado.
    def test_quien_lee_y_firma(self):
        conversacion = abrir_conversacion(self.nutria, Buzon(grupo=self.henares), "Llaves del local", "¿Quién las tiene?")
        url = f"/comunicaciones/conversaciones/{conversacion.pk}/"
        for persona, codigo in ((self.lince, 200), (self.zorro, 200), (self.garza, 403), (self.erizo, 403), (self.nutria, 200)):
            self.como(persona)
            self.assertEqual(self.client.get(url).status_code, codigo, persona)
        self.como(crear_usuario_de_prueba("superadmin", es_superadmin=True))
        self.assertEqual(self.client.get(url).status_code, 200)
        self.como(self.lince)
        self.client.post(url, {"accion": "responder", "texto": "Las tengo yo."})
        self.assertContains(self.client.get(url), "Admin de GRU Henares (Lince)")
        self.client.post(url, {"accion": "estado", "estado": Conversacion.SOLUCIONADA})
        conversacion.refresh_from_db()
        self.assertEqual(conversacion.estado, Conversacion.SOLUCIONADA)
        self.como(self.nutria)
        self.assertEqual(self.client.post(url, {"accion": "estado", "estado": Conversacion.ABIERTA}).status_code, 403)

    # El número del menú: Lince ve (1) cuando Nutria escribe y (0) al leerla; Nutria, (1) cuando responde Lince.
    def test_sin_leer(self):
        with self.captureOnCommitCallbacks(execute=True):
            conversacion = abrir_conversacion(self.nutria, Buzon(grupo=self.henares), "Duda", "Hola")
        self.assertContains(self.client.get("/comunicaciones/conversaciones/"), "data-contador>(1)</span>")
        with self.captureOnCommitCallbacks(execute=True):
            self.client.get(f"/comunicaciones/conversaciones/{conversacion.pk}/")
        self.assertContains(self.client.get("/comunicaciones/conversaciones/"), "data-contador>(0)</span>")
        with self.captureOnCommitCallbacks(execute=True):
            escribir(conversacion, self.lince, "Dime", como_admin=True)
        self.como(self.nutria)
        self.assertContains(self.client.get("/comunicaciones/conversaciones/"), "data-contador>(1)</span>")

    # Escribir a la administración ofrece la de sus grupos (también los de encima), su organización y el
    # superadmin; no las de otra organización.
    def test_a_quien_se_escribe(self):
        self.como(self.garza)
        respuesta = self.client.get("/comunicaciones/conversaciones/nueva/")
        for nombre in ("Admin de GRU Sorbe", "Admin de GRU Henares", "Admin de GRU Tajo", "Admin de ORG Tajo", "Superadmin"):
            self.assertContains(respuesta, nombre)
        self.assertNotContains(respuesta, "ORG Ebro")

    # Lo que cuesta la lista (con más conversaciones) y una conversación (con más mensajes).
    def test_consultas(self):
        conversacion = abrir_conversacion(self.nutria, Buzon(grupo=self.henares), "Duda", "Hola")

        def mas():
            abrir_conversacion(self.garza, Buzon(grupo=self.henares), "Otra", "Hola")
            escribir(conversacion, self.lince, "Respuesta", como_admin=True)

        self.comprobar_consultas("/comunicaciones/conversaciones/", 5, mas)
        self.comprobar_consultas(f"/comunicaciones/conversaciones/{conversacion.pk}/", 6, mas)


class PruebasDeNiveles(PruebaDeAdministracion):
    """Configuración → Niveles de aviso (solo el superadmin)."""

    # Crear uno, cambiarle el color, no poder borrar uno usado; un admin no entra.
    def test_niveles(self):
        self.assertEqual(self.client.get("/comunicaciones/niveles/").status_code, 403)
        self.como(crear_usuario_de_prueba("superadmin", es_superadmin=True))
        datos = {"accion": "crear", "nuevo-nombre": "Urgente", "nuevo-descripcion": "", "nuevo-color": "#7f1d1d", "nuevo-orden": 40}
        self.assertRedirects(self.client.post("/comunicaciones/niveles/", datos), "/comunicaciones/niveles/")
        urgente = NivelDeAviso.objects.get(nombre="Urgente")
        prefijo = f"n{urgente.pk}"
        datos = {"accion": "editar", "nivel": urgente.pk, f"{prefijo}-nombre": "Urgente", f"{prefijo}-descripcion": "", f"{prefijo}-color": "#000000", f"{prefijo}-orden": 5}
        self.client.post("/comunicaciones/niveles/", datos)
        urgente.refresh_from_db()
        self.assertEqual(urgente.color, "#000000")
        enviar_aviso(self.lince, Buzon(grupo=self.henares), self.atencion, "Aviso", "Texto", grupos=[self.henares])
        respuesta = self.client.post("/comunicaciones/niveles/", {"accion": "borrar", "nivel": self.atencion.pk})
        self.assertContains(respuesta, "ya se ha usado")
        self.client.post("/comunicaciones/niveles/", {"accion": "borrar", "nivel": urgente.pk})
        self.assertFalse(NivelDeAviso.objects.filter(nombre="Urgente").exists())
