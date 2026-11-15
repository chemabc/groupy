"""
Pruebas en un navegador de verdad (ver base/pruebas_navegador.py) de lo que lleva JavaScript en
«Participación»: el rango de fechas de la lista de documentos (tabla filtrable común); la vista previa de un documento, que se pone al día mientras se escribe (htmx); en una
consulta nueva, la fecha de publicación y el aviso de «tiempo real», que salen según lo elegido (Alpine);
y el editor colaborativo en tiempo real con dos personas a la vez (isla «editorEnVivo» y editor/).
"""

import base64
import json
import os
import socket
import subprocess
import tempfile
import time
import unittest

from django.conf import settings

from base import editor
from base.pruebas import crear_usuario_de_prueba
from base.pruebas_navegador import PruebaEnElNavegador
from documentos import servicios
from documentos.models import Documento
from grupos.models import AdminDeOrganizacion, Pertenencia
from grupos.servicios import admitir, crear_organizacion


class PruebasDeParticipacionEnElNavegador(PruebaEnElNavegador):
    """El usuario de la prueba administra GRU Tajo."""

    # Crea la organización y lo hace admin de su grupo.
    def preparar(self):
        _tajo, self.grupo = crear_organizacion("ORG Tajo", "GRU Tajo")
        admitir(self.usuario, self.grupo, rol=Pertenencia.ADMIN_GRUPO)

    # La lista de documentos con rango de fechas: al poner «Desde» después del último cambio de uno, se
    # esconde; al quitarlo, vuelve (se filtra en el navegador, sin recargar).
    def test_rango_de_fechas(self):
        self.preparar()
        viejo = servicios.crear(self.usuario, Documento.LIBRE, "Notas viejas", grupo=self.grupo, visibilidad="grupo:0")
        servicios.crear(self.usuario, Documento.LIBRE, "Notas nuevas", grupo=self.grupo, visibilidad="grupo:0")
        Documento.objects.filter(pk=viejo.pk).update(actualizado="2025-01-15T10:00:00Z")
        self.abrir("/documentos/")
        desde = self.pagina.get_by_label("Último cambio desde")
        desde.fill("2025-06-01")
        self.pagina.get_by_text("Notas viejas").wait_for(state="hidden")
        self.assertTrue(self.pagina.get_by_text("Notas nuevas").is_visible())
        self.pagina.get_by_label("Último cambio hasta").fill("2025-02-01")
        self.pagina.get_by_text("Notas nuevas").wait_for(state="hidden")
        desde.fill("")
        self.pagina.get_by_label("Último cambio hasta").fill("")
        self.pagina.get_by_text("Notas viejas").wait_for()
        self.assertEqual(self.errores, [])

    # Al escribir, la vista previa de la derecha muestra el texto convertido, sin guardar ni recargar.
    def test_vista_previa(self):
        self.preparar()
        documento = servicios.crear(self.usuario, Documento.LIBRE, "Notas", grupo=self.grupo, visibilidad="grupo:0")
        self.abrir(f"/documentos/{documento.pk}/escribir/")
        cuadro = self.pagina.locator('textarea[name="texto"]')
        cuadro.fill("## Huerto\n\n- **Regar** los martes")
        self.pagina.locator("#vista-previa h2:has-text('Huerto')").wait_for()
        self.assertEqual(self.pagina.locator("#vista-previa strong").inner_text(), "Regar")
        self.assertEqual(self.errores, [])

    # En una consulta nueva, «En una fecha» enseña la fecha de publicación y «En tiempo real», el aviso.
    def test_consulta_nueva(self):
        self.preparar()
        self.abrir("/consultas/nueva/")
        publicar = self.pagina.locator('input[name="publicar_el"]')
        self.assertFalse(publicar.is_visible())
        self.pagina.locator('select[name="resultados"]').select_option("fecha")
        publicar.wait_for(state="visible")
        self.pagina.locator('select[name="resultados"]').select_option("tiempo_real")
        self.pagina.get_by_text("influye en quien aún no ha votado.").last.wait_for(state="visible")
        self.assertEqual(self.errores, [])


class PruebasDelEditorEnVivoEnElNavegador(PruebaEnElNavegador):
    """
    El editor colaborativo en tiempo real de verdad: arranca el servidor del editor (editor/, en Node) contra
    el servidor de pruebas de Django, y dos personas con la redacción escriben a la vez en dos navegadores.
    Lo que escribe cada una aparece en el de la otra y, unos segundos después, queda guardado en la
    plataforma con las dos en la autoría. Se salta si el editor no está instalado (npm install en editor/).
    """

    # Comprueba que el editor está instalado y construye su cliente (una vez para las dos pruebas).
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.carpeta = settings.BASE_DIR / "editor"
        if not (cls.carpeta / "node_modules").exists():
            super().tearDownClass()
            raise unittest.SkipTest("El editor no está instalado (npm install en editor/).")
        subprocess.run(["npm", "run", "construir"], cwd=cls.carpeta, check=True, capture_output=True)

    # Arranca un servidor del editor para cada prueba, en un puerto libre y con su carpeta de datos vacía
    # (los números de los documentos se repiten entre pruebas y el editor recordaría el texto de la otra).
    def setUp(self):
        super().setUp()
        with socket.socket() as hueco:
            hueco.bind(("127.0.0.1", 0))
            self.puerto = hueco.getsockname()[1]
        aplicaciones = {"asambleas": {"secreto": "secreto-de-prueba", "url": f"{self.live_server_url}/editor"}}
        entorno = {
            **os.environ, "EDITOR_PUERTO": str(self.puerto), "EDITOR_APLICACIONES": json.dumps(aplicaciones), "EDITOR_DATOS": tempfile.mkdtemp(),
            "EDITOR_CLAVE": base64.b64encode(os.urandom(32)).decode(),
        }
        self.editor = subprocess.Popen(["node", "src/servidor.mjs"], cwd=self.carpeta, env=entorno, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.editor.stdout.readline()  # espera a «Editor colaborativo en marcha…»
        self.addCleanup(self.parar_editor)

    # Para el servidor del editor de la prueba.
    def parar_editor(self):
        self.editor.terminate()
        self.editor.wait()

    # La configuración del editor de esta prueba (para self.settings).
    def configuracion(self):
        url = f"ws://127.0.0.1:{self.puerto}"
        return {"url": url, "interna": url.replace("ws", "http"), "app": "asambleas", "secreto": "secreto-de-prueba"}

    # Espera a que el cuadro del editor de una pestaña tenga un texto.
    def esperar_texto(self, pagina, texto):
        pagina.locator(f".cm-content:has-text('{texto}')").wait_for(timeout=10000)

    # Las dos escriben, cada una ve lo de la otra y la plataforma lo guarda con las dos en la autoría; la
    # vista Typst se enciende y se apaga; y un comentario de una le sale a la otra, con su bocadillo.
    def test_dos_personas_a_la_vez(self):
        with self.settings(EDITOR=self.configuracion()):
            _tajo, grupo = crear_organizacion("ORG Tajo", "GRU Tajo")
            admitir(self.usuario, grupo, rol=Pertenencia.ADMIN_GRUPO)
            nutria = crear_usuario_de_prueba("Nutria")
            admitir(nutria, grupo)
            documento = servicios.crear(self.usuario, Documento.LIBRE, "Notas", grupo=grupo, visibilidad="grupo:0", texto="## Huerto\n")
            servicios.dar_redaccion(self.usuario, documento, nutria)
            primera = self.pagina
            self.abrir(f"/documentos/{documento.pk}/escribir/")
            self.pagina = self.pestana_nueva()
            self.entrar("Nutria")
            self.abrir(f"/documentos/{documento.pk}/escribir/")
            segunda = self.pagina
            self.esperar_texto(primera, "Huerto")
            self.esperar_texto(segunda, "Huerto")
            primera.get_by_text("En directo").wait_for()
            primera.locator(".cm-content").click()
            primera.keyboard.press("Control+End")
            primera.keyboard.type("Regar los martes. ")
            self.esperar_texto(segunda, "Regar los martes")
            segunda.locator(".cm-content").click()
            segunda.keyboard.press("Control+End")
            segunda.keyboard.type("Y los jueves.")
            self.esperar_texto(primera, "Y los jueves")
            # La vista Typst: apagada no hay panel; al encenderla sale el resultado compilado.
            self.assertFalse(primera.locator(".ec-panel").is_visible())
            primera.get_by_role("button", name="Vista Typst").click()
            primera.locator(".ec-panel img[src^='blob:']").wait_for(timeout=15000)
            primera.get_by_text("Al día").wait_for(timeout=10000)
            primera.get_by_role("button", name="Vista Typst").click()
            self.assertFalse(primera.locator(".ec-panel").is_visible())
            # Un comentario: Nutria selecciona «jueves», comenta y a Lince le sale resaltado; al pulsarlo, el bocadillo.
            segunda.locator(".cm-content").click()
            segunda.keyboard.press("Control+End")
            for _ in range(len("jueves.")):
                segunda.keyboard.press("Shift+ArrowLeft")
            segunda.get_by_role("button", name="💬 Comentar").click()
            segunda.locator(".ec-burbuja textarea").fill("¿Y los viernes?")
            segunda.locator(".ec-burbuja").get_by_role("button", name="Comentar").click()
            primera.locator(".ec-comentado").first.wait_for(timeout=10000)
            primera.locator(".ec-comentado").first.click()
            primera.locator(".ec-burbuja:has-text('¿Y los viernes?')").wait_for(timeout=5000)
            for _ in range(60):
                documento.refresh_from_db()
                if "Y los jueves" in documento.texto:
                    break
                time.sleep(0.25)
            self.assertIn("Regar los martes. Y los jueves.", documento.texto)
            self.assertTrue({self.usuario.alias, "Nutria"} <= set(sum(documento.autorias, [])))
            self.assertEqual(self.errores, [])

    # La biblioteca: quien administra ORG Tajo crea una carpeta y una plantilla (con su vista previa) y un
    # fragmento; después, en un documento vacío, elige la plantilla (el texto de partida aparece) y mete el
    # fragmento con un clic desde el cajón.
    def test_biblioteca(self):
        with self.settings(EDITOR=self.configuracion()):
            tajo, grupo = crear_organizacion("ORG Tajo", "GRU Tajo")
            admitir(self.usuario, grupo)
            AdminDeOrganizacion.objects.create(usuario=self.usuario, organizacion=tajo)
            # Una carpeta y una plantilla con aspecto y texto de partida.
            self.abrir("/documentos/plantillas/")
            pagina = self.pagina
            pagina.get_by_role("button", name="📁 Nueva carpeta").click()
            pagina.get_by_label("Nombre").fill("Actas")
            self.assertEqual(pagina.get_by_label("De quién es (quién puede cambiarlo)").input_value(), f"asambleas:o{tajo.pk}")
            pagina.get_by_role("button", name="Guardar").click()
            pagina.locator("summary:has-text('Actas')").wait_for()
            pagina.get_by_role("button", name="＋ Nueva plantilla").click()
            pagina.get_by_label("Nombre").fill("Acta de Tajo")
            pagina.get_by_label("Aspecto", exact=False).fill("#set text(size: 12pt)")
            pagina.get_by_role("textbox", name="Texto de partida").fill("## Asistentes\n")
            pagina.get_by_role("button", name="Guardar").click()
            pagina.locator("button.ec-hoja:has-text('Acta de Tajo')").wait_for()
            pagina.get_by_role("button", name="Previsualizar").click()
            pagina.locator("img.ec-previa[src^='blob:']").wait_for(timeout=15000)
            # Un fragmento, solo de quien lo crea (dentro de una carpeta de la organización).
            self.abrir("/documentos/fragmentos/")
            pagina = self.pagina
            pagina.get_by_role("button", name="📁 Nueva carpeta").click()
            pagina.get_by_label("Nombre").fill("Actas")
            pagina.get_by_role("button", name="Guardar").click()
            pagina.get_by_role("button", name="＋ Nuevo fragmento").click()
            pagina.get_by_label("Nombre").fill("Ruegos")
            self.assertEqual(pagina.get_by_label("De quién es (quién puede cambiarlo)").input_value(), f"asambleas:u:{editor.id_para_editor(self.usuario)}")
            pagina.get_by_label("Texto, código o las dos cosas").fill("## Ruegos y preguntas")
            pagina.get_by_role("button", name="Guardar").click()
            pagina.locator("button.ec-hoja:has-text('Ruegos')").wait_for()
            # En un documento vacío: la plantilla pone su texto de partida y el fragmento se mete con un clic.
            documento = servicios.crear(self.usuario, Documento.LIBRE, "Acta", grupo=grupo, visibilidad="grupo:0", texto="")
            self.abrir(f"/documentos/{documento.pk}/escribir/")
            pagina = self.pagina
            pagina.get_by_text("En directo").wait_for()
            pagina.locator("select[aria-label='Plantilla'] option:has-text('Acta de Tajo')").wait_for(state="attached")
            pagina.get_by_label("Plantilla", exact=True).select_option(label="Acta de Tajo")
            self.esperar_texto(pagina, "Asistentes")
            pagina.get_by_role("button", name="📚 Fragmentos e imágenes").click()
            pagina.locator(".ec-cajon button.ec-hoja:has-text('Ruegos')").click()
            self.esperar_texto(pagina, "Ruegos y preguntas")
            self.assertEqual(self.errores, [])
