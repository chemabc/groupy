"""
Pruebas de la cercanía (audiencias/cercania.py): quién sale en el selector de personas, en qué bloque y en
qué orden, que no salga nadie que no lo vea, quién puede ver la lista y que el número de consultas no crezca
con las personas.
"""

from django.core.cache import cache
from django.test import TestCase

from audiencias.cercania import cercania, ids_que_ven, ve_la_lista
from audiencias.servicios import crear_privada
from base.pruebas import crear_usuario_de_prueba
from grupos.models import Grupo, Pertenencia
from grupos.servicios import admitir, crear_grupo, crear_organizacion


class PruebasDeCercania(TestCase):
    """
    El árbol de ORG Tajo: GRU Tajo ⊃ GRU Jarama ⊃ GRU Henares ⊃ (GRU Sorbe, GRU Badiel); GRU Jarama ⊃ GRU
    Manzanares; GRU Tajo ⊃ GRU Alberche. Y ORG Ebro aparte. La referencia es GRU Henares.
    """

    # Crea los grupos y las personas: Lince (admin de Henares), Nutria y Pato en Henares (Pato también en
    # Manzanares), Garza en Sorbe, Tejón en Manzanares, Búho en Jarama, Encina en Alberche y Zorro en Ebro.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, raiz = crear_organizacion("ORG Tajo", "GRU Tajo")
        jarama = crear_grupo(cls.tajo, "GRU Jarama", padre=raiz)
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=jarama)
        sorbe = crear_grupo(cls.tajo, "GRU Sorbe", padre=cls.henares)
        crear_grupo(cls.tajo, "GRU Badiel", padre=cls.henares)
        manzanares = crear_grupo(cls.tajo, "GRU Manzanares", padre=jarama)
        alberche = crear_grupo(cls.tajo, "GRU Alberche", padre=raiz)
        _ebro, gru_ebro = crear_organizacion("ORG Ebro", "GRU Ebro")
        cls.personas = {}
        for alias, grupos in [
            ("Lince", [cls.henares]), ("Nutria", [cls.henares]), ("Pato", [cls.henares, manzanares]), ("Garza", [sorbe]),
            ("Tejón", [manzanares]), ("Búho", [jarama]), ("Encina", [alberche]), ("Zorro", [gru_ebro]),
        ]:
            persona = crear_usuario_de_prueba(alias)
            for grupo in grupos:
                admitir(persona, grupo, rol=Pertenencia.ADMIN_GRUPO if alias == "Lince" else Pertenencia.USUARIO)
            cls.personas[alias] = persona
        cls.henares = Grupo.objects.select_related("organizacion").get(pk=cls.henares.pk)

    # Antes de cada prueba: sin cálculos de permisos guardados de otras pruebas.
    def setUp(self):
        cache.clear()

    # Resume una cercanía como [(título, [(grupo, [alias…])…])…], para comparar fácilmente.
    def resumen(self, resultado):
        return [(b.titulo, [(g.nombre, [p.alias for p in g.personas]) for g in b.grupos]) for b in resultado.bloques]

    # «Mi grupo» (grupo:0): el propio grupo y sus subgrupos; Pato sale solo una vez, en el más cercano.
    def test_mi_grupo(self):
        resultado = cercania(self.personas["Lince"], self.henares, clave="grupo:0")
        self.assertEqual(self.resumen(resultado), [
            ("Aquí: GRU Henares", [("GRU Henares", ["Lince", "Nutria", "Pato"])]),
            ("En sus subgrupos", [("GRU Sorbe", ["Garza"])]),
        ])
        self.assertEqual([b.cercania for b in resultado.bloques], ["Muy cerca", "Cerca"])
        self.assertEqual([p.marca for p in resultado.bloques[0].grupos[0].personas], ["admin · tú", "", ""])

    # Hasta el abuelo (grupo:2): un bloque por cada nivel de más arriba, con sus grupos; nunca otra
    # organización.
    def test_niveles_por_encima(self):
        resultado = cercania(self.personas["Lince"], self.henares, clave="grupo:2")
        self.assertEqual(self.resumen(resultado)[2:], [
            ("Un nivel por encima: GRU Jarama", [("GRU Jarama", ["Búho"]), ("GRU Manzanares", ["Tejón"])]),
            ("Dos niveles por encima: GRU Tajo", [("GRU Alberche", ["Encina"])]),
        ])
        self.assertNotIn(self.personas["Zorro"].pk, ids_que_ven(self.henares, clave="organizacion"))
        self.assertEqual(
            ids_que_ven(self.henares, clave="grupo:2"),
            {p.pk for alias, p in self.personas.items() if alias != "Zorro"},
        )

    # Una audiencia privada: solo sus personas, cada una en su escalón.
    def test_audiencia_privada(self):
        privada = crear_privada([self.personas["Nutria"], self.personas["Encina"]], organizacion=self.tajo)
        resultado = cercania(self.personas["Lince"], self.henares, audiencia=privada)
        self.assertEqual(self.resumen(resultado), [
            ("Aquí: GRU Henares", [("GRU Henares", ["Nutria"])]),
            ("Dos niveles por encima: GRU Tajo", [("GRU Alberche", ["Encina"])]),
        ])
        self.assertEqual(ids_que_ven(self.henares, audiencia=privada), {self.personas["Nutria"].pk, self.personas["Encina"].pk})

    # Las cuentas desactivadas no salen ni se pueden elegir.
    def test_sin_cuentas_desactivadas(self):
        type(self.personas["Nutria"]).objects.filter(pk=self.personas["Nutria"].pk).update(activo=False)
        self.assertNotIn(self.personas["Nutria"].pk, ids_que_ven(self.henares, clave="grupo:0"))

    # Si la organización cierra la lista de miembros, una persona cualquiera no ve la lista (solo puede
    # escribir el alias); quien administra el grupo, sí.
    def test_lista_cerrada(self):
        self.assertTrue(ve_la_lista(self.personas["Nutria"], self.henares))
        self.tajo.miembros_ven_miembros = False
        self.tajo.save()
        henares = Grupo.objects.select_related("organizacion").get(pk=self.henares.pk)
        resultado = cercania(self.personas["Nutria"], henares, clave="grupo:0")
        self.assertEqual((resultado.ve_la_lista, resultado.bloques), (False, ()))
        self.assertTrue(ve_la_lista(self.personas["Lince"], henares))

    # El número de consultas no crece con las personas.
    def test_consultas(self):
        lince = self.personas["Lince"]
        cercania(lince, self.henares, clave="organizacion")
        with self.assertNumQueries(5):
            cercania(lince, self.henares, clave="organizacion")
        for numero in range(20):
            admitir(crear_usuario_de_prueba(f"Nueva {numero}"), self.henares)
        with self.assertNumQueries(5):
            resultado = cercania(lince, self.henares, clave="organizacion")
        self.assertEqual(resultado.bloques[0].total, 23)
