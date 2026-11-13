"""
Pruebas del módulo «mantenimiento»: solo lo ve el superadmin (menú y pantallas), el menú de tres
niveles, los documentos, las plantillas y las importaciones de grupos y usuarios.
"""


from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from base.hojas import Hoja, crear_ods, leer_filas
from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from grupos.models import AdminDeOrganizacion, Grupo, Organizacion, Pertenencia
from grupos.servicios import admitir, crear_grupo, crear_organizacion
from mantenimiento.documentos import DOCUMENTOS
from mantenimiento.importacion import aplicar_grupos, aplicar_usuarios, revisar_grupos, revisar_usuarios
from mantenimiento.models import AjustesDeMantenimiento


# Convierte una lista de filas (la primera, la cabecera) en lo que devuelve leer_filas(), pasando de
# verdad por un .csv, como si se hubiera subido.
def filas_de(filas):
    texto = "\n".join(";".join(celdas) for celdas in filas)
    return leer_filas(SimpleUploadedFile("datos.csv", texto.encode("utf-8")))


# Cabeceras de las plantillas.
CABECERA_DE_GRUPOS = ["Organización", "Grupo", "Grupo padre", "Localización"]
CABECERA_DE_USUARIOS = ["Alias", "Contraseña", "Organización", "Grupo", "Rol", "Asamblea base", "Admin de la organización", "Correo alternativo"]


class PruebasComoSuperadmin(PruebaDePantalla):
    """Recorre «Desarrollo y mantenimiento» como superadmin."""

    # El usuario de la sesión es superadmin.
    @classmethod
    def setUpTestData(cls):
        cls.usuario = crear_usuario_de_prueba("Águila", es_superadmin=True)

    # El menú tiene la sección con sus tres subsecciones; en «Pruebas», arriba, las dos importaciones.
    def test_menu(self):
        respuesta = self.client.get("/mantenimiento/pruebas/grupos/")
        for texto in ["Desarrollo y mantenimiento", "Ayuda y documentación", "Pruebas", "Importar grupos", "Importar usuarios"]:
            self.assertContains(respuesta, texto)
        self.assertEqual(respuesta.context["interfaz"]["codigos"], ["mantenimiento.desarrollo", "mantenimiento.pruebas"])

    # Cada pantalla cuesta pocas consultas y no tiene listas que crezcan.
    def test_consultas(self):
        for clave, _fichero, _titulo in DOCUMENTOS:
            with self.subTest(documento=clave):
                self.comprobar_consultas(f"/mantenimiento/documentacion/{clave}/", 1, None)
        self.comprobar_consultas("/mantenimiento/trastienda/", 1, None)
        self.comprobar_consultas("/mantenimiento/pruebas/grupos/", 1, None)
        self.comprobar_consultas("/mantenimiento/pruebas/usuarios/", 2, None)
        self.comprobar_consultas("/mantenimiento/pruebas/ejemplos/", 4, None)

    # Los documentos se convierten con tablas e índice, y sus enlaces llevan a sus páginas; cada uno es
    # una pestaña del menú superior.
    def test_documentos(self):
        respuesta = self.client.get("/mantenimiento/documentacion/diseno/")
        self.assertContains(respuesta, "<table>")
        self.assertContains(respuesta, 'class="toc"')
        self.assertContains(respuesta, 'href="/mantenimiento/documentacion/registro-y-validacion/"')
        self.assertContains(respuesta, 'aria-current="page">Diseño y decisiones</a>')

    # Las plantillas se descargan como .ods y se pueden volver a leer.
    def test_plantillas(self):
        for direccion, primera in [("grupos", "Organización"), ("usuarios", "Alias")]:
            respuesta = self.client.get(f"/mantenimiento/pruebas/{direccion}/plantilla.ods")
            self.assertEqual(respuesta["Content-Type"], "application/vnd.oasis.opendocument.spreadsheet")
            filas = leer_filas(SimpleUploadedFile("plantilla.ods", respuesta.content))
            self.assertEqual(filas[0][1][0], primera)

    # Importar grupos de principio a fin por la pantalla: revisar, ver la vista previa y confirmar.
    def test_importar_grupos_por_la_pantalla(self):
        hoja = crear_ods([Hoja("Datos", [CABECERA_DE_GRUPOS, ["ORG Miño", "GRU Sil", "GRU Miño", "Ourense"], ["ORG Miño", "GRU Miño", "", ""]])])
        respuesta = self.client.post(
            "/mantenimiento/pruebas/grupos/", {"accion": "revisar", "fichero": SimpleUploadedFile("grupos.ods", hoja)}
        )
        self.assertContains(respuesta, "ORG Miño › GRU Miño › GRU Sil")
        self.assertContains(respuesta, "Confirmar e importar")
        self.assertFalse(Grupo.objects.exists())
        respuesta = self.client.post("/mantenimiento/pruebas/grupos/", {"accion": "confirmar"})
        self.assertContains(respuesta, "Importación hecha")
        self.assertEqual(Grupo.objects.get(nombre="GRU Sil").padre.nombre, "GRU Miño")
        # Confirmar otra vez no hace nada: el plan ya se usó.
        self.assertContains(self.client.post("/mantenimiento/pruebas/grupos/", {"accion": "confirmar"}), "No hay ninguna importación pendiente")

    # Sin activar el alta masiva no se importan usuarios; el interruptor la activa.
    def test_alta_masiva_desactivada(self):
        respuesta = self.client.post("/mantenimiento/pruebas/usuarios/", {"accion": "revisar"})
        self.assertContains(respuesta, "El alta masiva de usuarios está desactivada.")
        self.client.post("/mantenimiento/pruebas/usuarios/permitir/")
        self.assertTrue(AjustesDeMantenimiento.actuales().alta_masiva_de_usuarios)

    # Crear y borrar los datos de ejemplo desde la pantalla; el superadmin se queda.
    @override_settings(DEBUG=True)
    def test_datos_de_ejemplo(self):
        respuesta = self.client.post("/mantenimiento/pruebas/ejemplos/", {"accion": "crear"})
        self.assertContains(respuesta, "Creados los datos de ejemplo de: Usuarios, Organizaciones y grupos, Etiquetas, Tipologías, Lugares, Talentos.")
        self.assertTrue(Organizacion.objects.filter(nombre="ORG Tajo").exists())
        respuesta = self.client.post("/mantenimiento/pruebas/ejemplos/", {"accion": "borrar"})
        self.assertContains(respuesta, "Borrados")
        self.assertFalse(Organizacion.objects.exists())
        self.assertEqual(set(get_user_model().objects.values_list("alias", flat=True)), {"Águila", "superadmin"})

    # Sin DEBUG (en el servidor real), los botones no hacen nada.
    @override_settings(DEBUG=False)
    def test_datos_de_ejemplo_fuera_de_desarrollo(self):
        respuesta = self.client.post("/mantenimiento/pruebas/ejemplos/", {"accion": "crear"})
        self.assertContains(respuesta, "Solo se pueden crear o borrar en desarrollo")
        self.assertFalse(Organizacion.objects.exists())

    # Un fichero que no es una hoja se explica.
    def test_fichero_ilegible(self):
        respuesta = self.client.post(
            "/mantenimiento/pruebas/grupos/", {"accion": "revisar", "fichero": SimpleUploadedFile("datos.pdf", b"%PDF")}
        )
        self.assertContains(respuesta, "Sube un fichero .ods (LibreOffice) o .csv.")


class PruebasComoUsuario(PruebaDePantalla):
    """Una persona sin el permiso no ve la sección ni puede entrar."""

    # No sale en su menú, y si escribe la dirección, sale la explicación de lo que falta.
    def test_sin_permiso(self):
        self.assertNotContains(self.client.get("/"), "Desarrollo y mantenimiento")
        for direccion in ["/mantenimiento/documentacion/diseno/", "/mantenimiento/pruebas/grupos/"]:
            respuesta = self.client.get(direccion)
            self.assertContains(respuesta, "hace falta el permiso «mantenimiento.ver»", status_code=403)


class PruebasDeImportarGrupos(TestCase):
    """Comprueba la revisión y la creación de grupos."""

    # Ya existe ORG Tajo con GRU Tajo ⊃ GRU Jarama.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.jarama = crear_grupo(cls.tajo, "GRU Jarama", padre=cls.general)

    # El orden de las filas da igual, los padres pueden existir ya y se crean las organizaciones nuevas;
    # los grupos ya existentes no se tocan.
    def test_crea_el_arbol(self):
        revision = revisar_grupos(filas_de([
            CABECERA_DE_GRUPOS,
            ["ORG Tajo", "GRU Sorbe", "GRU Henares", ""],
            ["ORG Tajo", "GRU Henares", "GRU Jarama", "Alcalá"],
            ["ORG Tajo", "GRU Jarama", "GRU Tajo", ""],
            ["ORG Ebro", "GRU Ebro", "", ""],
            ["ORG Ebro", "GRU Segre", "GRU Ebro", ""],
        ]))
        self.assertFalse(revision.hay_errores, [fila.mensajes for fila in revision.filas])
        self.assertEqual(revision.resumen, {"nuevo": 4, "existe": 1})
        self.assertEqual(revision.filas[0].detalle, "ORG Tajo › GRU Tajo › GRU Jarama › GRU Henares › GRU Sorbe")
        self.assertEqual(aplicar_grupos(revision.plan), {"organizaciones": 1, "grupos": 4})
        sorbe = Grupo.objects.get(nombre="GRU Sorbe")
        self.assertEqual(list(sorbe.ascendencia.order_by("distancia").values_list("antecesor__nombre", flat=True)),
                         ["GRU Sorbe", "GRU Henares", "GRU Jarama", "GRU Tajo"])
        self.assertEqual(Grupo.objects.get(nombre="GRU Henares").ambito, "Alcalá")

    # Errores: padre que no existe, círculo, repetidos y campos vacíos. Con errores no hay plan.
    def test_errores(self):
        revision = revisar_grupos(filas_de([
            CABECERA_DE_GRUPOS,
            ["ORG Tajo", "GRU A", "GRU Fantasma", ""],
            ["ORG Tajo", "GRU B", "GRU C", ""],
            ["ORG Tajo", "GRU C", "GRU B", ""],
            ["ORG Tajo", "GRU D", "", ""],
            ["ORG Tajo", "GRU D", "", ""],
            ["", "GRU E", "", ""],
        ]))
        mensajes = [" ".join(fila.mensajes) for fila in revision.filas]
        self.assertIn("«GRU Fantasma» no está en el fichero", mensajes[0])
        self.assertIn("círculo", mensajes[1])
        self.assertIn("ya está más arriba, en la fila 5", mensajes[4])
        self.assertIn("Faltan la organización o el grupo", mensajes[5])
        self.assertTrue(revision.hay_errores)
        self.assertEqual(revision.plan, {})

    # Un grupo que ya existe con otro padre se avisa, pero no se cambia.
    def test_aviso_de_otro_padre(self):
        revision = revisar_grupos(filas_de([CABECERA_DE_GRUPOS, ["ORG Tajo", "GRU Jarama", "", ""], ["ORG Tajo", "GRU Jarama2", "GRU Tajo", ""]]))
        self.assertEqual(revision.filas[0].estado, "existe")
        revision = revisar_grupos(filas_de([CABECERA_DE_GRUPOS, ["ORG Tajo", "GRU Tajo", "GRU Jarama", ""]]))
        self.assertIn("Ya existe con otro grupo padre", revision.filas[0].mensajes[0])

    # Faltan columnas: se explica cuáles.
    def test_faltan_columnas(self):
        revision = revisar_grupos(filas_de([["Organización", "Grupo"], ["ORG Tajo", "GRU X"]]))
        self.assertIn("Faltan columnas en la primera fila: «Grupo padre»", revision.errores[0])

    # Revisar cuesta lo mismo con 3 filas que con 30.
    def test_consultas(self):
        for cuantas in (3, 30):
            filas = filas_de([CABECERA_DE_GRUPOS, *[["ORG Tajo", f"GRU {numero}", "GRU Tajo", ""] for numero in range(cuantas)]])
            with self.assertNumQueries(2):
                revisar_grupos(filas)


class PruebasDeImportarUsuarios(TestCase):
    """Comprueba la revisión y la creación de usuarios."""

    # ORG Tajo (GRU Tajo ⊃ GRU Henares) y ORG Ebro (GRU Segre). Ya existe Lince, en Henares (su base).
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.general)
        cls.ebro, cls.segre = crear_organizacion("ORG Ebro", "GRU Segre")
        cls.lince = crear_usuario_de_prueba("Lince")
        admitir(cls.lince, cls.henares, es_base=True)

    # Alias nuevos con su contraseña, varios grupos, rol vacío = usuario, base por defecto la primera
    # fila, admin de organización; un alias existente solo gana pertenencias.
    def test_crea_usuarios_y_pertenencias(self):
        revision = revisar_usuarios(filas_de([
            CABECERA_DE_USUARIOS,
            ["Nutria", "Clave-Larga-2026", "ORG Tajo", "GRU Henares", "", "", "sí", "nutria@ejemplo.org"],
            ["nutria", "", "ORG Ebro", "GRU Segre", "Admin del grupo", "", "", ""],
            ["LINCE", "otra", "ORG Ebro", "GRU Segre", "", "sí", "", ""],
        ]))
        self.assertTrue(revision.hay_errores)  # «nutria» y «Nutria» escritos distinto
        revision = revisar_usuarios(filas_de([
            CABECERA_DE_USUARIOS,
            ["Nutria", "Clave-Larga-2026", "ORG Tajo", "GRU Henares", "", "", "sí", "nutria@ejemplo.org"],
            ["Nutria", "", "ORG Ebro", "GRU Segre", "Admin del grupo", "", "", ""],
            ["Lince", "otra", "ORG Ebro", "GRU Segre", "", "sí", "", ""],
        ]))
        self.assertFalse(revision.hay_errores, [fila.mensajes for fila in revision.filas])
        avisos = " ".join(" ".join(fila.mensajes) for fila in revision.filas)
        self.assertIn("su contraseña no se cambia", avisos)
        self.assertIn("Ya tiene asamblea base: no se cambia.", avisos)
        self.assertIn("Será su asamblea base", avisos)
        self.assertNotIn("Clave-Larga-2026", str(revision.plan))
        self.assertEqual(aplicar_usuarios(revision.plan), {"usuarios": 1, "pertenencias": 3})
        nutria = get_user_model().objects.get(alias="Nutria")
        self.assertTrue(nutria.check_password("Clave-Larga-2026"))
        self.assertEqual(nutria.correo_alternativo, "nutria@ejemplo.org")
        self.assertEqual(Pertenencia.objects.get(usuario=nutria, es_base=True).grupo, self.henares)
        self.assertEqual(Pertenencia.objects.get(usuario=nutria, grupo=self.segre).rol, "admin_grupo")
        self.assertTrue(AdminDeOrganizacion.objects.filter(usuario=nutria, organizacion=self.tajo).exists())
        self.assertTrue(Pertenencia.objects.filter(usuario=self.lince, grupo=self.segre, es_base=False).exists())

    # Errores: grupo que no existe, rol desconocido, contraseña floja o ausente, sí/no raro, correo
    # malo y alias con símbolos.
    def test_errores(self):
        revision = revisar_usuarios(filas_de([
            CABECERA_DE_USUARIOS,
            ["Garza", "Clave-Larga-2026", "ORG Tajo", "GRU Nada", "", "", "", ""],
            ["Garza", "", "ORG Tajo", "GRU Henares", "pirata", "", "", ""],
            ["Erizo", "123", "ORG Tajo", "GRU Henares", "", "", "", ""],
            ["Tejón", "", "ORG Tajo", "GRU Henares", "", "", "", ""],
            ["Lobo", "Clave-Larga-2026", "ORG Tajo", "GRU Henares", "", "quizá", "", ""],
            ["Olmo", "Clave-Larga-2026", "ORG Tajo", "GRU Henares", "", "", "", "no-es-correo"],
            ["<b>", "Clave-Larga-2026", "ORG Tajo", "GRU Henares", "", "", "", ""],
        ]))
        mensajes = [" ".join(fila.mensajes) for fila in revision.filas]
        self.assertIn("No existe el grupo «GRU Nada» en «ORG Tajo»", mensajes[0])
        self.assertIn("No existe el rol «pirata»", mensajes[1])
        self.assertIn("Contraseña no válida", mensajes[2])
        self.assertIn("Falta la contraseña de este alias nuevo", mensajes[3])
        self.assertIn("escribe «sí», «no» o déjalo vacío", mensajes[4])
        self.assertIn("no es un correo válido", mensajes[5])
        self.assertIn("El alias debe tener", mensajes[6])
        self.assertEqual(revision.plan, {})

    # Revisar cuesta lo mismo con 3 filas que con 30 (sin contar el cifrado de las contraseñas, que no
    # hace consultas).
    def test_consultas(self):
        for cuantas in (3, 30):
            # Con un alias que ya existe (Lince), para que se hagan todas las consultas.
            filas = filas_de([
                CABECERA_DE_USUARIOS,
                ["Lince", "", "ORG Ebro", "GRU Segre", "", "", "", ""],
                *[[f"Extra {numero}", "", "ORG Tajo", "GRU Henares", "", "", "", ""] for numero in range(cuantas)],
            ])
            with self.assertNumQueries(5):
                revisar_usuarios(filas)


class PruebasDeHojas(TestCase):
    """Comprueba la lectura de .ods y .csv."""

    # Un .ods con celdas repetidas, números y espacios dobles se lee como se ve.
    def test_ods(self):
        datos = crear_ods([Hoja("Datos", [["A", "B"], ["uno  dos", "3"], [], ["x", ""]])])
        filas = leer_filas(SimpleUploadedFile("hoja.ods", datos))
        self.assertEqual(filas, [(1, ["A", "B"]), (2, ["uno  dos", "3"]), (4, ["x"])])

    # Un .csv con punto y coma o con coma, y con tildes en UTF-8 o Latin-1.
    def test_csv(self):
        for separador, codificacion in [(";", "utf-8"), (",", "latin-1")]:
            texto = f"Organización{separador}Grupo\nORG Miño{separador}GRU Sil\n".encode(codificacion)
            self.assertEqual(leer_filas(SimpleUploadedFile("a.csv", texto))[1][1], ["ORG Miño", "GRU Sil"])
