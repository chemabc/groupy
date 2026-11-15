"""
Pruebas de archivos, enlaces y papelera (docs/diseno.md, apartado 13.4): qué tipos se admiten (nunca de
Microsoft), que el contenido sea lo que dice su extensión, el antivirus (con un ClamAV de mentira), las
versiones, el espacio de cada organización, quién ve y descarga, eliminar y recuperar, lo congelado por una
votación abierta y los documentos de las tareas en la ficha de su proyecto. También el rango de fechas de
la tabla filtrable común.

Lo de otros módulos (proyectos, tareas, debates, consultas) se crea con apps.get_model, sin importarlos.

Estructura: ORG Tajo (GRU Tajo ⊃ GRU Henares). Lince (admin de GRU Henares) y Nutria están en GRU
Henares; Erizo, en otra organización.
"""

import io
import shutil
import socketserver
import tempfile
import threading
import zipfile
from datetime import date, timedelta

from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from audiencias.selector import audiencia_de
from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from base.tablas import FuenteDeLista
from documentos import archivos, servicios
from documentos.models import Documento, EspacioParaArchivos, VersionDeArchivo
from grupos.models import Pertenencia
from grupos.servicios import admitir, crear_grupo, crear_organizacion
from tipologias.servicios import crear_tipologia

# Un PDF muy pequeño pero válido.
PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"
# Carpeta temporal para los ficheros de las pruebas (se borra al terminar, en tearDownModule).
CARPETA = tempfile.mkdtemp(prefix="pruebas-archivos-")


# Al terminar todas las pruebas de este fichero: borra la carpeta temporal de los ficheros.
def tearDownModule():
    shutil.rmtree(CARPETA, ignore_errors=True)


# Un documento abierto de texto (.odt) mínimo: un zip cuyo primer fichero, «mimetype», dice qué es.
def odt():
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as zip_:
        zip_.writestr("mimetype", "application/vnd.oasis.opendocument.text")
        zip_.writestr("content.xml", "<office:document-content/>")
    return memoria.getvalue()


class PruebasDeComprobar(SimpleTestCase):
    """Qué archivos pasan y cuáles no (sin base de datos ni antivirus)."""

    # Formatos de Microsoft: el aviso que explica cómo guardarlo; un tipo raro: otro aviso; un PDF falso o
    # un texto con bytes nulos: no; un PDF, un .odt y un texto de verdad: sí.
    @override_settings(ANTIVIRUS="")
    def test_tipos(self):
        for nombre in ("acta.docx", "cuentas.XLSX", "charla.pptx", "viejo.doc"):
            with self.assertRaisesMessage(ValidationError, "No se admiten formatos de Microsoft"):
                archivos.comprobar(SimpleUploadedFile(nombre, b"lo que sea"))
        with self.assertRaisesMessage(ValidationError, "no se admite"):
            archivos.comprobar(SimpleUploadedFile("programa.exe", b"MZ"))
        with self.assertRaisesMessage(ValidationError, "no parece"):
            archivos.comprobar(SimpleUploadedFile("informe.pdf", b"MZ\x90\x00programa"))
        with self.assertRaisesMessage(ValidationError, "no parece"):
            archivos.comprobar(SimpleUploadedFile("notas.txt", b"hola\x00mundo"))
        self.assertEqual(archivos.comprobar(SimpleUploadedFile("Informe.PDF", PDF)).extension, "pdf")
        self.assertEqual(archivos.comprobar(SimpleUploadedFile("acta.odt", odt())).revision, "sin_revisar")
        self.assertEqual(archivos.comprobar(SimpleUploadedFile("datos.csv", "año;cuota\n2026;5".encode())).tipo_mime, "text/csv; charset=utf-8")

    # Más de 20 MB: no.
    @override_settings(ANTIVIRUS="")
    def test_tamano(self):
        grande = SimpleUploadedFile("grande.pdf", PDF + b"0" * archivos.TAMANO_MAXIMO)
        with self.assertRaisesMessage(ValidationError, "como mucho, 20 MB"):
            archivos.comprobar(grande)


class ClamavDeMentira(socketserver.BaseRequestHandler):
    """Un ClamAV de mentira: lee la orden INSTREAM y responde que hay virus si ve la palabra «VIRUS»."""

    # Lee los trozos (tamaño en 4 bytes y contenido) hasta el de tamaño cero, y responde.
    def handle(self):
        recibido = b""
        while not recibido.endswith(b"\0\0\0\0"):
            parte = self.request.recv(65536)
            if not parte:
                break
            recibido += parte
        respuesta = b"stream: Eicar-Test-Signature FOUND\0" if b"VIRUS" in recibido else b"stream: OK\0"
        self.request.sendall(respuesta)


class PruebasDelAntivirus(SimpleTestCase):
    """El antivirus, con un ClamAV de mentira en un puerto libre."""

    # Arranca el ClamAV de mentira en un hilo.
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.servidor = socketserver.TCPServer(("127.0.0.1", 0), ClamavDeMentira)
        threading.Thread(target=cls.servidor.serve_forever, daemon=True).start()
        cls.direccion = f"127.0.0.1:{cls.servidor.server_address[1]}"

    # Lo para al terminar.
    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()
        super().tearDownClass()

    # Limpio: «limpio»; con virus: no se guarda; sin respuesta: tampoco.
    def test_revisar(self):
        with override_settings(ANTIVIRUS=self.direccion):
            self.assertEqual(archivos.revisar_con_el_antivirus(PDF), "limpio")
            with self.assertRaisesMessage(ValidationError, "ha encontrado un virus"):
                archivos.revisar_con_el_antivirus(PDF + b"VIRUS")
        with override_settings(ANTIVIRUS="127.0.0.1:1"), self.assertRaisesMessage(ValidationError, "no responde"):
            archivos.revisar_con_el_antivirus(PDF)


@override_settings(MEDIA_ROOT=CARPETA, ANTIVIRUS="")
class PruebaDeArchivos(PruebaDePantalla):
    """Base con la estructura del principio del fichero."""

    # Crea la estructura.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.general)
        cls.ebro, cls.gru_ebro = crear_organizacion("ORG Ebro", "GRU Ebro")
        cls.lince = crear_usuario_de_prueba("Lince")
        cls.nutria = crear_usuario_de_prueba("Nutria")
        cls.erizo = crear_usuario_de_prueba("Erizo")
        admitir(cls.lince, cls.henares, rol=Pertenencia.ADMIN_GRUPO)
        admitir(cls.nutria, cls.henares)
        admitir(cls.erizo, cls.gru_ebro)
        cls.usuario = cls.nutria

    # Inicia sesión como otra persona.
    def como(self, persona):
        self.client.force_login(persona)

    # Sube un PDF de Nutria a GRU Henares (o colgado de algo, con «ancla»).
    def pdf(self, nombre="plano.pdf", ancla=(None, None), persona=None):
        return servicios.subir_archivo(
            persona or self.nutria, SimpleUploadedFile(nombre, PDF), grupo=self.henares, visibilidad="grupo:0", ancla=ancla
        )

    # Un debate de GRU Henares que ve todo el grupo (con la facilitación de quien se diga).
    def debate(self):
        Debate = apps.get_model("debates", "Debate")
        return Debate.objects.create(pregunta="¿Dónde?", grupo=self.henares, audiencia=audiencia_de("grupo:0", self.henares), estado="abierto")


class PruebasDeSubir(PruebaDeArchivos):
    """Subir, ver, descargar y versiones."""

    # Desde la pantalla, colgado de un debate: queda con su grupo; la ficha lo enseña en un marco y
    # «Abrir» lo entrega como PDF (sin adivinar tipos); Erizo, de otra organización, no lo ve.
    def test_subir_desde_la_pantalla(self):
        debate = self.debate()
        respuesta = self.client.post(f"/documentos/nuevo/archivo/?ancla=debates.debate:{debate.pk}", {"archivo": SimpleUploadedFile("contexto.pdf", PDF), "titulo": ""})
        documento = Documento.objects.get(tipo=Documento.ARCHIVO)
        self.assertRedirects(respuesta, f"/documentos/{documento.pk}/")
        self.assertEqual((documento.titulo, documento.grupo, documento.ancla_tipo, documento.extension), ("contexto.pdf", self.henares, "debates.debate", "pdf"))
        self.assertContains(self.client.get(f"/documentos/{documento.pk}/"), "<iframe")
        descarga = self.client.get(f"/documentos/{documento.pk}/archivo/")
        self.assertEqual((descarga["Content-Type"], descarga["X-Content-Type-Options"]), ("application/pdf", "nosniff"))
        self.assertEqual(b"".join(descarga.streaming_content), PDF)
        self.assertIn("attachment", self.client.get(f"/documentos/{documento.pk}/archivo/?descargar=1")["Content-Disposition"])
        # En la ficha del debate, en «Cuelga de aquí».
        self.assertContains(self.client.get(f"/debates/{debate.pk}/"), "contexto.pdf")
        self.como(self.erizo)
        self.assertEqual(self.client.get(f"/documentos/{documento.pk}/archivo/").status_code, 403)

    # Un .docx desde la pantalla: sale el aviso de Microsoft y no se guarda nada.
    def test_aviso_de_microsoft(self):
        respuesta = self.client.post("/documentos/nuevo/archivo/", {"archivo": SimpleUploadedFile("acta.docx", b"PK..."), "visibilidad": "grupo:0"})
        self.assertContains(respuesta, "No se admiten formatos de Microsoft")
        self.assertFalse(Documento.objects.exists())

    # Otra versión: se guardan las dos y se descarga cada una; Nutria (la autora) puede, Lince (admin)
    # también; una persona del grupo cualquiera, no.
    def test_versiones(self):
        documento = self.pdf()
        url = f"/documentos/{documento.pk}/"
        self.client.post(url, {"accion": "version", "archivo": SimpleUploadedFile("plano-v2.pdf", PDF + b"% v2\n")})
        self.assertEqual(list(documento.archivos.values_list("numero", "nombre_original")), [(2, "plano-v2.pdf"), (1, "plano.pdf")])
        self.assertEqual(b"".join(self.client.get(f"{url}archivo/1/").streaming_content), PDF)
        otra = crear_usuario_de_prueba("Garza")
        admitir(otra, self.henares)
        self.assertFalse(servicios.puede_modificar(otra, documento))
        self.assertTrue(servicios.puede_modificar(self.lince, documento))

    # El espacio de la organización: con 0 MB… no se puede poner (mínimo 1); con 1 MB y un archivo de casi
    # 1 MB, el segundo ya no cabe.
    def test_espacio(self):
        with self.assertRaises(ValidationError):
            servicios.poner_espacio(str(self.tajo.pk), "0")
        servicios.poner_espacio(str(self.tajo.pk), "1")
        servicios.subir_archivo(self.nutria, SimpleUploadedFile("a.txt", b"a" * 1_000_000), grupo=self.henares, visibilidad="grupo:0")
        with self.assertRaisesMessage(ValidationError, "espacio máximo"):
            servicios.subir_archivo(self.nutria, SimpleUploadedFile("b.txt", b"b" * 100_000), grupo=self.henares, visibilidad="grupo:0")
        # La pantalla, solo el superadmin.
        self.assertEqual(self.client.get("/documentos/espacio/").status_code, 403)
        self.como(crear_usuario_de_prueba("superadmin", es_superadmin=True))
        self.assertContains(self.client.get("/documentos/espacio/"), "ORG Tajo")
        self.client.post("/documentos/espacio/", {"organizacion": str(self.tajo.pk), "megas": ""})
        self.assertFalse(EspacioParaArchivos.objects.filter(organizacion=self.tajo).exists())


class PruebasDeEnlaces(PruebaDeArchivos):
    """Enlaces a otra web o a otro documento."""

    # A Drive y a un texto de aquí; a los dos a la vez, no; a «javascript:», no.
    def test_enlazar(self):
        acta = servicios.crear(self.lince, Documento.LIBRE, "Notas", grupo=self.henares, visibilidad="grupo:0")
        respuesta = self.client.post("/documentos/nuevo/enlace/", {"titulo": "Carpeta", "url": "https://drive.google.com/x", "visibilidad": "grupo:0"})
        enlace = Documento.objects.get(tipo=Documento.ENLACE)
        self.assertRedirects(respuesta, f"/documentos/{enlace.pk}/")
        self.assertContains(self.client.get(f"/documentos/{enlace.pk}/"), 'rel="noopener noreferrer"')
        interno = servicios.enlazar(self.nutria, "", enlazado=acta, grupo=self.henares, visibilidad="grupo:0")
        self.assertEqual(interno.titulo, "Notas")
        self.assertContains(self.client.get(f"/documentos/{interno.pk}/"), f"/documentos/{acta.pk}/")
        with self.assertRaises(ValidationError):
            servicios.enlazar(self.nutria, "Doble", url="https://a.org", enlazado=acta, grupo=self.henares)
        with self.assertRaises(ValidationError):
            servicios.enlazar(self.nutria, "Malo", url="javascript:alert(1)", grupo=self.henares)


class PruebasDePapelera(PruebaDeArchivos):
    """Eliminar, recuperar y vaciar la papelera."""

    # Nutria elimina su PDF: sale de la lista y va a la papelera; Lince (admin) también puede recuperarlo;
    # otra persona del grupo, no lo ve. A los 30 días se borra con su fichero.
    def test_eliminar_recuperar_y_vaciar(self):
        documento = self.pdf()
        url = f"/documentos/{documento.pk}/"
        self.assertRedirects(self.client.post(url, {"accion": "eliminar"}), "/documentos/papelera/")
        self.assertNotContains(self.client.get("/documentos/"), "plano.pdf")
        self.assertContains(self.client.get("/documentos/papelera/"), "plano.pdf")
        otra = crear_usuario_de_prueba("Garza")
        admitir(otra, self.henares)
        self.como(otra)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.como(self.lince)
        self.assertRedirects(self.client.post("/documentos/papelera/", {"recuperar": documento.pk}), url)
        documento.refresh_from_db()
        self.assertIsNone(documento.en_papelera_desde)
        # Vaciar: lo eliminado hace más de 30 días se borra, con su fichero.
        servicios.eliminar(self.lince, documento)
        fichero = documento.archivos.get().fichero.name
        Documento.objects.filter(pk=documento.pk).update(en_papelera_desde=timezone.now() - timedelta(days=31))
        self.assertEqual(servicios.vaciar_papelera(timezone.now() - timedelta(days=30)), 1)
        self.assertFalse(VersionDeArchivo.objects.exists())
        from django.core.files.storage import default_storage

        self.assertFalse(default_storage.exists(fichero))

    # Un texto también se elimina; una persona del grupo que no lo creó, no puede.
    def test_quien_elimina(self):
        texto = servicios.crear(self.lince, Documento.LIBRE, "Notas", grupo=self.henares, visibilidad="grupo:0")
        self.assertFalse(servicios.puede_eliminar(self.nutria, texto))
        self.assertTrue(servicios.puede_eliminar(self.lince, texto))


class PruebasDeColgantes(PruebaDeArchivos):
    """Congelados por una votación y los de las tareas en su proyecto."""

    # Un PDF de contexto de una consulta: antes de abrirse se cambia; abierta, ni versiones, ni nombre, ni
    # eliminar (pero sí añadir otro); y la ficha lo dice.
    def test_congelado_por_una_votacion(self):
        Consulta = apps.get_model("consultas", "Consulta")
        ahora = timezone.now()
        consulta = Consulta.objects.create(
            titulo="Presupuesto", grupo=self.henares, audiencia=audiencia_de("grupo:0", self.henares),
            audiencia_resultados=audiencia_de("grupo:0", self.henares), abre=ahora + timedelta(days=1), cierra=ahora + timedelta(days=8), estado="aceptada",
        )
        documento = self.pdf("presupuesto.pdf", ancla=("consultas.consulta", consulta.pk))
        self.assertTrue(servicios.puede_modificar(self.nutria, documento))
        Consulta.objects.filter(pk=consulta.pk).update(abre=ahora - timedelta(hours=1))
        self.assertFalse(servicios.puede_modificar(self.nutria, documento))
        self.assertFalse(servicios.puede_eliminar(self.lince, documento))
        with self.assertRaises(ValidationError):
            servicios.nueva_version(self.nutria, documento, SimpleUploadedFile("otro.pdf", PDF))
        self.assertContains(self.client.get(f"/documentos/{documento.pk}/"), "Congelado")
        self.pdf("anexo.pdf", ancla=("consultas.consulta", consulta.pk))

    # Un archivo de una tarea sale en la ficha de su proyecto, con el nombre de la tarea; de una tarea
    # personal no se cuelga nada.
    def test_tareas_en_su_proyecto(self):
        Proyecto, Tarea = apps.get_model("proyectos", "Proyecto"), apps.get_model("proyectos", "Tarea")
        proyecto = Proyecto.objects.create(
            titulo="Huerto", tipologia=crear_tipologia("proyecto", "Genérico"), grupo=self.henares, audiencia=audiencia_de("grupo:0", self.henares), creador=self.nutria
        )
        tarea = Tarea.objects.create(titulo="Comprar semillas", proyecto=proyecto, grupo=self.henares, responsable=self.nutria)
        self.pdf("factura.pdf", ancla=("proyectos.tarea", tarea.pk))
        respuesta = self.client.get(f"/proyectos/{proyecto.pk}/")
        self.assertContains(respuesta, "factura.pdf")
        self.assertContains(respuesta, "de «Comprar semillas»")
        personal = Tarea.objects.create(titulo="Lo mío", personal=True, responsable=self.nutria)
        with self.assertRaisesMessage(ValidationError, "no se pueden colgar"):
            self.pdf("x.pdf", ancla=("proyectos.tarea", personal.pk))


class PruebasDeLaLista(PruebaDeArchivos):
    """La lista filtrable de documentos."""

    # Textos, archivos y enlaces juntos, con sus filtros; cuesta lo mismo con más filas.
    def test_lista(self):
        def mas():
            self.pdf("otro.pdf")
            servicios.enlazar(self.nutria, "Web", url="https://ejemplo.org", grupo=self.henares, visibilidad="grupo:0")

        self.pdf()
        respuesta = self.comprobar_consultas("/documentos/", 4, mas)
        for texto in ("plano.pdf", "Enlace a otra web", "Cuelga de", "Último cambio:", 'data-fecha="'):
            self.assertContains(respuesta, texto)


class PruebasDePermisos(PruebaDeArchivos):
    """Lo que puede hacer cada persona con cada documento (R U D) y, si no, por qué y cómo conseguirlo."""

    # Un texto de Lince: Nutria solo lee (R) y la ficha le dice a quién pedir la redacción; Lince (la tiene y
    # administra) puede todo (R U D). La lista lo dice en «Puedo» y en el filtro «Puedo cambiarlo»; arriba,
    # dónde puede crear.
    def test_letras_y_explicacion(self):
        texto = servicios.crear(self.lince, Documento.LIBRE, "Notas de Lince", grupo=self.henares, visibilidad="grupo:0")
        propio = self.pdf()
        permisos = servicios.permisos_en_lista(self.nutria, [texto, propio])
        self.assertEqual((permisos[texto.pk].u, permisos[texto.pk].d, permisos[texto.pk].falta_redaccion), (False, False, True))
        self.assertEqual((permisos[propio.pk].u, permisos[propio.pk].d), (True, True))
        lista = self.client.get("/documentos/")
        self.assertContains(lista, "No puedes cambiarlo: Solo lo escriben quienes tienen su redacción")
        self.assertContains(lista, "puedes crear documentos en GRU Tajo, GRU Henares.")
        ficha = self.client.get(f"/documentos/{texto.pk}/")
        self.assertContains(ficha, "pide la redacción a")
        self.assertContains(ficha, "/comunicaciones/personas/escribir/?a=Lince")
        self.assertContains(ficha, "pídesela a la administración de GRU Henares")
        self.assertTrue(servicios.permisos_de(self.lince, texto).u)
        # Quien no puede crear en ningún grupo lo ve explicado, sin botones de crear.
        self.como(crear_usuario_de_prueba("Suelta"))
        respuesta = self.client.get("/documentos/")
        self.assertContains(respuesta, "No puedes crear documentos")
        self.assertNotContains(respuesta, "Subir un archivo</a>")


class PruebasDelRangoDeFechas(SimpleTestCase):
    """El rango de fechas de la tabla filtrable común (base/tablas.py)."""

    # Desde, hasta, los dos o ninguno; las filas sin fecha no salen cuando hay rango.
    def test_filtrar(self):
        filas = [{"n": "a", "f": date(2026, 1, 10)}, {"n": "b", "f": date(2026, 3, 1)}, {"n": "c", "f": None}]
        fuente = FuenteDeLista(filas, ["n"])

        # Los nombres de las filas que quedan con ese rango.
        def quedan(desde, hasta):
            return [fila["n"] for fila in fuente.filtrar([], {}, {}, ("f", desde, hasta)).filas]

        self.assertEqual(quedan("2026-02-01", ""), ["b"])
        self.assertEqual(quedan("", "2026-02-01"), ["a"])
        self.assertEqual(quedan("2026-01-10", "2026-03-01"), ["a", "b"])
        self.assertEqual([fila["n"] for fila in fuente.filtrar([], {}, {}).filas], ["a", "b", "c"])
