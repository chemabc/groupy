"""
Pruebas de «Usuarios → Roles y permisos»: número de consultas de cada pantalla, roles (crear, cambiar
permisos, borrar), excepciones y «Explicar un permiso», que debe decidir siempre igual que puede().
"""

from itertools import product

from django.core.cache import cache

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from base.registro import registro
from grupos.models import Pertenencia
from grupos.servicios import admitir, cambiar_rol, crear_grupo, crear_organizacion, nombrar_admin_de_organizacion
from permisos.models import ExcepcionDePermiso, PermisoDeRol, Rol
from permisos.servicios import crear_rol, explicar_permiso, poner_excepcion, puede


class PruebaDeRoles(PruebaDePantalla):
    """Base: superadmin con la sesión iniciada; ORG Tajo (GRU Tajo ⊃ GRU Henares ⊃ GRU Sorbe)."""

    # Crea la estructura: Lince admin de GRU Henares, Nutria en GRU Henares, Garza en GRU Sorbe y Zorro
    # admin de la organización.
    @classmethod
    def setUpTestData(cls):
        cls.usuario = crear_usuario_de_prueba("superadmin", es_superadmin=True)
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.general)
        cls.sorbe = crear_grupo(cls.tajo, "GRU Sorbe", padre=cls.henares)
        cls.lince = crear_usuario_de_prueba("Lince")
        cls.nutria = crear_usuario_de_prueba("Nutria")
        cls.garza = crear_usuario_de_prueba("Garza")
        cls.zorro = crear_usuario_de_prueba("Zorro")
        admitir(cls.lince, cls.henares, rol=Pertenencia.ADMIN_GRUPO)
        admitir(cls.nutria, cls.henares)
        admitir(cls.garza, cls.sorbe)
        admitir(cls.zorro, cls.general)
        nombrar_admin_de_organizacion(cls.zorro, cls.tajo)


class PruebasDeConsultas(PruebaDeRoles):
    """Cada pantalla cuesta lo mismo con pocas filas que con muchas."""

    # Lista de roles, con más roles cada vez.
    def test_roles(self):
        self.comprobar_consultas("/usuarios/roles/", 2, lambda: crear_rol(f"rol_{Rol.objects.count()}", "Otro"))

    # Ficha de un rol (los permisos salen del registro, en memoria).
    def test_ficha_de_rol(self):
        self.comprobar_consultas("/usuarios/roles/rol/usuario/", 4, None)

    # Excepciones, con más excepciones cada vez.
    def test_excepciones(self):
        def mas():
            persona = crear_usuario_de_prueba(f"Persona {ExcepcionDePermiso.objects.count()}")
            poner_excepcion(persona, self.henares, "grupos.invitar", True, "Prueba")

        self.comprobar_consultas("/usuarios/roles/excepciones/", 3, mas)

    # Explicar, sin elegir nada y con una explicación.
    def test_explicar(self):
        self.comprobar_consultas("/usuarios/roles/explicar/", 2, None)
        self.comprobar_consultas(f"/usuarios/roles/explicar/?alias=Nutria&grupo={self.henares.pk}&permiso=grupos.admitir", 9, None)


class PruebasDeRoles(PruebaDeRoles):
    """Crear un rol, darle permisos, darlo a alguien y borrarlo."""

    # Solo el superadmin entra (de entrada nadie más tiene «administracion.roles»).
    def test_solo_superadmin(self):
        self.client.force_login(self.zorro)
        self.assertContains(self.client.get("/usuarios/roles/"), "administracion.roles", status_code=403)

    # Crear «Tesorería», marcarle un permiso, que valga para quien lo tiene, y no poder borrarlo mientras
    # alguien lo tenga.
    def test_rol_personalizado(self):
        respuesta = self.client.post("/usuarios/roles/", {"codigo": "tesoreria", "nombre": "Tesorería"})
        self.assertRedirects(respuesta, "/usuarios/roles/rol/tesoreria/")
        self.assertContains(self.client.post("/usuarios/roles/", {"codigo": "tesoreria", "nombre": "Otra"}), "Ya existe un rol")
        self.assertContains(self.client.post("/usuarios/roles/", {"codigo": "Tesorería", "nombre": "Otra"}), "Solo minúsculas")
        respuesta = self.client.post("/usuarios/roles/rol/tesoreria/", {"accion": "permisos", "permisos": ["grupos.invitar"]})
        self.assertContains(respuesta, "1 permiso(s) añadido(s)")
        cambiar_rol(Pertenencia.objects.get(usuario=self.nutria), "tesoreria")
        cache.clear()
        self.assertTrue(puede(self.nutria, "grupos.invitar", grupo=self.henares))
        respuesta = self.client.post("/usuarios/roles/rol/tesoreria/", {"accion": "borrar"})
        self.assertContains(respuesta, "1 persona tiene el rol «Tesorería»")
        cambiar_rol(Pertenencia.objects.get(usuario=self.nutria), Pertenencia.USUARIO)
        self.assertRedirects(self.client.post("/usuarios/roles/rol/tesoreria/", {"accion": "borrar"}), "/usuarios/roles/")
        self.assertFalse(Rol.objects.filter(codigo="tesoreria").exists())

    # Quitar un permiso a un rol del sistema vale al momento; los del sistema no se borran.
    def test_rol_del_sistema(self):
        self.assertTrue(puede(self.lince, "grupos.admitir", grupo=self.henares))
        actuales = list(PermisoDeRol.objects.filter(rol_id="admin_grupo").exclude(permiso="grupos.admitir").values_list("permiso", flat=True))
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/usuarios/roles/rol/admin_grupo/", {"accion": "permisos", "permisos": actuales})
        self.assertFalse(puede(self.lince, "grupos.admitir", grupo=self.henares))
        self.assertNotContains(self.client.get("/usuarios/roles/rol/admin_grupo/"), "Borrar el rol")
        self.assertContains(self.client.post("/usuarios/roles/rol/admin_grupo/", {"accion": "borrar"}), "rol del sistema")


class PruebasDeExcepciones(PruebaDeRoles):
    """Dar y quitar permisos sueltos."""

    # Quitar a Lince «grupos.admitir» en su grupo gana a su rol; al borrar la excepción, lo recupera.
    def test_quitar_y_devolver(self):
        datos = {
            "accion": "crear", "alias": "lince", "grupo": self.henares.pk, "permiso": "grupos.admitir",
            "concede": "quitar", "motivo": "Mientras se aclara un conflicto",
        }
        self.assertRedirects(self.client.post("/usuarios/roles/excepciones/", datos), "/usuarios/roles/excepciones/")
        cache.clear()
        self.assertFalse(puede(self.lince, "grupos.admitir", grupo=self.henares))
        self.assertContains(self.client.get("/usuarios/roles/excepciones/"), "Mientras se aclara un conflicto")
        excepcion = ExcepcionDePermiso.objects.get()
        self.client.post("/usuarios/roles/excepciones/", {"accion": "borrar", "excepcion": excepcion.pk})
        cache.clear()
        self.assertTrue(puede(self.lince, "grupos.admitir", grupo=self.henares))
        self.assertContains(self.client.post("/usuarios/roles/excepciones/", {**datos, "alias": "Nadie"}), "No hay nadie con ese alias.")


class PruebasDeExplicar(PruebaDeRoles):
    """«Explicar un permiso» decide igual que puede()."""

    # Para cada persona, grupo y permiso (con un rol personalizado y excepciones de los dos tipos de por
    # medio), la explicación llega al mismo resultado que el cálculo rápido.
    def test_decide_igual_que_puede(self):
        crear_rol("tesoreria", "Tesorería")
        PermisoDeRol.objects.create(rol_id="tesoreria", permiso="grupos.invitar")
        cambiar_rol(Pertenencia.objects.get(usuario=self.garza), "tesoreria")
        poner_excepcion(self.nutria, self.henares, "grupos.invitar", True, "Le toca")
        poner_excepcion(self.lince, self.henares, "grupos.admitir", False, "Pausa")
        poner_excepcion(self.zorro, self.sorbe, "grupos.editar_grupo", False, "Pausa")
        cache.clear()
        personas = [self.usuario, self.lince, self.nutria, self.garza, self.zorro]
        for persona, grupo, permiso in product(personas, [self.general, self.henares, self.sorbe], registro.permisos):
            with self.subTest(persona=str(persona), grupo=str(grupo), permiso=permiso):
                self.assertEqual(explicar_permiso(persona, permiso, grupo).tiene, puede(persona, permiso, grupo=grupo))

    # La pantalla muestra los pasos en lenguaje llano.
    def test_pantalla(self):
        respuesta = self.client.get(f"/usuarios/roles/explicar/?alias=Garza&grupo={self.henares.pk}&permiso=grupos.ver_miembros")
        self.assertContains(respuesta, "Es miembro de «GRU Henares» (está en «GRU Sorbe»)")
        self.assertContains(respuesta, "Resultado: lo tiene.")
