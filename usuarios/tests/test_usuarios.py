"""
Pruebas del módulo «usuarios»: el alias, la entrada y la salida, la sesión obligatoria, las
preferencias, el cambio de contraseña y los usuarios de ejemplo.
"""

from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from base.pruebas import CONTRASENA_DE_PRUEBA, PruebaDePantalla, crear_usuario_de_prueba
from usuarios import ejemplos
from usuarios.models import Usuario


class PruebasDelAlias(TestCase):
    """Comprueba la forma del alias y que no se repita sin contar mayúsculas ni tildes."""

    # «María» y «maria» son el mismo alias: el segundo no se puede crear.
    def test_no_se_repite_sin_tildes_ni_mayusculas(self):
        crear_usuario_de_prueba("María")
        with self.assertRaisesMessage(ValidationError, "Ya hay un usuario con ese alias"):
            crear_usuario_de_prueba("MARIA")

    # Los espacios de más se quitan antes de guardar.
    def test_espacios(self):
        usuario = crear_usuario_de_prueba("  Lince   rojo ")
        self.assertEqual(usuario.alias, "Lince rojo")
        self.assertEqual(usuario.alias_normalizado, "lince rojo")

    # Alias demasiado cortos o con símbolos no valen.
    def test_forma(self):
        for alias in ["ab", "<script>", "correo@ejemplo.org"]:
            with self.subTest(alias=alias), self.assertRaises(ValidationError):
                crear_usuario_de_prueba(alias)

    # El superadmin puede entrar en la trastienda; los demás, no.
    def test_superadmin(self):
        superadmin = crear_usuario_de_prueba("Águila", es_superadmin=True)
        normal = crear_usuario_de_prueba("Lince")
        self.assertTrue(superadmin.is_staff and superadmin.has_perm("lo_que_sea"))
        self.assertFalse(normal.is_staff or normal.has_perm("lo_que_sea"))


class PruebasDeEntradaYSalida(TestCase):
    """Comprueba la pantalla de entrada, la salida y que nada se ve sin sesión."""

    # Crea el usuario «Águila» para todas las pruebas de la clase.
    @classmethod
    def setUpTestData(cls):
        cls.usuario = crear_usuario_de_prueba("Águila")

    # Sin sesión, cualquier pantalla lleva a la entrada, recordando adónde se quería ir.
    def test_sin_sesion_se_va_a_la_entrada(self):
        respuesta = self.client.get("/componentes/")
        self.assertRedirects(respuesta, "/cuenta/entrar/?next=/componentes/")

    # Si la petición es de htmx (por ejemplo, con la sesión caducada), se le pide que cargue la entrada
    # como página entera, en lugar de meterla en la zona central.
    def test_sin_sesion_con_htmx(self):
        respuesta = self.client.get("/componentes/", headers={"HX-Request": "true", "HX-Target": "zona"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["HX-Redirect"], "/cuenta/entrar/?next=/componentes/")

    # La pantalla de entrada se ve sin sesión, sin consultas y sin botón «copiar» en el alias.
    def test_pantalla_de_entrada(self):
        with self.assertNumQueries(0):
            respuesta = self.client.get("/cuenta/entrar/")
        self.assertContains(respuesta, 'name="username"')
        self.assertNotContains(respuesta, 'x-data="copiar"')

    # Se entra escribiendo el alias sin tilde y en minúsculas, y se va adonde se quería ir.
    def test_entrar_sin_tildes(self):
        respuesta = self.client.post(
            "/cuenta/entrar/", {"username": "aguila", "password": CONTRASENA_DE_PRUEBA, "next": "/componentes/"}
        )
        self.assertRedirects(respuesta, "/componentes/")
        self.assertContains(self.client.get("/"), "Águila")

    # Con una contraseña equivocada no se entra y se explica.
    def test_contrasena_equivocada(self):
        respuesta = self.client.post("/cuenta/entrar/", {"username": "Águila", "password": "otra"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Por favor")

    # Una cuenta desactivada no puede entrar.
    def test_cuenta_desactivada(self):
        Usuario.objects.filter(pk=self.usuario.pk).update(activo=False)
        respuesta = self.client.post("/cuenta/entrar/", {"username": "Águila", "password": CONTRASENA_DE_PRUEBA})
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    # «Salir» cierra la sesión y vuelve a la entrada.
    def test_salir(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.post("/cuenta/salir/")
        self.assertRedirects(respuesta, "/cuenta/entrar/")
        self.assertRedirects(self.client.get("/"), "/cuenta/entrar/?next=/")


class PruebasDeMiCuenta(PruebaDePantalla):
    """Comprueba «Mi cuenta»: preferencias y contraseña, con su número de consultas."""

    # Preferencias: una consulta (el usuario de la sesión). No muestra listas.
    def test_consultas_de_preferencias(self):
        respuesta = self.comprobar_consultas("/cuenta/preferencias/", 1, None)
        self.assertContains(respuesta, 'data-valor="supercompacta"')

    # Contraseña: una consulta. No muestra listas.
    def test_consultas_de_contrasena(self):
        self.comprobar_consultas("/cuenta/contrasena/", 1, None)

    # Guardar una preferencia cuesta una consulta más (la actualización) y queda en la cuenta.
    def test_guardar_preferencia(self):
        with self.assertNumQueries(2):
            respuesta = self.client.post("/cuenta/preferencias/guardar/", {"clave": "tema", "valor": "oscuro"})
        self.assertEqual(respuesta.status_code, 204)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.tema, "oscuro")

    # Una preferencia o un valor inventados no se guardan.
    def test_preferencia_no_valida(self):
        for datos in [{"clave": "tema", "valor": "fucsia"}, {"clave": "password", "valor": "x"}]:
            with self.subTest(datos=datos):
                respuesta = self.client.post("/cuenta/preferencias/guardar/", datos)
                self.assertEqual(respuesta.status_code, 400)

    # Las preferencias de la cuenta salen ya en <html>, para pintar la página sin destello. El tema
    # vacío (el del sistema) no se pone.
    def test_preferencias_en_la_pagina(self):
        respuesta = self.client.get("/")
        self.assertContains(respuesta, 'data-letra="normal"')
        self.assertNotContains(respuesta, "data-tema=")
        Usuario.objects.filter(pk=self.usuario.pk).update(tema="dia", densidad="supercompacta")
        respuesta = self.client.get("/")
        self.assertContains(respuesta, 'data-tema="dia"')
        self.assertContains(respuesta, 'data-densidad="supercompacta"')

    # Cambiar la contraseña: hace falta la actual, la nueva vale y la sesión sigue abierta.
    def test_cambiar_contrasena(self):
        nueva = "Otra-Contraseña-Larga-7"
        datos = {"old_password": CONTRASENA_DE_PRUEBA, "new_password1": nueva, "new_password2": nueva}
        respuesta = self.client.post("/cuenta/contrasena/", datos)
        self.assertContains(respuesta, "Contraseña cambiada")
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password(nueva))
        self.assertEqual(self.client.get("/").status_code, 200)

    # Con la contraseña actual equivocada no se cambia.
    def test_cambiar_contrasena_sin_la_actual(self):
        datos = {"old_password": "mal", "new_password1": "Otra-Larga-7", "new_password2": "Otra-Larga-7"}
        respuesta = self.client.post("/cuenta/contrasena/", datos)
        self.assertNotContains(respuesta, "Contraseña cambiada")
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password(CONTRASENA_DE_PRUEBA))


class PruebasDeLosEjemplos(TestCase):
    """Comprueba la orden «ejemplos» con los usuarios de ejemplo."""

    # Crear dos veces no duplica; el superadmin es «superadmin»; se entra con la contraseña común;
    # borrar quita los usuarios de ejemplo pero no al superadmin.
    @override_settings(DEBUG=True)
    def test_crear_y_borrar(self):
        call_command("ejemplos", "crear", stdout=None)
        call_command("ejemplos", "crear", stdout=None)
        self.assertEqual(Usuario.objects.count(), len(ejemplos.ALIAS_DE_EJEMPLO) + 1)
        self.assertTrue(Usuario.objects.get(alias="superadmin").es_superadmin)
        self.assertTrue(self.client.login(username="cigueña", password=ejemplos.CONTRASENA_DE_EJEMPLO))
        call_command("ejemplos", "borrar", stdout=None)
        self.assertEqual(list(Usuario.objects.values_list("alias", flat=True)), ["superadmin"])

    # Sin DEBUG (en el servidor real) la orden se niega.
    @override_settings(DEBUG=False)
    def test_solo_en_desarrollo(self):
        with self.assertRaises(CommandError):
            call_command("ejemplos", "crear")


class PruebasDeMisDatos(PruebaDePantalla):
    """«Configuración de mi cuenta → Mis datos → Datos»: cada dato con quién lo ve, y el correo se cambia."""

    # Crea a Nutria, con la sesión iniciada.
    @classmethod
    def setUpTestData(cls):
        cls.usuario = crear_usuario_de_prueba("Nutria")

    # La pantalla enseña los datos y quién ve cada uno, con 1 consulta (el usuario de la sesión).
    def test_ver(self):
        respuesta = self.comprobar_consultas("/cuenta/datos/", 1, None)
        self.assertContains(respuesta, "Quién lo ve")
        self.assertContains(respuesta, "Nutria")

    # El correo alternativo se cambia y se puede quitar; uno mal escrito no se guarda.
    def test_cambiar_el_correo(self):
        respuesta = self.client.post("/cuenta/datos/", {"correo_alternativo": "nutria@example.org"})
        self.assertRedirects(respuesta, "/cuenta/datos/?guardado=1")
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.correo_alternativo, "nutria@example.org")
        self.assertContains(self.client.post("/cuenta/datos/", {"correo_alternativo": "no-es-un-correo"}), "Introduzca una dirección")
        self.client.post("/cuenta/datos/", {"correo_alternativo": ""})
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.correo_alternativo, "")
