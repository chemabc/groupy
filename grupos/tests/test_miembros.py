"""
Pruebas de «Administrar → Grupos que administro → Miembros» (grupos/miembros.py) y de la inactividad
(grupos/inactividad.py, usuarios/middleware.py ApuntarActividad y «Mi organización → Inactividad»).

Estructura: ORG Tajo (GRU Tajo ⊃ GRU Henares ⊃ GRU Sorbe). Lince administra GRU Henares (admin_grupo);
Nutria está en GRU Henares (su base) y en GRU Sorbe; Garza en GRU Sorbe. Erizo, en ORG Ebro.
"""

from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from grupos import inactividad
from grupos.models import AdminDeOrganizacion, LimiteDeInactividad, Pertenencia
from grupos.servicios import admitir, crear_grupo, crear_organizacion
from usuarios.models import Usuario


class PruebaDeMiembros(PruebaDePantalla):
    """Base con la estructura del principio del fichero; la sesión es de Lince."""

    # Crea la estructura.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.general)
        cls.sorbe = crear_grupo(cls.tajo, "GRU Sorbe", padre=cls.henares)
        cls.ebro, cls.gru_ebro = crear_organizacion("ORG Ebro", "GRU Ebro")
        cls.lince, cls.nutria, cls.garza, cls.erizo = (crear_usuario_de_prueba(a) for a in ("Lince", "Nutria", "Garza", "Erizo"))
        admitir(cls.lince, cls.henares, rol=Pertenencia.ADMIN_GRUPO, es_base=True)
        admitir(cls.nutria, cls.henares, es_base=True)
        admitir(cls.nutria, cls.sorbe)
        admitir(cls.garza, cls.sorbe, es_base=True)
        admitir(cls.erizo, cls.gru_ebro, es_base=True)
        cls.usuario = cls.lince

    # Inicia sesión como otra persona.
    def como(self, usuario):
        cache.clear()
        self.client.force_login(usuario)


class PruebasDeLaPantalla(PruebaDeMiembros):
    """Qué se ve y qué se puede hacer desde «Miembros»."""

    # Lince ve a las personas de GRU Henares y de GRU Sorbe (una fila por pertenencia), no las de otra
    # organización; las filas que no son la asamblea base salen tenues. Nutria no entra.
    def test_lo_que_se_ve(self):
        respuesta = self.client.get("/organizaciones/miembros/")
        filas = respuesta.context["tabla"].filas
        self.assertEqual(sorted((f["alias"], f["grupo"].split(" › ")[-1]) for f in filas), [
            ("Garza", "GRU Sorbe"), ("Lince", "GRU Henares"), ("Nutria", "GRU Henares"), ("Nutria", "GRU Sorbe"),
        ])
        tenue = [f for f in filas if f["_clase"]]
        self.assertEqual([(f["alias"], f["grupo"].split(" › ")[-1]) for f in tenue], [("Nutria", "GRU Sorbe")])
        self.assertContains(respuesta, "opacity-60")
        self.como(self.nutria)
        self.assertEqual(self.client.get("/organizaciones/miembros/").status_code, 403)

    # Lince puede gestionar GRU Henares (cambiar el rol de Nutria, sacarla), pero no GRU Sorbe (el permiso de
    # admitir es de su grupo, no de los subgrupos) ni a sí mismo como admin (hacer o deshacer admins pide
    # «grupos.nombrar_admin_grupo»).
    def test_de_una_en_una(self):
        nutria_en_henares = Pertenencia.objects.get(usuario=self.nutria, grupo=self.henares)
        garza = Pertenencia.objects.get(usuario=self.garza)
        filas = {(f["alias"], f["grupo"].split(" › ")[-1]): f for f in self.client.get("/organizaciones/miembros/").context["tabla"].filas}
        self.assertTrue(filas[("Nutria", "GRU Henares")]["gestiona"])
        self.assertFalse(filas[("Garza", "GRU Sorbe")]["gestiona"])
        self.assertFalse(filas[("Lince", "GRU Henares")]["gestiona"])
        self.client.post("/organizaciones/miembros/", {"accion": f"sacar:{garza.pk}"})
        self.assertTrue(Pertenencia.objects.filter(pk=garza.pk).exists())
        respuesta = self.client.post("/organizaciones/miembros/", {"accion": f"sacar:{nutria_en_henares.pk}"}, follow=True)
        self.assertContains(respuesta, "Hecho con 1 fila.")
        self.assertFalse(Pertenencia.objects.filter(pk=nutria_en_henares.pk).exists())

    # En bloque: el admin de la organización cambia el rol de varias filas a la vez; lo que no puede (una de
    # otra organización, aunque mande su número) se ignora.
    def test_en_bloque(self):
        AdminDeOrganizacion.objects.create(usuario=self.lince, organizacion=self.tajo)
        self.como(self.lince)
        nutria_en_sorbe = Pertenencia.objects.get(usuario=self.nutria, grupo=self.sorbe)
        garza = Pertenencia.objects.get(usuario=self.garza)
        erizo = Pertenencia.objects.get(usuario=self.erizo)
        respuesta = self.client.post("/organizaciones/miembros/", {
            "accion": "en_bloque", "operacion": f"rol:{Pertenencia.ADMIN_GRUPO}", "seleccion": [nutria_en_sorbe.pk, garza.pk, erizo.pk],
        }, follow=True)
        self.assertContains(respuesta, "Hecho con 2 filas.")
        self.assertEqual(set(Pertenencia.objects.filter(rol=Pertenencia.ADMIN_GRUPO).values_list("usuario__alias", flat=True)), {"Lince", "Nutria", "Garza"})
        self.assertEqual(Pertenencia.objects.get(pk=erizo.pk).rol, Pertenencia.USUARIO)

    # Admitir desde aquí: solo en los grupos donde se puede admitir.
    def test_admitir(self):
        otra = crear_usuario_de_prueba("Otra")
        self.client.post("/organizaciones/miembros/", {"accion": "admitir", "grupo": self.henares.pk, "alias": "Otra", "rol": Pertenencia.USUARIO})
        self.assertTrue(Pertenencia.objects.filter(usuario=otra, grupo=self.henares).exists())
        respuesta = self.client.post("/organizaciones/miembros/", {"accion": "admitir", "grupo": self.sorbe.pk, "alias": "Otra", "rol": Pertenencia.USUARIO})
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Pertenencia.objects.filter(usuario=otra, grupo=self.sorbe).exists())

    # Lo que cuesta no crece con las personas.
    def test_consultas(self):
        def mas():
            numero = Usuario.objects.count()
            persona = crear_usuario_de_prueba(f"Persona {numero}")
            admitir(persona, self.sorbe, es_base=True)
            admitir(persona, self.henares)

        self.comprobar_consultas("/organizaciones/miembros/", 7, mas)


class PruebasDeInactividad(PruebaDeMiembros):
    """El día de actividad, el plazo en cascada y la marca «Sin actividad»."""

    # Cada petición apunta el día (una vez al día); la plataforma no guarda la hora.
    def test_apuntar_el_dia(self):
        Usuario.objects.filter(pk=self.lince.pk).update(ultima_actividad=None)
        self.client.get("/organizaciones/miembros/")
        self.assertEqual(Usuario.objects.get(pk=self.lince.pk).ultima_actividad, timezone.localdate())

    # De partida, 30 días y mínimo 30. El superadmin sube el de partida a 90 y el mínimo a 15; la
    # organización baja a 60 y GRU Henares a 20, que vale también en GRU Sorbe. Un grupo no puede bajar del
    # mínimo ni subir del de la plataforma.
    def test_cascada(self):
        self.assertEqual(inactividad.dias_por_grupo([self.sorbe]), {self.sorbe.pk: 30})
        LimiteDeInactividad.objects.create(dias=90, minimo=15)
        LimiteDeInactividad.objects.create(organizacion=self.tajo, dias=60)
        self.assertEqual(inactividad.dias_por_grupo([self.sorbe, self.gru_ebro]), {self.sorbe.pk: 60, self.gru_ebro.pk: 90})
        LimiteDeInactividad.objects.create(grupo=self.henares, dias=20)
        self.assertEqual(inactividad.dias_por_grupo([self.sorbe, self.general]), {self.sorbe.pk: 20, self.general.pk: 60})
        respuesta = self.client.post(f"/organizaciones/inactividad/?nivel=g{self.henares.pk}", {"dias": 10})
        self.assertContains(respuesta, "No puede bajar del mínimo")
        respuesta = self.client.post(f"/organizaciones/inactividad/?nivel=g{self.henares.pk}", {"dias": 120})
        self.assertContains(respuesta, "Solo se puede bajar")
        self.client.post(f"/organizaciones/inactividad/?nivel=g{self.henares.pk}", {"dias": 16})
        self.assertEqual(LimiteDeInactividad.objects.get(grupo=self.henares).dias, 16)
        # Lince no puede tocar la plataforma ni la organización (no es su admin).
        self.assertEqual(self.client.get("/organizaciones/inactividad/?nivel=").status_code, 403)
        self.assertEqual(self.client.get(f"/organizaciones/inactividad/?nivel=o{self.tajo.pk}").status_code, 403)

    # Quien lleva más del plazo sin actividad sale marcado (y se puede filtrar); no se ve el día.
    def test_marca(self):
        Usuario.objects.filter(pk=self.garza.pk).update(ultima_actividad=timezone.localdate() - timedelta(days=45))
        Usuario.objects.filter(pk=self.nutria.pk).update(ultima_actividad=timezone.localdate() - timedelta(days=5))
        respuesta = self.client.get("/organizaciones/miembros/")
        filas = {f["alias"]: f["actividad"] for f in respuesta.context["tabla"].filas}
        self.assertEqual(filas["Garza"], "Sin actividad (más de 30 días)")
        self.assertEqual(filas["Nutria"], "")
        self.assertNotContains(respuesta, (timezone.localdate() - timedelta(days=45)).strftime("%d/%m/%Y"))
