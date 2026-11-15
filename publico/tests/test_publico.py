"""
Pruebas de la portada pública y las miniwebs (docs/diseno.md, apartado 15): lo público se ve sin sesión y
lo demás no; una página de un grupo la ven el grupo y lo que cuelga de él (no los de encima ni otras
organizaciones); la relación de publicación y consumo; publicar avisa; las novedades; las imágenes; quién
gestiona; y lo que cuesta cada pantalla.

Estructura: ORG Tajo (GRU Tajo ⊃ GRU Henares ⊃ GRU Sorbe) y ORG Ebro (GRU Ebro ⊃ GRU Arga). Lince administra
GRU Henares; Nutria está en GRU Henares; Garza, en GRU Sorbe; Tejón, en GRU Tajo; Zorro administra GRU Arga.
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
from eventos_sw.servicios import procesar_bandeja
from grupos.models import Pertenencia
from grupos.servicios import admitir, crear_grupo, crear_organizacion
from publico import servicios
from publico.models import Pagina, RelacionDeConsumo

# Carpeta temporal para las imágenes de las pruebas (se borra al terminar, en tearDownModule).
CARPETA = tempfile.mkdtemp(prefix="pruebas-publico-")


# Al terminar todas las pruebas de este fichero: borra la carpeta temporal.
def tearDownModule():
    shutil.rmtree(CARPETA, ignore_errors=True)


# Una imagen PNG de verdad, pequeña.
def png():
    memoria = io.BytesIO()
    Image.new("RGB", (4, 4), "teal").save(memoria, "PNG")
    return memoria.getvalue()


@override_settings(MEDIA_ROOT=CARPETA)
class PruebaDePublico(PruebaDePantalla):
    """Base con la estructura del principio del fichero."""

    # Crea la estructura.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.general)
        cls.sorbe = crear_grupo(cls.tajo, "GRU Sorbe", padre=cls.henares)
        cls.ebro, cls.gru_ebro = crear_organizacion("ORG Ebro", "GRU Ebro")
        cls.arga = crear_grupo(cls.ebro, "GRU Arga", padre=cls.gru_ebro)
        cls.lince = crear_usuario_de_prueba("Lince")
        cls.nutria = crear_usuario_de_prueba("Nutria")
        cls.garza = crear_usuario_de_prueba("Garza")
        cls.tejon = crear_usuario_de_prueba("Tejon")
        cls.zorro = crear_usuario_de_prueba("Zorro")
        cls.superadmin = crear_usuario_de_prueba("superadmin", es_superadmin=True)
        admitir(cls.lince, cls.henares, rol=Pertenencia.ADMIN_GRUPO)
        admitir(cls.nutria, cls.henares, es_base=True)
        admitir(cls.garza, cls.sorbe)
        admitir(cls.tejon, cls.general)
        admitir(cls.zorro, cls.arga, rol=Pertenencia.ADMIN_GRUPO)
        cls.usuario = cls.nutria

    # Inicia sesión como otra persona.
    def como(self, persona):
        self.client.force_login(persona)

    # Crea, escribe y publica una página (función de ayuda).
    def publicada(self, usuario, ambito, titulo, texto="## Hola", publica=False):
        pagina = servicios.crear(usuario, ambito, titulo, publica=publica)
        pagina = servicios.guardar(usuario, pagina, texto, pagina.version)
        return servicios.publicar(usuario, pagina)


class PruebasDeLaPortada(PruebaDePublico):
    """La portada pública, sin sesión."""

    # Sin sesión: «/» lleva a la portada; se ven las páginas públicas publicadas (no los borradores ni las
    # internas), el botón «Entrar» y la lista de organizaciones con portada.
    def test_sin_sesion(self):
        self.publicada(self.superadmin, "p", "Bienvenida", "## Bienvenida a la plataforma")
        servicios.crear(self.superadmin, "p", "Borrador oculto")
        self.publicada(self.superadmin, f"o{self.tajo.pk}", "Quiénes somos", "## Somos ORG Tajo", publica=True)
        interna = self.publicada(self.superadmin, f"o{self.tajo.pk}", "Normas", "## Solo dentro")
        self.client.logout()
        self.assertRedirects(self.client.get("/"), "/portada/")
        respuesta = self.client.get("/portada/")
        for texto in ("Bienvenida a la plataforma", "Entrar", "ORG Tajo"):
            self.assertContains(respuesta, texto)
        self.assertNotContains(respuesta, "Borrador oculto")
        self.assertContains(self.client.get(f"/o/{self.tajo.pk}/"), "Somos ORG Tajo")
        self.assertEqual(self.client.get(f"/o/{self.ebro.pk}/").status_code, 404)
        # Lo interno, sin sesión, nunca.
        self.assertEqual(self.client.get(f"/o/{self.tajo.pk}/{interna.pk}/").status_code, 404)
        self.assertRedirects(self.client.get(f"/webs/pagina/{interna.pk}/"), f"/cuenta/entrar/?next=/webs/pagina/{interna.pk}/", fetch_redirect_response=False)

    # El texto escrito a mano no cuela HTML: un «<script>» sale como texto.
    def test_html_seguro(self):
        pagina = self.publicada(self.superadmin, "p", "Prueba", "<script>alert(1)</script>\n\n[x](javascript:alert(1))")
        self.assertNotIn("<script>", pagina.html)
        self.assertNotIn("javascript:", pagina.html)

    # Una página de grupo nunca es pública; la portada cuesta pocas consultas, haya las páginas que haya.
    def test_grupo_no_publico_y_consultas(self):
        pagina = servicios.crear(self.lince, f"g{self.henares.pk}", "Huerta", publica=True)
        self.assertFalse(pagina.publica)
        self.publicada(self.superadmin, "p", "Uno")
        self.client.logout()

        # Añade una página de la plataforma y otra pública de ORG Tajo.
        def mas():
            self.publicada(self.superadmin, "p", "Otra")
            self.publicada(self.superadmin, f"o{self.tajo.pk}", "Pública", publica=True)

        self.comprobar_consultas("/portada/", 2, mas)


class PruebasDeQuienVe(PruebaDePublico):
    """Las miniwebs: de abuelo hacia abajo, y publicación y consumo."""

    # La página de GRU Henares la ven Nutria (GRU Henares) y Garza (GRU Sorbe, que cuelga de él); no Tejón
    # (GRU Tajo, por encima) ni Zorro (otra organización).
    def test_de_arriba_abajo(self):
        pagina = self.publicada(self.lince, f"g{self.henares.pk}", "Calendario de la huerta", "## Habas en noviembre")
        url = f"/webs/pagina/{pagina.pk}/"
        for persona, codigo in ((self.nutria, 200), (self.garza, 200), (self.tejon, 404), (self.zorro, 404)):
            with self.subTest(persona=persona):
                self.como(persona)
                self.assertEqual(self.client.get(url).status_code, codigo)
        self.como(self.garza)
        respuesta = self.client.get(url)
        self.assertContains(respuesta, "Habas en noviembre")
        # La barra de camino lleva de la organización al grupo.
        for texto in ("ORG Tajo", "GRU Tajo", "GRU Henares", "Calendario de la huerta"):
            self.assertContains(respuesta, texto)

    # GRU Arga (de ORG Ebro) propone publicar para GRU Henares; hasta que Lince lo acepta, Nutria no ve su
    # página; después sí (en «Grupos de actividad»), y Garza también (cuelga de GRU Henares). Al cortarla, ya no.
    def test_publicacion_y_consumo(self):
        taller = self.publicada(self.zorro, f"g{self.arga.pk}", "Taller de bicis", "## Martes")
        relacion = servicios.proponer_relacion(self.zorro, self.arga, self.henares, "Para la gente de la huerta")
        url = f"/webs/pagina/{taller.pk}/"
        self.assertEqual(self.client.get(url).status_code, 404)
        self.como(self.nutria)
        with self.assertRaises(Exception):
            servicios.aceptar_relacion(self.nutria, relacion)
        self.como(self.lince)
        self.client.post("/webs/relaciones/", {"accion": "aceptar", "relacion": relacion.pk})
        relacion.refresh_from_db()
        self.assertEqual(relacion.estado, RelacionDeConsumo.ACEPTADA)
        for persona in (self.nutria, self.garza):
            self.como(persona)
            respuesta = self.client.get(url)
            self.assertContains(respuesta, "Grupos de actividad")
            self.assertContains(respuesta, "Martes")
        self.como(self.zorro)
        self.client.post("/webs/relaciones/", {"accion": "cortar", "relacion": relacion.pk})
        self.como(self.nutria)
        self.assertEqual(self.client.get(url).status_code, 404)

    # Sin páginas que ver, «🌐 Webs» lo dice; el botón sale en la cabecera.
    def test_sin_webs(self):
        self.assertContains(self.client.get("/webs/"), "Aún no hay webs publicadas")
        self.assertContains(self.client.get("/"), 'data-cabecera="publico.webs"')


class PruebasDeGestionar(PruebaDePublico):
    """Crear, escribir, publicar, imágenes, avisos y novedades."""

    # Lince crea, escribe y publica desde las pantallas; la primera publicación avisa a Nutria y a Garza
    # (no a Lince) y les sale en Novedades (con su número en el botón, que vuelve a cero al mirarlas).
    def test_publicar_avisa_y_novedades(self):
        self.como(self.lince)
        self.client.post("/webs/gestionar/", {"ambito": f"g{self.henares.pk}", "titulo": "Huerta", "orden": 1})
        pagina = Pagina.objects.get()
        self.client.post(f"/webs/gestionar/{pagina.pk}/escribir/?sin_directo=1", {"texto": "## Huerta comunitaria", "version": pagina.version})
        self.como(self.nutria)
        self.assertEqual(self.client.get(f"/webs/pagina/{pagina.pk}/").status_code, 404)
        self.como(self.lince)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(f"/webs/gestionar/{pagina.pk}/", {"accion": "publicar"})
            procesar_bandeja()
        Notificacion = apps.get_model("comunicaciones", "Notificacion")
        avisados = set(Notificacion.objects.filter(tipo="publico.publicada").values_list("usuario__alias", flat=True))
        self.assertEqual(avisados, {"Nutria", "Garza"})
        cache.clear()
        self.assertEqual(servicios.novedades_sin_ver(self.nutria), 1)
        self.como(self.nutria)
        self.assertContains(self.client.get("/webs/novedades/"), "Huerta")
        self.assertEqual(servicios.novedades_sin_ver(self.nutria), 0)

    # Nutria no gestiona: ni la pantalla de páginas ni la de una página.
    def test_quien_gestiona(self):
        pagina = servicios.crear(self.lince, f"g{self.henares.pk}", "Huerta")
        self.assertEqual(self.client.get("/webs/gestionar/").status_code, 403)
        self.assertEqual(self.client.get(f"/webs/gestionar/{pagina.pk}/").status_code, 403)
        self.assertNotIn(f"g{self.henares.pk}", dict(servicios.ambitos_de(self.nutria)))

    # Una imagen en una página pública se ve sin sesión; en una interna, no.
    def test_imagenes(self):
        publica = self.publicada(self.superadmin, "p", "Portada")
        interna = self.publicada(self.lince, f"g{self.henares.pk}", "Huerta")
        foto = servicios.subir_imagen(self.superadmin, publica, SimpleUploadedFile("foto.png", png()))
        otra = servicios.subir_imagen(self.lince, interna, SimpleUploadedFile("huerta.png", png()))
        with self.assertRaisesMessage(Exception, "Solo imágenes"):
            servicios.subir_imagen(self.lince, interna, SimpleUploadedFile("x.svg", b"<svg/>"))
        self.assertEqual(self.client.get(f"/webs/imagen/{otra.pk}/").status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get(f"/webs/imagen/{foto.pk}/").status_code, 200)
        self.assertEqual(self.client.get(f"/webs/imagen/{otra.pk}/").status_code, 404)

    # Las pantallas no crecen con las páginas ni con los grupos.
    def test_consultas(self):
        pagina = self.publicada(self.lince, f"g{self.henares.pk}", "Huerta")
        veces = []

        # Añade un subgrupo con web y otra página (nombres distintos cada vez).
        def mas():
            veces.append(1)
            sub = crear_grupo(self.tajo, f"GRU Badiel {len(veces)}", padre=self.henares)
            self.publicada(self.superadmin, f"g{sub.pk}", f"Sub {len(veces)}")
            self.publicada(self.lince, f"g{self.henares.pk}", f"Otra {len(veces)}")

        self.comprobar_consultas(f"/webs/pagina/{pagina.pk}/", 9, mas)
        self.comprobar_consultas(f"/webs/grupo/{self.henares.pk}/", 10, mas)
        self.comprobar_consultas("/webs/jerarquia/", 8, mas)
        self.comprobar_consultas("/webs/novedades/", 14, mas)
        self.como(self.lince)
        self.comprobar_consultas("/webs/gestionar/", 4, mas)
        self.comprobar_consultas(f"/webs/gestionar/{pagina.pk}/", 4, mas)
