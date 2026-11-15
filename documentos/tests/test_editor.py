"""
Pruebas de la conexión con el editor colaborativo en tiempo real (base/editor.py y
base/vistas_del_editor.py), con un documento de verdad: qué permiso lleva el pase de cada persona, que las
llamadas del editor solo valen firmadas, que lo escrito se guarda con la autoría repartida entre quienes han
escrito y que un acta aprobada ya no admite cambios. El servidor del editor no hace falta: sus llamadas se
imitan firmándolas igual que él (editor/src/pases.mjs tiene sus propias pruebas).

Estructura: ORG Tajo (GRU Tajo ⊃ GRU Henares). Lince y Nutria en GRU Henares; Erizo, en otra organización.
"""

import base64
import json
import time

from django.test import override_settings

from base import editor
from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from documentos import servicios
from documentos.models import CambioDeDocumento, Documento, LimitesDeDocumento
from grupos.servicios import admitir, crear_grupo, crear_organizacion

# Consultas de «Escribir» con el editor en tiempo real.
CONSULTAS_DE_ESCRIBIR = 6
# Configuración de un editor de prueba (no hace falta que exista: cerrar_sala no llega y no pasa nada).
EDITOR = {"url": "ws://editor.prueba:1234", "interna": "http://127.0.0.1:9", "app": "asambleas", "secreto": "secreto-de-prueba"}


# Cabeceras firmadas como las pone el servidor del editor (editor/src/pases.mjs, cabecerasFirmadas).
def firmadas(texto, secreto="secreto-de-prueba"):
    hora = str(int(time.time()))
    with override_settings(EDITOR={**EDITOR, "secreto": secreto}):
        firma = editor._base64url(editor._firma(f"{hora}.{texto}"))
    return {"HTTP_X_EDITOR_HORA": hora, "HTTP_X_EDITOR_FIRMA": firma}


@override_settings(EDITOR=EDITOR)
class PruebasDelEditor(PruebaDePantalla):
    """Un orden del día de Lince en GRU Henares, que ve todo el grupo."""

    # Crea la estructura.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.general)
        cls.ebro, cls.gru_ebro = crear_organizacion("ORG Ebro", "GRU Ebro")
        cls.lince, cls.nutria, cls.erizo = (crear_usuario_de_prueba(a) for a in ("Lince", "Nutria", "Erizo"))
        admitir(cls.lince, cls.henares)
        admitir(cls.nutria, cls.henares)
        admitir(cls.erizo, cls.gru_ebro)
        cls.usuario = cls.lince

    # Crea el orden del día.
    def setUp(self):
        super().setUp()
        self.odd = servicios.crear(self.lince, Documento.ODD, "Orden del día", grupo=self.henares, visibilidad="grupo:0")
        self.sala = editor.sala(servicios.ANCLA, self.odd.pk)

    # Lince escribe, Nutria comenta y Erizo no entra. El pase es un JWT con esos datos, firmado y de vida corta.
    def test_pases(self):
        self.assertEqual(editor.pase(self.lince, servicios.ANCLA, self.odd.pk)["permiso"], "escribir")
        self.assertEqual(editor.pase(self.nutria, servicios.ANCLA, self.odd.pk)["permiso"], "comentar")
        self.assertIsNone(editor.pase(self.erizo, servicios.ANCLA, self.odd.pk))
        cabecera, cuerpo, firma = editor.pase(self.lince, servicios.ANCLA, self.odd.pk)["pase"].split(".")
        self.assertEqual(firma, editor._base64url(editor._firma(f"{cabecera}.{cuerpo}")))
        datos = json.loads(base64.urlsafe_b64decode(cuerpo + "=" * (-len(cuerpo) % 4)))
        self.assertEqual((datos["app"], datos["sala"], datos["alias"]), ("asambleas", self.sala, "Lince"))
        self.assertLessEqual(datos["exp"] - time.time(), editor.MINUTOS_DE_PASE * 60)
        self.client.force_login(self.erizo)
        self.assertEqual(self.client.get("/editor/pase/", {"sala": self.sala}).status_code, 403)

    # El pase lleva el formato, el título y los límites que valen (el más estricto de todos los niveles).
    def test_opciones_en_el_pase(self):
        LimitesDeDocumento.objects.create(organizacion=self.tajo, max_escritores=6, max_comentaristas=40)
        LimitesDeDocumento.objects.create(grupo=self.general, max_comentaristas=12)
        LimitesDeDocumento.objects.create(documento=self.odd, max_escritores=3)
        cuerpo = editor.pase(self.lince, servicios.ANCLA, self.odd.pk)["pase"].split(".")[1]
        datos = json.loads(base64.urlsafe_b64decode(cuerpo + "=" * (-len(cuerpo) % 4)))
        self.assertEqual((datos["formato"], datos["titulo"], datos["max_escritores"], datos["max_comentaristas"]), ("markdown", "Orden del día", 3, 12))

    # El texto inicial solo se da con la firma buena.
    def test_texto(self):
        self.client.logout()
        self.assertEqual(self.client.get("/editor/texto/", {"sala": self.sala}).status_code, 403)
        self.assertEqual(self.client.get("/editor/texto/", {"sala": self.sala}, **firmadas(self.sala, "otro")).status_code, 403)
        respuesta = self.client.get("/editor/texto/", {"sala": self.sala}, **firmadas(self.sala)).json()
        self.assertEqual(respuesta, {"texto": self.odd.texto, "version": self.odd.version})

    # Lo escrito por dos personas se guarda con las dos en la autoría y en el registro; aprobado, ya no.
    def test_guardado(self):
        cuerpo = json.dumps({"sala": self.sala, "texto": self.odd.texto + "\nUn punto nuevo\n", "alias": ["Lince", "Nutria"], "version": 1})
        respuesta = self.client.post("/editor/guardado/", cuerpo, content_type="application/json", **firmadas(cuerpo))
        self.assertEqual(respuesta.status_code, 200)
        self.odd.refresh_from_db()
        self.assertEqual(respuesta.json()["version"], self.odd.version)
        self.assertEqual(self.odd.autorias[-1], ["Lince", "Nutria"])
        self.assertEqual(CambioDeDocumento.objects.filter(documento=self.odd).first().alias, "Lince, Nutria")
        self.assertEqual(self.client.post("/editor/guardado/", cuerpo, content_type="application/json").status_code, 403)
        servicios.aprobar(self.lince, self.odd)
        respuesta = self.client.post("/editor/guardado/", cuerpo, content_type="application/json", **firmadas(cuerpo))
        self.assertEqual(respuesta.status_code, 409)

    # Con editor, «Escribir» pinta la isla con su sala y su pase, sin el formulario del texto; Nutria la ve
    # de solo lectura. Cuesta lo mismo que sin editor.
    def test_pantalla(self):
        respuesta = self.client.get(f"/documentos/{self.odd.pk}/escribir/")
        self.assertContains(respuesta, f'data-sala="asambleas/{self.sala}"')
        self.assertNotContains(respuesta, 'name="texto"')
        self.client.force_login(self.nutria)
        self.assertContains(self.client.get(f"/documentos/{self.odd.pk}/escribir/"), "Solo lectura")
        self.assertContains(self.client.get(f"/documentos/{self.odd.pk}/"), "Seguir en directo")
        self.client.force_login(self.lince)

        # Un cambio más en el registro (no debe costar más consultas).
        def mas():
            servicios.guardar_desde_editor(self.odd.pk, self.odd.texto + f"\nOtro {CambioDeDocumento.objects.count()}\n", ["Lince"])

        self.comprobar_consultas(f"/documentos/{self.odd.pk}/escribir/", CONSULTAS_DE_ESCRIBIR, mas)
