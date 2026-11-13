"""
Pruebas de «talentos»: catálogo (sin repetir, por relacionadas, fusionar), mis talentos y con quién los
comparto, recuentos (nunca quiénes), peticiones (a quién llegan, «Lo ofrezco», quién ve el alias,
cerrar), el número del menú y lo que cuestan las pantallas.

Estructura: ORG Tajo (GRU Tajo ⊃ GRU Henares ⊃ GRU Sorbe) con Lince admin de GRU Henares, Nutria en GRU
Henares y Garza en GRU Sorbe; ORG Ebro con Erizo.
"""

from django.apps import apps
from django.core.cache import cache
from django.core.exceptions import ValidationError

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from eventos_sw.servicios import procesar_bandeja
from grupos.models import Pertenencia
from grupos.servicios import admitir, crear_grupo, crear_organizacion
from talentos.models import Ofrecimiento, PeticionDeTalentos, Talento, TalentoDePersona
from talentos.servicios import anadir, compartir, fusionar, obtener_o_crear, ofrecer, pedir, peticiones_para, recuento_del_grupo

# Tabla de notificaciones de «comunicaciones», buscada por su nombre: «talentos» está en una capa
# inferior y no puede importarlo (ni en las pruebas).
Notificacion = apps.get_model("comunicaciones", "Notificacion")


class PruebaDeTalentos(PruebaDePantalla):
    """Base con la estructura del principio del fichero; la sesión es de Nutria."""

    # Crea la estructura y el talento «Furgoneta» (con la relacionada «Camioneta»).
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
        cls.furgoneta = Talento(nombre="Furgoneta", tipo=Talento.RECURSO, relacionadas="camioneta")
        cls.furgoneta.save()
        cls.usuario = cls.nutria

    # Inicia sesión como otra persona.
    def como(self, usuario):
        cache.clear()
        self.client.force_login(usuario)

    # Da a una persona la furgoneta y la comparte con unos grupos.
    def con_furgoneta(self, persona, *grupos):
        suyo = anadir(persona, "Furgoneta", Talento.RECURSO)
        compartir(suyo, [grupo.pk for grupo in grupos])
        return suyo


class PruebasDelCatalogo(PruebaDeTalentos):
    """El catálogo común."""

    # Escribirlo distinto o por una relacionada da el mismo talento; uno nuevo se crea en forma fija.
    def test_sin_repetir(self):
        self.assertEqual(obtener_o_crear("FURGONETA", Talento.RECURSO), self.furgoneta)
        self.assertEqual(obtener_o_crear("camioneta", Talento.RECURSO), self.furgoneta)
        nuevo = obtener_o_crear("trabajos   VERTICALES", Talento.HABILIDAD)
        self.assertEqual(nuevo.nombre, "Trabajos verticales")

    # Fusionar: quien tenía el repetido pasa a tener el que se queda (compartido igual) y el nombre queda
    # como relacionada.
    def test_fusionar(self):
        furgo = Talento(nombre="Furgo", tipo=Talento.RECURSO)
        furgo.save()
        suyo = TalentoDePersona.objects.create(usuario=self.nutria, talento=furgo)
        compartir(suyo, [self.henares.pk])
        fusionar(self.furgoneta, [furgo])
        self.assertFalse(Talento.objects.filter(nombre="Furgo").exists())
        self.assertEqual(TalentoDePersona.objects.get(usuario=self.nutria).talento, self.furgoneta)
        self.furgoneta.refresh_from_db()
        self.assertEqual(self.furgoneta.relacionadas, "Camioneta, Furgo")
        self.assertEqual(recuento_del_grupo(self.henares), [(self.furgoneta, 1)])


class PruebasDeMisTalentos(PruebaDeTalentos):
    """Mis talentos y los recuentos."""

    # Añadir desde la pantalla y compartir con su grupo; no con un grupo ajeno.
    def test_anadir_y_compartir(self):
        self.client.post("/talentos/", {"accion": "anadir", "nombre": "camioneta", "tipo": "recurso", "detalle": "9 plazas"})
        suyo = TalentoDePersona.objects.get(usuario=self.nutria)
        self.assertEqual(suyo.talento, self.furgoneta)
        self.client.post("/talentos/", {"accion": "compartir", "talento": suyo.pk, "grupos": [self.henares.pk], "detalle": "9 plazas"})
        self.assertEqual(list(suyo.compartidos.values_list("grupo", flat=True)), [self.henares.pk])
        respuesta = self.client.post("/talentos/", {"accion": "compartir", "talento": suyo.pk, "grupos": [self.gru_ebro.pk]})
        self.assertContains(respuesta, "Solo puedes compartir")

    # El recuento del grupo cuenta también los compartidos con sus subgrupos, y no dice quiénes.
    def test_recuento(self):
        self.con_furgoneta(self.nutria, self.henares)
        self.con_furgoneta(self.garza, self.sorbe)
        self.assertEqual(recuento_del_grupo(self.henares), [(self.furgoneta, 2)])
        self.assertEqual(recuento_del_grupo(self.sorbe), [(self.furgoneta, 1)])
        respuesta = self.client.get(f"/talentos/grupos/?grupo={self.henares.pk}")
        self.assertContains(respuesta, "2 personas")
        self.assertNotContains(respuesta, "Garza")


class PruebasDePeticiones(PruebaDeTalentos):
    """Peticiones de talentos."""

    # Lince pide 2 furgonetas a GRU Henares: avisa a Nutria y a Garza (que la comparten con el grupo o un
    # subgrupo), no a quien no la comparte. Nutria la ofrece: Lince ve su alias; Garza solo el número.
    def test_pedir_y_ofrecer(self):
        self.con_furgoneta(self.nutria, self.henares)
        self.con_furgoneta(self.garza, self.sorbe)
        anadir(self.erizo, "Furgoneta", Talento.RECURSO)
        peticion = pedir(self.lince, self.henares, "Mudanza del local", "", [(self.furgoneta, 2)])
        procesar_bandeja()
        avisados = set(Notificacion.objects.filter(tipo="talentos.peticion").values_list("usuario__alias", flat=True))
        self.assertEqual(avisados, {"Nutria", "Garza"})
        self.assertContains(self.client.get("/talentos/peticiones/"), "data-contador>(1)</span>")
        necesidad = peticion.necesidades.get()
        self.client.post(f"/talentos/peticiones/{peticion.pk}/", {"accion": "ofrecer", "necesidad": necesidad.pk, "mensaje": "por la tarde"})
        self.assertTrue(Ofrecimiento.objects.filter(usuario=self.nutria).exists())
        procesar_bandeja()
        self.assertTrue(Notificacion.objects.filter(usuario=self.lince, texto="Nutria ofrece Furgoneta para «Mudanza del local».").exists())
        self.como(self.lince)
        self.assertContains(self.client.get(f"/talentos/peticiones/{peticion.pk}/"), "Nutria: «por la tarde»")
        self.como(self.garza)
        respuesta = self.client.get(f"/talentos/peticiones/{peticion.pk}/")
        self.assertContains(respuesta, "1 de 2")
        self.assertNotContains(respuesta, "Nutria")

    # Solo piden los admins; sin el talento no se ofrece; quien no es del grupo no la ve; cerrada, no se ofrece.
    def test_reglas(self):
        with self.assertRaises(Exception):
            pedir(self.nutria, self.henares, "X", "", [(self.furgoneta, 1)])
        peticion = pedir(self.lince, self.henares, "Mudanza", "", [(self.furgoneta, 1)])
        necesidad = peticion.necesidades.get()
        with self.assertRaises(ValidationError):
            ofrecer(self.nutria, necesidad)
        self.como(self.erizo)
        self.assertEqual(self.client.get(f"/talentos/peticiones/{peticion.pk}/").status_code, 403)
        self.como(self.lince)
        self.client.post(f"/talentos/peticiones/{peticion.pk}/", {"accion": "cerrar"})
        peticion.refresh_from_db()
        self.assertEqual(peticion.estado, PeticionDeTalentos.CERRADA)
        self.con_furgoneta(self.nutria, self.henares)
        with self.assertRaises(ValidationError):
            ofrecer(self.nutria, necesidad)

    # El enlace «Tengo dudas» lleva a escribir a la administración del grupo con el asunto puesto.
    def test_dudas(self):
        peticion = pedir(self.lince, self.henares, "Mudanza", "", [(self.furgoneta, 1)])
        respuesta = self.client.get(f"/talentos/peticiones/{peticion.pk}/")
        self.assertContains(respuesta, f"administracion=g{self.henares.pk}&amp;asunto=Talentos%3A+Mudanza")
        respuesta = self.client.get(f"/comunicaciones/conversaciones/nueva/?administracion=g{self.henares.pk}&asunto=Talentos%3A+Mudanza")
        self.assertContains(respuesta, 'value="Talentos: Mudanza"')

    # Lo que cuestan las pantallas (con más talentos, compartidos y peticiones).
    def test_consultas(self):
        def mas():
            numero = Talento.objects.count()
            suyo = anadir(self.nutria, f"Talento {numero}", Talento.HABILIDAD)
            compartir(suyo, [self.henares.pk, self.general.pk])
            pedir(self.lince, self.henares, f"Petición {numero}", "", [(suyo.talento, 1), (self.furgoneta, 2)])

        mas()
        self.comprobar_consultas("/talentos/", 6, mas)
        self.comprobar_consultas("/talentos/peticiones/", 6, mas)
        self.comprobar_consultas(f"/talentos/grupos/?grupo={self.henares.pk}", 5, mas)
        self.assertGreater(peticiones_para(self.nutria), 0)
