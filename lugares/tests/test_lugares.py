"""
Pruebas de «lugares»: coordenadas desde la URL, elegir el lugar, proponer lugares y cambios (y que el
superadmin los acepte o rechace), importar desde una hoja, qué ve cada cual según la configuración de su
organización, recuentos desde 5 y número de consultas.
"""

import io

from django.core.cache import cache
from django.test import SimpleTestCase

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from grupos.servicios import admitir, crear_organizacion, nombrar_admin_de_organizacion
from lugares.models import ConfiguracionDeLugares, Lugar, LugarDePersona, PropuestaDeLugar, coordenadas_de
from lugares.servicios import proponer, recuentos

# URL de OpenStreetMap de ejemplo, con sus coordenadas.
URL = "https://www.openstreetmap.org/#map=18/40.4820/-3.3640"


class PruebasDeCoordenadas(SimpleTestCase):
    """Sacar las coordenadas de las URL de los mapas."""

    # OpenStreetMap (los dos formatos), Google Maps y una sin coordenadas.
    def test_formatos(self):
        self.assertEqual(coordenadas_de(URL), (40.482, -3.364))
        self.assertEqual(coordenadas_de("https://www.openstreetmap.org/?mlat=40.41&mlon=-3.70#map=17/40.41/-3.70"), (40.41, -3.7))
        self.assertEqual(coordenadas_de("https://www.google.com/maps/place/X/@40.4168,-3.7038,17z"), (40.4168, -3.7038))
        self.assertEqual(coordenadas_de("https://maps.google.com/?q=40.4168,-3.7038"), (40.4168, -3.7038))
        self.assertEqual(coordenadas_de("https://ejemplo.org/sitio"), (None, None))


class PruebaDeLugares(PruebaDePantalla):
    """Base: ORG Tajo con Nutria (la sesión) y un lugar; el superadmin aparte."""

    # Crea la organización, las personas y el lugar.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.usuario = crear_usuario_de_prueba("Nutria")
        admitir(cls.usuario, cls.general)
        cls.superadmin = crear_usuario_de_prueba("superadmin", es_superadmin=True)
        cls.instituto = Lugar(nombre="IES Complutense", direccion="Vía Complutense 19", url_localizacion=URL)
        cls.instituto.save()

    # Inicia sesión como otra persona.
    def como(self, usuario):
        cache.clear()
        self.client.force_login(usuario)

    # Datos de un lugar para los formularios de propuesta (con su prefijo).
    def datos(self, prefijo, **otros):
        base = {"nombre": "CEIP Nuevo", "direccion": "C/ Nueva 1", "url_localizacion": URL, "telefonos": "", "correos": "", "notas": "", "motivo": ""}
        base.update(otros)
        return {f"{prefijo}-{clave}": valor for clave, valor in base.items()}


class PruebasDeMiLugar(PruebaDeLugares):
    """Elegir el lugar y proponer."""

    # Elegir el lugar desde la pantalla y quitarlo.
    def test_elegir_y_quitar(self):
        self.client.post("/lugares/", {"accion": "elegir", "lugar": self.instituto.pk})
        self.assertEqual(LugarDePersona.objects.get(usuario=self.usuario).lugar, self.instituto)
        self.assertContains(self.client.get("/lugares/"), "Vía Complutense 19")
        self.client.post("/lugares/", {"accion": "quitar"})
        self.assertFalse(LugarDePersona.objects.exists())

    # Proponer un lugar nuevo: el superadmin lo acepta, entra en la lista y pasa a ser el de quien lo
    # propuso. Las coordenadas salen de la URL.
    def test_proponer_un_lugar_nuevo(self):
        respuesta = self.client.post("/lugares/", {"accion": "nuevo", **self.datos("nuevo")})
        self.assertContains(respuesta, "Propuesta enviada")
        propuesta = PropuestaDeLugar.objects.get()
        self.como(self.superadmin)
        self.assertContains(self.client.get("/lugares/propuestas/"), "Lugar nuevo: CEIP Nuevo")
        self.client.post("/lugares/propuestas/", {"accion": "aceptar", "propuesta": propuesta.pk, "respuesta": ""})
        nuevo = Lugar.objects.get(nombre="CEIP Nuevo")
        self.assertEqual((nuevo.latitud, nuevo.longitud), (40.482, -3.364))
        self.assertEqual(LugarDePersona.objects.get(usuario=self.usuario).lugar, nuevo)

    # Proponer un cambio en su lugar: el superadmin ve qué cambia; rechazar pide una respuesta; al
    # aceptar, el lugar cambia para todos.
    def test_proponer_un_cambio(self):
        LugarDePersona.objects.create(usuario=self.usuario, lugar=self.instituto)
        datos = self.datos("cambio", nombre="IES Complutense", direccion="Vía Complutense 19", telefonos="918 000 000", motivo="Falta el teléfono")
        self.client.post("/lugares/", {"accion": "cambio", **datos})
        propuesta = PropuestaDeLugar.objects.get()
        self.como(self.superadmin)
        respuesta = self.client.get("/lugares/propuestas/")
        self.assertContains(respuesta, "Cambio en IES Complutense")
        self.assertContains(respuesta, "918 000 000")
        self.assertContains(self.client.post("/lugares/propuestas/", {"accion": "rechazar", "propuesta": propuesta.pk, "respuesta": ""}), "explica por qué")
        self.client.post("/lugares/propuestas/", {"accion": "aceptar", "propuesta": propuesta.pk})
        self.instituto.refresh_from_db()
        self.assertEqual(self.instituto.telefonos, "918 000 000")

    # Solo el superadmin gestiona.
    def test_gestion_solo_superadmin(self):
        for url in ("/lugares/propuestas/", "/lugares/nuevo/", "/lugares/importar/"):
            self.assertEqual(self.client.get(url).status_code, 403, url)


class PruebasDeLoQueSeVe(PruebaDeLugares):
    """Mapa, lista y recuentos según la configuración."""

    # Con 5 personas de la organización en un lugar se ve el número; con 4, no. Las de otra organización
    # no cuentan.
    def test_recuentos_desde_5(self):
        ebro, gru_ebro = crear_organizacion("ORG Ebro", "GRU Ebro")
        for numero in range(4):
            persona = crear_usuario_de_prueba(f"Persona {numero}")
            admitir(persona, self.general)
            LugarDePersona.objects.create(usuario=persona, lugar=self.instituto)
        de_fuera = crear_usuario_de_prueba("De fuera")
        admitir(de_fuera, gru_ebro)
        LugarDePersona.objects.create(usuario=de_fuera, lugar=self.instituto)
        self.assertEqual(recuentos(self.usuario), {})
        LugarDePersona.objects.create(usuario=self.usuario, lugar=self.instituto)
        self.assertEqual(recuentos(self.usuario), {self.instituto.pk: 5})
        self.assertContains(self.client.get(f"/lugares/lugar/{self.instituto.pk}/"), "5 personas trabajan aquí")

    # Si la organización cierra el mapa, sus miembros no lo ven; su admin lo cambia en «Configuración».
    def test_configuracion(self):
        self.assertEqual(self.client.get("/lugares/mapa/").status_code, 200)
        zorro = crear_usuario_de_prueba("Zorro")
        admitir(zorro, self.general)
        nombrar_admin_de_organizacion(zorro, self.tajo)
        self.como(zorro)
        self.client.post("/lugares/configuracion/", {"organizacion": self.tajo.pk, "recuentos_para_miembros": "on"})
        configuracion = ConfiguracionDeLugares.objects.get(organizacion=self.tajo)
        self.assertEqual((configuracion.mapa_para_miembros, configuracion.recuentos_para_miembros), (False, True))
        self.como(self.usuario)
        self.assertContains(self.client.get("/lugares/mapa/"), "Configuración → Lugares", status_code=403)
        self.assertEqual(self.client.get("/lugares/lista/").status_code, 403)

    # Lo que cuestan el mapa y la lista (con más lugares).
    def test_consultas(self):
        def mas():
            for numero in range(3):
                Lugar(nombre=f"Lugar {Lugar.objects.count()}", direccion="C/ X", url_localizacion=URL).save()

        self.comprobar_consultas("/lugares/mapa/", 8, mas)
        self.comprobar_consultas("/lugares/lista/", 7, mas)
        self.comprobar_consultas("/lugares/", 4, mas)


class PruebasDeImportar(PruebaDeLugares):
    """Importar lugares desde una hoja."""

    # Vista previa con un error (falta la URL) que impide confirmar; corregida, se crean los nuevos y el
    # que ya existe no se toca.
    def test_importar(self):
        self.como(self.superadmin)
        cabecera = "Nombre,Dirección,URL de localización,Latitud,Longitud,Teléfonos,Correos,Notas\n"
        mala = cabecera + "Nuevo 1,C/ A,,,,,,\n"
        fichero = io.BytesIO(mala.encode())
        fichero.name = "lugares.csv"
        respuesta = self.client.post("/lugares/importar/", {"accion": "subir", "fichero": fichero})
        self.assertContains(respuesta, "Hay filas con errores")
        buena = cabecera + f"Nuevo 1,C/ A,{URL},,,,,\nIES Complutense,Vía Complutense 19,{URL},,,,,\nNuevo 2,C/ B,https://ejemplo.org,40.1,-3.2,,,\n"
        fichero = io.BytesIO(buena.encode())
        fichero.name = "lugares.csv"
        respuesta = self.client.post("/lugares/importar/", {"accion": "subir", "fichero": fichero})
        self.assertContains(respuesta, "Ya existe")
        respuesta = self.client.post("/lugares/importar/", {"accion": "confirmar"})
        self.assertContains(respuesta, "Importados 2 lugares.")
        self.assertEqual(Lugar.objects.get(nombre="Nuevo 2").latitud, 40.1)
        self.assertEqual(self.client.get("/lugares/importar/?plantilla").status_code, 200)

    # La propuesta, además, avisa al superadmin (con el trabajador de la bandeja).
    def test_aviso_al_superadmin(self):
        from django.apps import apps

        from eventos_sw.servicios import procesar_bandeja

        proponer(self.usuario, {"nombre": "CEIP X", "direccion": "C/ X", "url_localizacion": URL})
        procesar_bandeja()
        Notificacion = apps.get_model("comunicaciones", "Notificacion")
        self.assertTrue(Notificacion.objects.filter(usuario=self.superadmin, texto="Nutria propone un lugar nuevo: CEIP X.").exists())
