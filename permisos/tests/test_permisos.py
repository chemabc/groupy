"""
Pruebas del módulo «permisos»: herencia de la pertenencia, roles que no se heredan, admin de
organización, roles personalizados, excepciones, cometidos, caché, explicación de lo que falta,
pantalla 403 y sincronización de los permisos por defecto.
"""

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from base.contrato import Ancla, Cometido as FichaDeCometido, Permiso
from base.pruebas import contratos_de_prueba, crear_usuario_de_prueba, modulo_falso
from grupos.servicios import admitir, crear_grupo, crear_organizacion, nombrar_admin_de_organizacion, sacar
from permisos.models import ExcepcionDePermiso, PermisoDeRol, Rol
from permisos.servicios import (
    PermisoNoDeclarado,
    SinPermiso,
    asignar_cometido,
    cometidos_en_grupo,
    exigir,
    permisos_de,
    puede,
    sincronizar_permisos,
    tiene_cometido,
)


class PruebaConGrupos(TestCase):
    """
    Base de las pruebas: ORG Tajo (GRU Tajo ⊃ GRU Jarama ⊃ GRU Henares) y ORG Ebro (GRU Segre).
    Nutria es usuaria de Henares; Lince, admin de Henares; Zorro, admin de ORG Tajo (está en Jarama).
    En estas pruebas, el rol «usuario» tiene «grupos.invitar», para tener un permiso de cualquier
    miembro con el que probar la herencia (en la aplicación es solo de los admins).
    """

    # Crea los grupos y las personas, y da «grupos.invitar» al rol «usuario».
    @classmethod
    def setUpTestData(cls):
        PermisoDeRol.objects.get_or_create(rol_id="usuario", permiso="grupos.invitar")
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.jarama = crear_grupo(cls.tajo, "GRU Jarama", padre=cls.general)
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.jarama)
        cls.ebro, cls.segre = crear_organizacion("ORG Ebro", "GRU Segre")
        cls.nutria = crear_usuario_de_prueba("Nutria")
        cls.lince = crear_usuario_de_prueba("Lince")
        cls.zorro = crear_usuario_de_prueba("Zorro")
        admitir(cls.nutria, cls.henares)
        admitir(cls.lince, cls.henares, rol="admin_grupo")
        admitir(cls.zorro, cls.jarama)
        nombrar_admin_de_organizacion(cls.zorro, cls.tajo)

    # Antes de cada prueba, la caché vacía (pasaría de una prueba a otra).
    def setUp(self):
        cache.clear()


class PruebasDeLasReglas(PruebaConGrupos):
    """Comprueba las reglas del cálculo."""

    # La pertenencia se hereda hacia arriba: Nutria puede invitar en Henares, Jarama y Tajo, no en Segre.
    def test_la_pertenencia_se_hereda_hacia_arriba(self):
        for grupo, esperado in [(self.henares, True), (self.jarama, True), (self.general, True), (self.segre, False)]:
            with self.subTest(grupo=grupo):
                self.assertEqual(puede(self.nutria, "grupos.invitar", grupo=grupo), esperado)

    # El rol de admin del grupo vale solo en su grupo.
    def test_admin_de_grupo_no_se_hereda(self):
        self.assertTrue(puede(self.lince, "grupos.editar_grupo", grupo=self.henares))
        self.assertFalse(puede(self.lince, "grupos.editar_grupo", grupo=self.jarama))
        self.assertFalse(puede(self.nutria, "grupos.editar_grupo", grupo=self.henares))

    # El admin de la organización puede en ella y en todos sus grupos, no en otras.
    def test_admin_de_organizacion(self):
        for grupo in [self.general, self.jarama, self.henares]:
            self.assertTrue(puede(self.zorro, "grupos.editar_grupo", grupo=grupo))
        self.assertTrue(puede(self.zorro, "grupos.editar_organizacion", organizacion=self.tajo))
        self.assertFalse(puede(self.zorro, "grupos.editar_organizacion", organizacion=self.ebro))
        self.assertFalse(puede(self.zorro, "grupos.editar_grupo", grupo=self.segre))

    # El superadmin puede todo, sin consultas.
    def test_superadmin(self):
        aguila = crear_usuario_de_prueba("Águila", es_superadmin=True)
        with self.assertNumQueries(0):
            self.assertTrue(puede(aguila, "grupos.editar_organizacion", organizacion=self.ebro))

    # Preguntar por un permiso que nadie declara es un error (suele ser una errata).
    def test_permiso_no_declarado(self):
        with self.assertRaises(PermisoNoDeclarado):
            puede(self.nutria, "grupos.volar", grupo=self.henares)

    # Un rol personalizado da sus permisos solo en el grupo donde se tiene.
    def test_rol_personalizado(self):
        tesoreria = Rol.objects.create(codigo="tesoreria", nombre="Tesorería")
        PermisoDeRol.objects.create(rol=tesoreria, permiso="grupos.editar_grupo")
        olmo = crear_usuario_de_prueba("Olmo")
        admitir(olmo, self.jarama, rol="tesoreria")
        self.assertTrue(puede(olmo, "grupos.editar_grupo", grupo=self.jarama))
        self.assertTrue(puede(olmo, "grupos.invitar", grupo=self.jarama))
        self.assertFalse(puede(olmo, "grupos.editar_grupo", grupo=self.general))

    # Un rol que no existe no se puede poner en una pertenencia.
    def test_rol_inexistente(self):
        with self.assertRaisesMessage(ValidationError, "No existe el rol de grupo «pirata»"):
            admitir(crear_usuario_de_prueba("Olmo"), self.jarama, rol="pirata")

    # Las excepciones dan o quitan un permiso solo en su grupo; quitar gana a dar.
    def test_excepciones(self):
        ExcepcionDePermiso.objects.create(usuario=self.nutria, grupo=self.henares, permiso="grupos.admitir", motivo="Acogida")
        ExcepcionDePermiso.objects.create(
            usuario=self.nutria, grupo=self.jarama, permiso="grupos.invitar", concede=False, motivo="Prueba"
        )
        self.assertTrue(puede(self.nutria, "grupos.admitir", grupo=self.henares))
        self.assertFalse(puede(self.nutria, "grupos.admitir", grupo=self.jarama))
        self.assertFalse(puede(self.nutria, "grupos.invitar", grupo=self.jarama))
        self.assertTrue(puede(self.nutria, "grupos.invitar", grupo=self.henares))


class PruebasDeLaCache(PruebaConGrupos):
    """Comprueba el coste del cálculo y que la caché se invalida al cambiar algo."""

    # Calcular cuesta lo mismo con un grupo que con diez; después, preguntar no cuesta consultas.
    def test_consultas(self):
        with self.assertNumQueries(7):
            permisos_de(self.zorro)
        for numero in range(10):
            crear_grupo(self.tajo, f"GRU Extra {numero}", padre=self.henares)
        cache.clear()
        with self.assertNumQueries(7):
            permisos_de(self.zorro)
        with self.assertNumQueries(0):
            puede(self.zorro, "grupos.editar_grupo", grupo=self.henares)

    # Al entrar en un grupo o salir de él, su cálculo se rehace (al terminar la transacción).
    def test_se_invalida_al_cambiar_de_grupo(self):
        self.assertFalse(puede(self.nutria, "grupos.invitar", grupo=self.segre))
        with self.captureOnCommitCallbacks(execute=True):
            admitir(self.nutria, self.segre)
        self.assertTrue(puede(self.nutria, "grupos.invitar", grupo=self.segre))
        with self.captureOnCommitCallbacks(execute=True):
            sacar(self.nutria, self.segre)
        self.assertFalse(puede(self.nutria, "grupos.invitar", grupo=self.segre))

    # Al quitar un permiso a un rol, se rehace el cálculo de todo el mundo.
    def test_se_invalida_al_cambiar_un_rol(self):
        self.assertTrue(puede(self.nutria, "grupos.invitar", grupo=self.henares))
        with self.captureOnCommitCallbacks(execute=True):
            PermisoDeRol.objects.filter(rol_id="usuario", permiso="grupos.invitar").delete()
        self.assertFalse(puede(self.nutria, "grupos.invitar", grupo=self.henares))


# Módulo de mentira con un cometido que da un permiso sobre un debate.
ALFA = modulo_falso(
    "alfa",
    permisos=(Permiso("alfa.moderar", "Moderar un debate"),),
    cometidos=(FichaDeCometido("alfa.facilitacion", "Facilitación", "Modera el debate", permisos=("alfa.moderar",)),),
    anclas=(Ancla("alfa.debate", "auth.Group", "Un debate de mentira"),),
)


class PruebasDeCometidos(PruebaConGrupos):
    """Comprueba los cometidos y los permisos que dan sobre algo concreto."""

    # Añade el módulo de mentira al registro durante la prueba.
    def setUp(self):
        super().setUp()
        contexto = contratos_de_prueba(ALFA)
        contexto.__enter__()
        self.addCleanup(contexto.__exit__, None, None, None)

    # Facilitar el debate 7 da «alfa.moderar» en ese debate, no en otro; y se ve desde el grupo general.
    def test_cometido_da_permiso_en_lo_concreto(self):
        asignar_cometido(self.nutria, "alfa.facilitacion", "alfa.debate", 7, grupo=self.henares)
        self.assertTrue(tiene_cometido(self.nutria, "alfa.facilitacion", "alfa.debate", 7))
        self.assertTrue(puede(self.nutria, "alfa.moderar", ancla=("alfa.debate", 7)))
        self.assertFalse(puede(self.nutria, "alfa.moderar", ancla=("alfa.debate", 8)))
        self.assertEqual([cometido.usuario for cometido in cometidos_en_grupo(self.general)], [self.nutria])

    # No se puede dar un cometido que nadie declara, ni en algo que no es un ancla.
    def test_cometido_no_declarado(self):
        with self.assertRaisesMessage(ValidationError, "Ningún módulo declara el cometido"):
            asignar_cometido(self.nutria, "alfa.nada", "alfa.debate", 7)
        with self.assertRaisesMessage(ValidationError, "como ancla"):
            asignar_cometido(self.nutria, "alfa.facilitacion", "alfa.nada", 7)

    # El registro avisa de un permiso con un rol que no es del sistema y de un cometido que da un
    # permiso que nadie declara.
    def test_errores_de_declaracion(self):
        mal = modulo_falso(
            "beta",
            permisos=(Permiso("beta.algo", "Algo", roles=("pirata",)),),
            cometidos=(FichaDeCometido("beta.cosa", "Cosa", "Cosa", permisos=("beta.nada",)),),
        )
        with contratos_de_prueba(mal) as registro:
            errores = " ".join(registro.errores)
        self.assertIn("«pirata», que no es de los del sistema", errores)
        self.assertIn("da el permiso «beta.nada», que nadie declara", errores)


class PruebasDeLaExplicacion(PruebaConGrupos):
    """Comprueba que la falta de permiso se explica: qué falta, quién lo tiene y a quién pedirlo."""

    # La explicación nombra el permiso, los roles que lo tienen y a sus admins.
    def test_explicacion(self):
        with self.assertRaises(SinPermiso) as error:
            exigir(self.nutria, "grupos.editar_grupo", grupo=self.henares)
        texto = str(error.exception)
        self.assertIn("Para editar los datos del grupo en «GRU Henares» hace falta el permiso «grupos.editar_grupo».", texto)
        self.assertIn("Lo tienen estos roles: Admin de la organización, Admin del grupo.", texto)
        self.assertIn("Lince (admin de GRU Henares), Zorro (admin de ORG Tajo), el superadmin", texto)

    # Una vista con @requiere_permiso responde 403 con la explicación, dentro de la plantilla de la
    # aplicación; con htmx, solo la zona central. Con el permiso, funciona.
    @override_settings(ROOT_URLCONF="permisos.tests.urls_de_prueba")
    def test_pantalla_403(self):
        self.client.force_login(self.nutria)
        respuesta = self.client.get(f"/prueba-permiso/{self.henares.pk}/")
        self.assertContains(respuesta, "No tienes permiso para esto", status_code=403)
        self.assertContains(respuesta, "Lince (admin de GRU Henares)", status_code=403)
        respuesta = self.client.get(f"/prueba-permiso/{self.henares.pk}/", headers={"HX-Request": "true", "HX-Target": "zona"})
        self.assertNotContains(respuesta, "<html", status_code=403)
        self.client.force_login(self.lince)
        self.assertContains(self.client.get(f"/prueba-permiso/{self.henares.pk}/"), "Editando")


class PruebasDeSincronizacion(TestCase):
    """Comprueba que los permisos nuevos reciben sus roles por defecto solo la primera vez."""

    # Un permiso nuevo recibe sus roles; si después se le quita a un rol, no vuelve solo.
    def test_solo_la_primera_vez(self):
        nuevo = modulo_falso("gamma", permisos=(Permiso("gamma.cantar", "Cantar", roles=("usuario", "admin_grupo")),))
        with contratos_de_prueba(nuevo):
            self.assertEqual(sincronizar_permisos(), ["gamma.cantar"])
            roles = set(PermisoDeRol.objects.filter(permiso="gamma.cantar").values_list("rol_id", flat=True))
            self.assertEqual(roles, {"usuario", "admin_grupo"})
            PermisoDeRol.objects.filter(permiso="gamma.cantar", rol_id="usuario").delete()
            self.assertEqual(sincronizar_permisos(), [])
            self.assertFalse(PermisoDeRol.objects.filter(permiso="gamma.cantar", rol_id="usuario").exists())

    # Tras «migrate» (al crear la base de pruebas), los permisos de los contratos ya tienen sus roles.
    def test_tras_migrate(self):
        self.assertTrue(PermisoDeRol.objects.filter(rol_id="admin_grupo", permiso="grupos.invitar").exists())
        self.assertFalse(PermisoDeRol.objects.filter(rol_id="usuario", permiso="grupos.invitar").exists())
        self.assertTrue(PermisoDeRol.objects.filter(rol_id="admin_org", permiso="permisos.dar_excepciones").exists())
