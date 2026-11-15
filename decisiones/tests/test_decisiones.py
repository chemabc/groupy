"""
Pruebas del registro de decisiones: se llena solo con los eventos_sw de los otros módulos (aquí se emiten a
mano, con los mismos datos), cada persona ve las de sus audiencias, la administración marca una como
sustituida y la lista cuesta lo mismo con más decisiones.

Estructura: ORG Tajo (GRU Tajo ⊃ GRU Henares). Lince es admin de GRU Henares; Nutria, miembro; Erizo, de otra
organización.
"""

from django.db import transaction

from audiencias.selector import audiencia_de
from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from decisiones.models import Decision
from eventos_sw.servicios import emitir
from grupos.models import Pertenencia
from grupos.servicios import admitir, crear_grupo, crear_organizacion


class PruebasDeDecisiones(PruebaDePantalla):
    """El registro, visto por Nutria."""

    # Crea la estructura y la audiencia «GRU Henares».
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
        cls.audiencia = audiencia_de("grupo:0", cls.henares)
        cls.usuario = cls.nutria

    # Anuncia una decisión como lo haría un acta aprobada.
    def anunciar(self, texto, origen_id=1):
        with transaction.atomic():
            emitir(
                "documentos.acuerdo_tomado", texto=texto, forma="consenso", detalle="", grupo_id=self.henares.pk,
                audiencia_id=self.audiencia.pk, origen_tipo="documentos.documento", origen_id=origen_id, enlace="/documentos/1/", tomada=None,
            )
        return Decision.objects.get(texto=texto)

    # El eventos_sw crea la decisión; si llega dos veces, no se repite.
    def test_se_llena_sola(self):
        self.anunciar("Cambiamos de local")
        self.anunciar("Cambiamos de local")
        self.assertEqual(Decision.objects.count(), 1)

    # Nutria la ve en la lista; Erizo (de otra organización), no.
    def test_quien_ve(self):
        decision = self.anunciar("Huerto en el solar")
        self.assertContains(self.client.get("/decisiones/"), "Huerto en el solar")
        self.client.force_login(self.erizo)
        self.assertNotContains(self.client.get("/decisiones/"), "Huerto en el solar")
        self.assertEqual(self.client.get(f"/decisiones/{decision.pk}/").status_code, 404)

    # Lince (admin) marca la antigua como sustituida por la nueva: sale de «Vigentes» y sigue en «Todas».
    # Nutria no puede hacerlo.
    def test_sustituir(self):
        antigua = self.anunciar("Asamblea los martes", origen_id=1)
        nueva = self.anunciar("Asamblea los jueves", origen_id=2)
        self.assertEqual(self.client.post(f"/decisiones/{antigua.pk}/", {"nueva": nueva.pk}).status_code, 403)
        self.client.force_login(self.lince)
        self.client.post(f"/decisiones/{antigua.pk}/", {"nueva": nueva.pk})
        antigua.refresh_from_db()
        self.assertEqual(antigua.sustituida_por, nueva)
        self.assertNotContains(self.client.get("/decisiones/"), "Asamblea los martes")
        self.assertContains(self.client.get("/decisiones/todas/"), "Asamblea los martes")

    # La lista cuesta lo mismo con más decisiones.
    def test_consultas(self):
        self.anunciar("Primera")
        self.comprobar_consultas("/decisiones/", 2, lambda: self.anunciar(f"Otra {Decision.objects.count()}", origen_id=Decision.objects.count() + 1))
