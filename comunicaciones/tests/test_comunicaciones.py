"""
Pruebas de «comunicaciones»: el registro conecta los avisos al repartidor, el repartido respeta las
preferencias, las pantallas cuestan pocas consultas y cada persona solo ve y toca sus notificaciones.
También, de punta a punta, los avisos del módulo «grupos».
"""

from django.core.cache import cache
from django.test import SimpleTestCase

from base.contrato import Emision, TipoDeAviso
from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba, modulo_falso
from base.registro import RegistroDeModulos
from comunicaciones.models import Notificacion
from comunicaciones.servicios import poner_preferencias, sin_ver
from eventos_sw.servicios import procesar_bandeja
from grupos.models import Pertenencia
from grupos.servicios import admitir, cambiar_rol, crear_grupo, crear_organizacion


class PruebasDelRegistroDeAvisos(SimpleTestCase):
    """El registro añade al repartidor una escucha asíncrona por cada tipo de aviso."""

    # Con un repartidor, cada aviso tiene su escucha (con el código del aviso como dato fijo); un aviso
    # con un origen desconocido o un eventos_sw que nadie emite es un error.
    def test_conecta_y_comprueba(self):
        alfa = modulo_falso(
            "alfa",
            emite=(Emision("alfa.creado", "…"),),
            avisos=(TipoDeAviso("alfa.creado", "Se ha creado", "sistema", "alfa.creado", "alfa.avisos.creado"),),
        )
        repartidor = modulo_falso("beta", reparte_avisos="beta.repartir")
        nuevo = RegistroDeModulos()
        nuevo.cargar([alfa, repartidor])
        self.assertEqual(nuevo.errores, [])
        escucha = nuevo.escuchas["alfa.creado"][0]
        self.assertEqual((escucha.receptor, dict(escucha.extra)), ("beta.repartir", {"aviso": "alfa.creado"}))
        malo = modulo_falso("alfa", avisos=(TipoDeAviso("alfa.x", "X", "nada", "alfa.nadie", "alfa.avisos.x"),))
        nuevo.cargar([malo])
        self.assertEqual(len(nuevo.errores), 2)


class PruebaDeComunicaciones(PruebaDePantalla):
    """Base: ORG Tajo con GRU Tajo ⊃ GRU Henares; Nutria (la sesión) y Lince."""

    # Crea la estructura.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.general)
        cls.usuario = crear_usuario_de_prueba("Nutria")
        cls.lince = crear_usuario_de_prueba("Lince")

    # Admite a Nutria en un grupo nuevo y reparte el aviso (como haría el trabajador). Devuelve el grupo.
    def admitir_y_repartir(self, nombre="GRU Sorbe"):
        with self.captureOnCommitCallbacks(execute=True):
            grupo = crear_grupo(self.tajo, nombre, padre=self.henares)
            admitir(self.usuario, grupo)
            procesar_bandeja()
        return grupo


class PruebasDeLosAvisosDeGrupos(PruebaDeComunicaciones):
    """De punta a punta: el cambio en «grupos» acaba en la bandeja de la persona."""

    # Admitir y cambiar el rol avisan a la persona, con enlace a la ficha del grupo.
    def test_admitido_y_rol(self):
        grupo = self.admitir_y_repartir()
        notificacion = Notificacion.objects.get(usuario=self.usuario)
        self.assertEqual(notificacion.texto, "Te han admitido en GRU Sorbe (ORG Tajo).")
        self.assertEqual((notificacion.origen, notificacion.enlace), ("grupos", f"/organizaciones/grupo/{grupo.pk}/"))
        cambiar_rol(Pertenencia.objects.get(usuario=self.usuario, grupo=grupo), Pertenencia.ADMIN_GRUPO)
        procesar_bandeja()
        self.assertTrue(Notificacion.objects.filter(texto="Ahora tu rol en GRU Sorbe (ORG Tajo) es «Admin del grupo».").exists())

    # Quien desactiva un tipo de aviso deja de recibirlo.
    def test_preferencias(self):
        poner_preferencias(self.usuario, [])
        self.admitir_y_repartir()
        self.assertFalse(Notificacion.objects.exists())
        respuesta = self.client.post("/comunicaciones/preferencias/", {"activados": ["grupos.admitido"]})
        self.assertContains(respuesta, "Preferencias guardadas.")
        self.admitir_y_repartir("GRU Badiel")
        self.assertEqual(Notificacion.objects.count(), 1)


class PruebasDeLaBandeja(PruebaDeComunicaciones):
    """La pantalla de notificaciones."""

    # Cuesta lo mismo con pocas notificaciones que con muchas, y lo mismo las preferencias.
    def test_consultas(self):
        def mas():
            Notificacion.objects.bulk_create(
                Notificacion(usuario=self.usuario, tipo="grupos.admitido", origen=origen, texto="Hola") for origen in ("grupos", "sistema")
            )

        self.comprobar_consultas("/comunicaciones/", 3, mas)
        self.comprobar_consultas("/comunicaciones/preferencias/", 2, None)

    # El número del menú son las sin ver; marcar una como vista lo baja.
    def test_contador(self):
        self.admitir_y_repartir()
        self.assertContains(self.client.get("/comunicaciones/"), "data-contador>(1)</span>")
        notificacion = Notificacion.objects.get()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/comunicaciones/", {"accion": "vista", "notificacion": notificacion.pk})
        self.assertContains(self.client.get("/comunicaciones/"), "data-contador>(0)</span>")

    # Abrir una notificación la marca como vista y lleva a su enlace (solo si es de la aplicación).
    def test_abrir(self):
        grupo = self.admitir_y_repartir()
        notificacion = Notificacion.objects.get()
        self.assertRedirects(self.client.get(f"/comunicaciones/notificacion/{notificacion.pk}/"), f"/organizaciones/grupo/{grupo.pk}/")
        notificacion.refresh_from_db()
        self.assertIsNotNone(notificacion.vista_el)
        notificacion.enlace = "https://malo.example/"
        notificacion.save()
        self.assertRedirects(self.client.get(f"/comunicaciones/notificacion/{notificacion.pk}/"), "/comunicaciones/")

    # La papelera borra una; «Limpiar las vistas» borra solo las vistas; nadie toca las de otra persona.
    def test_borrar_y_limpiar(self):
        vista, sin_ver_, otra, ajena = Notificacion.objects.bulk_create(
            [
                Notificacion(usuario=self.usuario, tipo="t", origen="grupos", texto="Vista"),
                Notificacion(usuario=self.usuario, tipo="t", origen="grupos", texto="Sin ver"),
                Notificacion(usuario=self.usuario, tipo="t", origen="sistema", texto="Otra"),
                Notificacion(usuario=self.lince, tipo="t", origen="grupos", texto="De Lince"),
            ]
        )
        Notificacion.objects.filter(pk=vista.pk).update(vista_el="2026-11-13T10:00:00Z")
        respuesta = self.client.get("/comunicaciones/")
        self.assertContains(respuesta, "Limpiar las vistas")
        self.assertNotContains(respuesta, "De Lince")
        self.client.post("/comunicaciones/", {"accion": "borrar", "notificacion": otra.pk})
        self.client.post("/comunicaciones/", {"accion": "borrar", "notificacion": ajena.pk})
        self.assertEqual(self.client.get(f"/comunicaciones/notificacion/{ajena.pk}/").status_code, 404)
        self.client.post("/comunicaciones/", {"accion": "limpiar"})
        self.assertEqual(list(Notificacion.objects.order_by("texto").values_list("texto", flat=True)), ["De Lince", "Sin ver"])
        cache.clear()
        self.assertEqual(sin_ver(self.usuario), 1)

    # Las bandejas filtran por origen.
    def test_bandejas(self):
        Notificacion.objects.bulk_create(
            [
                Notificacion(usuario=self.usuario, tipo="t", origen="grupos", texto="De grupos"),
                Notificacion(usuario=self.usuario, tipo="t", origen="sistema", texto="Del sistema"),
            ]
        )
        respuesta = self.client.get("/comunicaciones/?origen=sistema")
        self.assertContains(respuesta, "Del sistema")
        self.assertNotContains(respuesta, "De grupos")
        self.assertContains(respuesta, "Organización y grupos <strong>(1)</strong>")
