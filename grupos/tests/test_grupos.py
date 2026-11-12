"""
Pruebas del módulo «grupos»: tabla de cierre, pertenencias, asamblea base, admin de organización,
invitaciones entre organizaciones y datos de ejemplo.
"""

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings

from base.contrato import Ancla, Escucha, Modo
from base.pruebas import contratos_de_prueba, crear_usuario_de_prueba, modulo_falso
from eventos_sw.tests import receptores
from grupos import ejemplos
from grupos.models import Contencion, Grupo, InvitacionDeGrupo, Organizacion, Pertenencia
from grupos.servicios import (
    admitir,
    cambiar_asamblea_base,
    crear_grupo,
    crear_organizacion,
    grupos_de,
    invitar,
    nombrar_admin_de_organizacion,
    responder_invitacion,
    retirar_invitacion,
    sacar,
)


# Devuelve los antecesores de un grupo como {nombre: distancia}, leídos de la tabla de cierre.
def antecesores(grupo):
    return dict(Contencion.objects.filter(descendiente=grupo).values_list("antecesor__nombre", "distancia"))


class PruebasDeLaTablaDeCierre(TestCase):
    """Comprueba que la tabla de cierre se mantiene sola al crear y mover grupos."""

    # Crea «ORG Tajo» con Jarama (que contiene a Henares, que contiene a Badiel) y Alberche.
    def setUp(self):
        self.tajo, self.jarama = crear_organizacion("ORG Tajo", "GRU Jarama")
        self.henares = crear_grupo(self.tajo, "GRU Henares", padre=self.jarama)
        self.badiel = crear_grupo(self.tajo, "GRU Badiel", padre=self.henares)
        self.alberche = crear_grupo(self.tajo, "GRU Alberche")

    # Cada grupo se contiene a sí mismo (distancia 0) y está dentro de su padre y de su abuelo.
    def test_al_crear(self):
        self.assertEqual(antecesores(self.badiel), {"GRU Badiel": 0, "GRU Henares": 1, "GRU Jarama": 2})
        self.assertEqual(antecesores(self.alberche), {"GRU Alberche": 0})

    # Mover Henares (con su subgrupo Badiel) bajo Alberche: los dos dejan de estar en Jarama.
    def test_al_mover_un_subarbol(self):
        self.henares.padre = self.alberche
        self.henares.save()
        self.assertEqual(antecesores(self.henares), {"GRU Henares": 0, "GRU Alberche": 1})
        self.assertEqual(antecesores(self.badiel), {"GRU Badiel": 0, "GRU Henares": 1, "GRU Alberche": 2})

    # Convertirlo en grupo principal lo saca de todos sus antecesores.
    def test_al_soltar(self):
        henares = Grupo.objects.get(pk=self.henares.pk)
        henares.padre = None
        henares.save()
        self.assertEqual(antecesores(self.badiel), {"GRU Badiel": 0, "GRU Henares": 1})

    # En orden de árbol cada grupo va justo después de su padre, y los hermanos por orden alfabético sin
    # contar tildes («Órbigo» entre «Esla» y «Pisuerga»), aunque un hermano empiece igual que el padre.
    def test_orden_de_arbol(self):
        duero, general = crear_organizacion("ORG Duero", "GRU Duero")
        for nombre in ["GRU Pisuerga", "GRU Órbigo", "GRU Esla", "GRU Duero Alto"]:
            crear_grupo(duero, nombre, padre=general)
        adaja = crear_grupo(duero, "GRU Adaja", padre=general)
        crear_grupo(duero, "GRU Eresma", padre=adaja)
        nombres = list(Grupo.objects.filter(organizacion=duero).en_orden_de_arbol().values_list("camino", flat=True))
        self.assertEqual(nombres, [
            "GRU Duero",
            "GRU Duero › GRU Adaja",
            "GRU Duero › GRU Adaja › GRU Eresma",
            "GRU Duero › GRU Duero Alto",
            "GRU Duero › GRU Esla",
            "GRU Duero › GRU Órbigo",
            "GRU Duero › GRU Pisuerga",
        ])

    # Un grupo no puede quedar dentro de sí mismo ni de uno de sus subgrupos.
    def test_sin_circulos(self):
        jarama = Grupo.objects.get(pk=self.jarama.pk)
        jarama.padre = self.badiel
        with self.assertRaisesMessage(ValidationError, "ni uno de sus subgrupos"):
            jarama.save()

    # El padre debe ser de la misma organización.
    def test_padre_de_otra_organizacion(self):
        _ebro, segre = crear_organizacion("ORG Ebro", "GRU Segre")
        with self.assertRaisesMessage(ValidationError, "misma organización"):
            crear_grupo(self.tajo, "GRU Raro", padre=segre)


class PruebasDePertenencias(TestCase):
    """Comprueba pertenencias, herencia hacia arriba, asamblea base y admin de organización."""

    # Crea Tajo (Jarama ⊃ Henares) y Ebro (Segre), y dos usuarios.
    def setUp(self):
        self.tajo, self.jarama = crear_organizacion("ORG Tajo", "GRU Jarama")
        self.henares = crear_grupo(self.tajo, "GRU Henares", padre=self.jarama)
        self.ebro, self.segre = crear_organizacion("ORG Ebro", "GRU Segre")
        self.lince = crear_usuario_de_prueba("Lince")
        self.nutria = crear_usuario_de_prueba("Nutria")

    # Quien está en Henares es miembro de Henares y de Jarama (que lo contiene), con una sola consulta.
    def test_la_pertenencia_se_hereda_hacia_arriba(self):
        admitir(self.lince, self.henares, es_base=True)
        admitir(self.lince, self.segre)
        with self.assertNumQueries(1):
            ids = grupos_de(self.lince)
        self.assertEqual(ids, {self.henares.pk, self.jarama.pk, self.segre.pk})

    # Solo una asamblea base por persona, en toda la plataforma; se puede cambiar.
    def test_una_asamblea_base(self):
        admitir(self.lince, self.henares, es_base=True)
        with self.assertRaisesMessage(ValidationError, "ya tiene otra asamblea base"):
            admitir(self.lince, self.segre, es_base=True)
        admitir(self.lince, self.segre)
        cambiar_asamblea_base(self.lince, self.segre)
        self.assertEqual(Pertenencia.objects.get(usuario=self.lince, es_base=True).grupo, self.segre)

    # Para ser admin de una organización hay que estar en uno de sus grupos; al salir del último, deja de
    # serlo.
    def test_admin_de_organizacion(self):
        with self.assertRaisesMessage(ValidationError, "estar en alguno de sus grupos"):
            nombrar_admin_de_organizacion(self.lince, self.tajo)
        admitir(self.lince, self.henares)
        nombrar_admin_de_organizacion(self.lince, self.tajo)
        sacar(self.lince, self.henares)
        self.assertFalse(self.tajo.admins.exists())


# Módulo de mentira que declara el ancla «alfa.proyecto» (lo que se invita) y escucha la aceptación.
ALFA = modulo_falso(
    "alfa",
    anclas=(Ancla("alfa.proyecto", "auth.Group", "Un proyecto de mentira"),),
    escucha=(Escucha("grupos.invitacion_aceptada", "eventos_sw.tests.receptores.anotar", Modo.SINCRONO),),
)


class PruebasDeInvitaciones(TestCase):
    """Comprueba las invitaciones a grupos de otra organización (proyectos conjuntos)."""

    # Tajo (Jarama, con Lince) invita a Ebro (Segre, con Zorro de admin y Grulla de usuaria).
    def setUp(self):
        contexto = contratos_de_prueba(ALFA)
        contexto.__enter__()
        self.addCleanup(contexto.__exit__, None, None, None)
        receptores.recibidos.clear()
        self.tajo, self.jarama = crear_organizacion("ORG Tajo", "GRU Jarama")
        self.ebro, self.segre = crear_organizacion("ORG Ebro", "GRU Segre")
        self.lince = crear_usuario_de_prueba("Lince")
        self.zorro = crear_usuario_de_prueba("Zorro")
        self.grulla = crear_usuario_de_prueba("Grulla")
        admitir(self.lince, self.jarama)
        admitir(self.zorro, self.segre, rol=Pertenencia.ADMIN_GRUPO)
        admitir(self.grulla, self.segre)

    # Crea la invitación de Jarama a Segre para el proyecto 7.
    def invitar(self):
        return invitar("alfa.proyecto", 7, self.jarama, self.segre, self.lince, "¿Hacemos juntas la campaña?")

    # La acepta el admin del grupo invitado, y se avisa a quien lleve el proyecto.
    def test_aceptar(self):
        invitacion = self.invitar()
        responder_invitacion(invitacion, self.zorro, acepta=True)
        self.assertEqual(invitacion.estado, InvitacionDeGrupo.ACEPTADA)
        self.assertEqual(receptores.recibidos, [invitacion.datos_del_aviso()])

    # Una usuaria normal del grupo invitado no puede responder.
    def test_solo_responde_el_admin(self):
        invitacion = self.invitar()
        with self.assertRaisesMessage(ValidationError, "Solo el admin de «GRU Segre»"):
            responder_invitacion(invitacion, self.grulla, acepta=True)

    # Una invitación respondida o retirada ya no se puede responder.
    def test_no_se_responde_dos_veces(self):
        invitacion = self.invitar()
        retirar_invitacion(invitacion, self.lince)
        with self.assertRaisesMessage(ValidationError, "ya está retirada"):
            responder_invitacion(invitacion, self.zorro, acepta=False)

    # No se invita dentro de la misma organización, ni a algo que no es un ancla, ni sin ser del grupo
    # que invita, ni dos veces a la vez.
    def test_invitaciones_no_validas(self):
        henares = crear_grupo(self.tajo, "GRU Henares")
        casos = [
            (("alfa.proyecto", 7, self.jarama, henares, self.lince), "otra organización"),
            (("alfa.nada", 7, self.jarama, self.segre, self.lince), "ningún módulo lo declara"),
            (("alfa.proyecto", 7, self.jarama, self.segre, self.zorro), "hay que ser miembro"),
        ]
        for argumentos, mensaje in casos:
            with self.subTest(mensaje=mensaje), self.assertRaisesMessage(ValidationError, mensaje):
                invitar(*argumentos)
        self.invitar()
        with self.assertRaisesMessage(ValidationError, "ya tiene una invitación pendiente"):
            self.invitar()


class PruebasDeLosEjemplos(TestCase):
    """Comprueba las organizaciones y grupos de ejemplo."""

    # Se crean con los usuarios de ejemplo, sin duplicarse, y se borran del todo.
    @override_settings(DEBUG=True)
    def test_crear_y_borrar(self):
        call_command("ejemplos", "crear", stdout=None)
        call_command("ejemplos", "crear", stdout=None)
        self.assertEqual(Organizacion.objects.count(), len(ejemplos.ESTRUCTURA))
        henares = Grupo.objects.get(nombre="GRU Henares")
        self.assertEqual(antecesores(henares), {"GRU Henares": 0, "GRU Jarama": 1, "GRU Tajo": 2})
        # Cinco niveles: Ebro ⊃ Segre ⊃ Cinca ⊃ Ésera ⊃ Isábena.
        self.assertEqual(antecesores(Grupo.objects.get(nombre="GRU Isábena"))["GRU Ebro"], 4)
        lince = Pertenencia.objects.get(usuario__alias="Lince", es_base=True)
        self.assertEqual((lince.grupo.nombre, lince.rol), ("GRU Henares", Pertenencia.ADMIN_GRUPO))
        self.assertEqual(Organizacion.objects.get(nombre="ORG Tajo").admins.get().usuario.alias, "Lince")
        call_command("ejemplos", "borrar", stdout=None)
        self.assertFalse(Organizacion.objects.exists() or Grupo.objects.exists() or Pertenencia.objects.exists())
