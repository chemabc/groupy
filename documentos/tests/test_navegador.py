"""
Pruebas en un navegador de verdad (ver base/pruebas_navegador.py) de lo que lleva JavaScript en
«Participación»: la vista previa de un documento, que se pone al día mientras se escribe (htmx); en una
consulta nueva, la fecha de publicación y el aviso de «tiempo real», que salen según lo elegido (Alpine);
y el editor colaborativo en tiempo real con dos personas a la vez (isla «editorEnVivo» y editor/).
"""

import json
import os
import socket
import subprocess
import tempfile
import time
import unittest

from django.conf import settings

from base.pruebas import crear_usuario_de_prueba
from base.pruebas_navegador import PruebaEnElNavegador
from documentos import servicios
from documentos.models import Documento
from grupos.models import Pertenencia
from grupos.servicios import admitir, crear_organizacion


class PruebasDeParticipacionEnElNavegador(PruebaEnElNavegador):
    """El usuario de la prueba administra GRU Tajo."""

    # Crea la organización y lo hace admin de su grupo.
    def preparar(self):
        _tajo, self.grupo = crear_organizacion("ORG Tajo", "GRU Tajo")
        admitir(self.usuario, self.grupo, rol=Pertenencia.ADMIN_GRUPO)

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

    # Arranca el servidor del editor en un puerto libre, con esta plataforma como única aplicación.
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        carpeta = settings.BASE_DIR / "editor"
        if not (carpeta / "node_modules").exists():
            super().tearDownClass()
            raise unittest.SkipTest("El editor no está instalado (npm install en editor/).")
        subprocess.run(["npm", "run", "construir"], cwd=carpeta, check=True, capture_output=True)
        with socket.socket() as hueco:
            hueco.bind(("127.0.0.1", 0))
            cls.puerto = hueco.getsockname()[1]
        aplicaciones = {"asambleas": {"secreto": "secreto-de-prueba", "url": f"{cls.live_server_url}/editor"}}
        entorno = {**os.environ, "EDITOR_PUERTO": str(cls.puerto), "EDITOR_APLICACIONES": json.dumps(aplicaciones), "EDITOR_DATOS": tempfile.mkdtemp()}
        cls.editor = subprocess.Popen(["node", "src/servidor.mjs"], cwd=carpeta, env=entorno, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        cls.editor.stdout.readline()  # espera a «Editor colaborativo en marcha…»

    # Para el servidor del editor.
    @classmethod
    def tearDownClass(cls):
        cls.editor.terminate()
        cls.editor.wait()
        super().tearDownClass()

    # Espera a que el cuadro del editor de una pestaña tenga un texto.
    def esperar_texto(self, pagina, texto):
        pagina.locator(f".cm-content:has-text('{texto}')").wait_for(timeout=10000)

    # Las dos escriben, cada una ve lo de la otra y la plataforma lo guarda con las dos en la autoría.
    def test_dos_personas_a_la_vez(self):
        url = f"ws://127.0.0.1:{self.puerto}"
        with self.settings(EDITOR={"url": url, "interna": url.replace("ws", "http"), "app": "asambleas", "secreto": "secreto-de-prueba"}):
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
            primera.locator("#vista-previa:has-text('Y los jueves')").wait_for(timeout=10000)
            for _ in range(60):
                documento.refresh_from_db()
                if "Y los jueves" in documento.texto:
                    break
                time.sleep(0.25)
            self.assertIn("Regar los martes. Y los jueves.", documento.texto)
            self.assertTrue({self.usuario.alias, "Nutria"} <= set(sum(documento.autorias, [])))
            self.assertEqual(self.errores, [])
