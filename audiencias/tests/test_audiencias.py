"""
Pruebas del módulo «audiencias»: quién ve qué, la configuración de cada organización, la regla entre
organizaciones (solo con invitación hecha y aceptada con privilegios), la caché y las frases que explican
a quién llega cada cosa.
"""

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase

from audiencias.models import Audiencia, ConfiguracionDeVisibilidad
from audiencias.servicios import (
    anadir_personas,
    audiencia_de_grupos,
    audiencia_para,
    crear_privada,
    describir,
    filtrar_visibles,
    puede_ver,
    visibles_para,
)
from base.contrato import Ancla
from base.pruebas import contratos_de_prueba, crear_usuario_de_prueba, modulo_falso
from grupos.models import Pertenencia
from grupos.servicios import admitir, crear_grupo, crear_organizacion, invitar, responder_invitacion, retirar_invitacion
from permisos.servicios import SinPermiso

# Módulo de mentira que declara el ancla «alfa.proyecto», lo que se invita en estas pruebas.
ALFA = modulo_falso("alfa", anclas=(Ancla("alfa.proyecto", "auth.Group", "Un proyecto de mentira"),))
# El proyecto 7 de mentira.
PROYECTO = ("alfa.proyecto", 7)


class PruebaConDosOrganizaciones(TestCase):
    """
    Base: ORG Tajo (GRU Tajo ⊃ GRU Jarama ⊃ GRU Henares, y GRU Tajo ⊃ GRU Alberche) y ORG Ebro
    (GRU Ebro ⊃ GRU Segre). Nutria está en Henares; Lince es admin de Henares; Búho está en Alberche;
    Zorro es admin de Segre y Grulla, usuaria de Segre.
    """

    # Crea los grupos y las personas.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.jarama = crear_grupo(cls.tajo, "GRU Jarama", padre=cls.general)
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.jarama)
        cls.alberche = crear_grupo(cls.tajo, "GRU Alberche", padre=cls.general)
        cls.ebro, cls.general_ebro = crear_organizacion("ORG Ebro", "GRU Ebro")
        cls.segre = crear_grupo(cls.ebro, "GRU Segre", padre=cls.general_ebro)
        cls.nutria, cls.lince, cls.buho, cls.zorro, cls.grulla = (
            crear_usuario_de_prueba(alias) for alias in ["Nutria", "Lince", "Búho", "Zorro", "Grulla"]
        )
        admitir(cls.nutria, cls.henares)
        admitir(cls.lince, cls.henares, rol=Pertenencia.ADMIN_GRUPO)
        admitir(cls.buho, cls.alberche)
        admitir(cls.zorro, cls.segre, rol=Pertenencia.ADMIN_GRUPO)
        admitir(cls.grulla, cls.segre)

    # Antes de cada prueba: caché vacía y el ancla de mentira en el registro.
    def setUp(self):
        cache.clear()
        contexto = contratos_de_prueba(ALFA)
        contexto.__enter__()
        self.addCleanup(contexto.__exit__, None, None, None)

    # Quiénes de la lista ven la audiencia, como conjunto de alias.
    def quienes_ven(self, audiencia, *personas):
        return {str(persona) for persona in personas if puede_ver(persona, audiencia)}

    # Todas las personas de la base.
    def todas(self):
        return (self.nutria, self.lince, self.buho, self.zorro, self.grulla)

    # Abre una invitación de Henares (la hace Lince, su admin) a Segre para el proyecto 7.
    def invitacion(self):
        return invitar(*PROYECTO, self.henares, self.segre, self.lince)


class PruebasDeNiveles(PruebaConDosOrganizaciones):
    """Comprueba cada nivel de visibilidad y lo que permite la configuración de la organización."""

    # «Mi grupo» (Jarama): lo ven sus miembros y los de sus subgrupos (Henares), no los de al lado.
    def test_mi_grupo_y_subgrupos(self):
        audiencia = audiencia_para("grupo", self.jarama)
        self.assertEqual(self.quienes_ven(audiencia, *self.todas()), {"Nutria", "Lince"})

    # Subir al padre se permite por defecto; al abuelo, solo si la organización lo permite.
    def test_altura(self):
        padre = audiencia_para("grupo", self.henares, altura=1)
        self.assertEqual(padre.grupos.get().grupo, self.jarama)
        with self.assertRaisesMessage(ValidationError, "como mucho 1 nivel"):
            audiencia_para("grupo", self.henares, altura=2)
        ConfiguracionDeVisibilidad.objects.create(organizacion=self.tajo, altura_maxima=2)
        abuelo = audiencia_para("grupo", self.henares, altura=2)
        self.assertEqual(self.quienes_ven(abuelo, *self.todas()), {"Nutria", "Lince", "Búho"})

    # «Toda la organización» y lo público, solo si la organización lo permite.
    def test_organizacion_y_publico(self):
        with self.assertRaisesMessage(ValidationError, "no permite publicar para toda la organización"):
            audiencia_para("organizacion", self.henares)
        with self.assertRaisesMessage(ValidationError, "no permite publicar para cualquiera"):
            audiencia_para("publico", self.henares)
        ConfiguracionDeVisibilidad.objects.create(
            organizacion=self.tajo, permite_toda_la_organizacion=True, permite_publico=True
        )
        organizacion = audiencia_para("organizacion", self.henares)
        self.assertEqual(self.quienes_ven(organizacion, *self.todas()), {"Nutria", "Lince", "Búho"})
        # Una audiencia pública nueva cambia lo que ve todo el mundo: la caché se invalida al terminar.
        with self.captureOnCommitCallbacks(execute=True):
            publica = audiencia_para("publico", self.henares)
        self.assertTrue(puede_ver(self.zorro, publica))
        from django.contrib.auth.models import AnonymousUser

        self.assertTrue(puede_ver(AnonymousUser(), publica))
        self.assertFalse(puede_ver(AnonymousUser(), organizacion))

    # Dos elecciones iguales comparten la misma audiencia, sin importar el orden.
    def test_se_comparten(self):
        una = audiencia_de_grupos([self.jarama, self.alberche], self.tajo)
        otra = audiencia_de_grupos([self.alberche, self.jarama], self.tajo)
        self.assertEqual(una.pk, otra.pk)

    # Lo privado solo lo ven las personas de la lista; al añadir a alguien, lo ve.
    def test_privado(self):
        audiencia = audiencia_para("privado", self.henares, personas=[self.nutria])
        self.assertEqual(self.quienes_ven(audiencia, *self.todas()), {"Nutria"})
        with self.captureOnCommitCallbacks(execute=True):
            anadir_personas(audiencia, [self.buho])
        self.assertEqual(self.quienes_ven(audiencia, *self.todas()), {"Nutria", "Búho"})

    # El superadmin ve todo menos lo personal de otras personas.
    def test_superadmin(self):
        aguila = crear_usuario_de_prueba("Águila", es_superadmin=True)
        de_grupo = audiencia_para("grupo", self.henares)
        personal = crear_privada([self.nutria], personal=True)
        self.assertTrue(puede_ver(aguila, de_grupo))
        self.assertFalse(puede_ver(aguila, personal))
        self.assertTrue(puede_ver(self.nutria, personal))
        self.assertEqual(set(filtrar_visibles(Audiencia.objects.all(), aguila, campo="")), {de_grupo})


class PruebasEntreOrganizaciones(PruebaConDosOrganizaciones):
    """La regla dura: nada pasa de una organización a otra sin invitación hecha y aceptada con privilegios."""

    # Sin invitación, ni el grupo ni sus personas pueden entrar.
    def test_sin_invitacion(self):
        with self.assertRaisesMessage(ValidationError, "«GRU Segre» es de otra organización"):
            audiencia_de_grupos([self.henares, self.segre], self.tajo, ancla=PROYECTO)
        with self.assertRaisesMessage(ValidationError, "«Grulla» no está en «ORG Tajo»"):
            crear_privada([self.nutria, self.grulla], organizacion=self.tajo, ancla=PROYECTO)

    # Con la invitación pendiente, tampoco.
    def test_con_invitacion_pendiente(self):
        self.invitacion()
        with self.assertRaises(ValidationError):
            audiencia_de_grupos([self.henares, self.segre], self.tajo, ancla=PROYECTO)

    # Invitar exige privilegios: una usuaria normal no puede.
    def test_invitar_exige_privilegios(self):
        with self.assertRaisesMessage(SinPermiso, "grupos.invitar"):
            invitar(*PROYECTO, self.henares, self.segre, self.nutria)

    # Aceptada por el admin del grupo invitado: el grupo y sus personas entran, solo para ese proyecto.
    def test_con_invitacion_aceptada(self):
        responder_invitacion(self.invitacion(), self.zorro, acepta=True)
        audiencia = audiencia_de_grupos([self.henares, self.segre], self.tajo, ancla=PROYECTO)
        self.assertEqual(self.quienes_ven(audiencia, *self.todas()), {"Nutria", "Lince", "Zorro", "Grulla"})
        with self.captureOnCommitCallbacks(execute=True):
            privada = crear_privada([self.nutria, self.grulla], organizacion=self.tajo, ancla=PROYECTO)
        self.assertTrue(puede_ver(self.grulla, privada))
        # Para otro proyecto no vale: esa invitación era solo para el 7.
        with self.assertRaises(ValidationError):
            audiencia_de_grupos([self.segre], self.tajo, ancla=("alfa.proyecto", 8))
        # Y el grupo que contiene al invitado (GRU Ebro) no entra.
        with self.assertRaises(ValidationError):
            audiencia_de_grupos([self.general_ebro], self.tajo, ancla=PROYECTO)

    # La audiencia con grupos invitados no se comparte con otras cosas iguales sin invitación.
    def test_no_se_comparte(self):
        responder_invitacion(self.invitacion(), self.zorro, acepta=True)
        con_invitados = audiencia_de_grupos([self.henares, self.segre], self.tajo, ancla=PROYECTO)
        self.assertIn("@alfa.proyecto:7", con_invitados.huella)

    # Una invitación rechazada o retirada no abre nada.
    def test_rechazada_o_retirada(self):
        responder_invitacion(self.invitacion(), self.zorro, acepta=False)
        retirar_invitacion(self.invitacion(), self.lince)
        with self.assertRaises(ValidationError):
            audiencia_de_grupos([self.segre], self.tajo, ancla=PROYECTO)


class PruebasDeCacheYFrases(PruebaConDosOrganizaciones):
    """El coste del cálculo, la invalidación y las frases que explican a quién llega."""

    # Calcular cuesta 2 consultas; después, preguntar no cuesta nada.
    def test_consultas(self):
        audiencia = audiencia_para("grupo", self.jarama)
        with self.assertNumQueries(2):
            visibles_para(self.nutria)
        with self.assertNumQueries(0):
            self.assertTrue(puede_ver(self.nutria, audiencia))

    # Al entrar en un grupo, se ve lo de ese grupo.
    def test_se_invalida(self):
        audiencia = audiencia_para("grupo", self.alberche)
        self.assertFalse(puede_ver(self.nutria, audiencia))
        with self.captureOnCommitCallbacks(execute=True):
            admitir(self.nutria, self.alberche)
        self.assertTrue(puede_ver(self.nutria, audiencia))

    # La frase dice a quién llega y solo cuenta las personas si son 5 o más.
    def test_frases(self):
        jarama = audiencia_para("grupo", self.jarama)
        self.assertEqual(describir(jarama), "Lo ven las personas de GRU Jarama y de sus subgrupos (menos de 5 personas).")
        for numero in range(4):
            admitir(crear_usuario_de_prueba(f"Extra {numero}"), self.henares)
        self.assertEqual(describir(jarama), "Lo ven las personas de GRU Jarama y de sus subgrupos (6 personas).")
        self.assertEqual(describir(crear_privada([self.nutria], personal=True)), "Solo lo ves tú.")
