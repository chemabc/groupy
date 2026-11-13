"""
Pruebas de las pantallas de «Organizaciones y grupos»: número de consultas (que no crece con las filas),
quién ve qué y quién puede hacer qué, y el número de invitaciones del menú.

Estructura común: ORG Tajo (GRU Tajo ⊃ GRU Jarama ⊃ GRU Henares ⊃ GRU Sorbe) y ORG Ebro (GRU Ebro ⊃
GRU Segre). Lince es admin de GRU Henares; Zorro, admin de ORG Tajo; Nutria, miembro de GRU Henares;
Garza, de GRU Sorbe; Erizo, de GRU Segre.
"""

from django.core.cache import cache

from base.contrato import Ancla
from base.pruebas import PruebaDePantalla, contratos_de_prueba, crear_usuario_de_prueba, modulo_falso
from grupos.models import Grupo, InvitacionDeGrupo, Pertenencia, RelacionEntreGrupos
from grupos.servicios import (
    admitir,
    crear_grupo,
    crear_organizacion,
    invitar,
    nombrar_admin_de_organizacion,
    relacionar,
)

# Módulo de mentira con un ancla, para poder invitar a algo.
ALFA = modulo_falso("alfa", anclas=(Ancla("alfa.proyecto", "auth.Group", "Un proyecto de mentira"),))


class PruebaDeGrupos(PruebaDePantalla):
    """Base: la estructura del principio del fichero, con la sesión iniciada como Nutria."""

    # Crea las organizaciones, los grupos y las personas.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.gru_tajo = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.jarama = crear_grupo(cls.tajo, "GRU Jarama", padre=cls.gru_tajo)
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.jarama)
        cls.sorbe = crear_grupo(cls.tajo, "GRU Sorbe", padre=cls.henares)
        cls.ebro, cls.gru_ebro = crear_organizacion("ORG Ebro", "GRU Ebro")
        cls.segre = crear_grupo(cls.ebro, "GRU Segre", padre=cls.gru_ebro)
        cls.lince = crear_usuario_de_prueba("Lince")
        cls.zorro = crear_usuario_de_prueba("Zorro")
        cls.nutria = crear_usuario_de_prueba("Nutria")
        cls.garza = crear_usuario_de_prueba("Garza")
        cls.erizo = crear_usuario_de_prueba("Erizo")
        cls.superadmin = crear_usuario_de_prueba("superadmin", es_superadmin=True)
        admitir(cls.lince, cls.henares, rol=Pertenencia.ADMIN_GRUPO, es_base=True)
        admitir(cls.zorro, cls.gru_tajo)
        nombrar_admin_de_organizacion(cls.zorro, cls.tajo)
        admitir(cls.nutria, cls.henares, es_base=True)
        admitir(cls.garza, cls.sorbe, es_base=True)
        admitir(cls.erizo, cls.segre, rol=Pertenencia.ADMIN_GRUPO, es_base=True)
        cls.usuario = cls.nutria

    # Inicia sesión como otra persona (y vacía la caché, como al empezar cada prueba).
    def como(self, usuario):
        cache.clear()
        self.client.force_login(usuario)

    # Añade cinco personas a GRU Henares y un subgrupo, para comprobar que las consultas no crecen.
    def mas_gente(self):
        inicio = Pertenencia.objects.count()
        for numero in range(inicio, inicio + 5):
            admitir(crear_usuario_de_prueba(f"Persona {numero}"), self.henares)
        crear_grupo(self.tajo, f"GRU Badiel {Grupo.objects.count()}", padre=self.henares)


class PruebasDeConsultas(PruebaDeGrupos):
    """Cada pantalla cuesta lo mismo con pocas filas que con muchas."""

    # Mis grupos, como Nutria.
    def test_mis_grupos(self):
        self.comprobar_consultas("/organizaciones/", 5, lambda: admitir(self.nutria, crear_grupo(self.tajo, "GRU Lozoya", padre=self.jarama)))

    # Árbol, como admin de la organización y como superadmin.
    def test_arbol(self):
        self.como(self.zorro)
        self.comprobar_consultas("/organizaciones/arbol/", 5, self.mas_gente)
        self.como(self.superadmin)
        self.comprobar_consultas("/organizaciones/arbol/", 3, self.mas_gente)

    # Ficha de un grupo, como su admin (con la gestión de miembros) y como miembro.
    def test_ficha_de_grupo(self):
        self.como(self.lince)
        self.comprobar_consultas(f"/organizaciones/grupo/{self.henares.pk}/", 10, self.mas_gente)
        self.como(self.nutria)
        self.comprobar_consultas(f"/organizaciones/grupo/{self.henares.pk}/", 9, self.mas_gente)

    # Ficha de la organización, como su admin.
    def test_ficha_de_organizacion(self):
        self.como(self.zorro)
        self.comprobar_consultas(
            f"/organizaciones/organizacion/{self.tajo.pk}/", 5, lambda: crear_grupo(self.tajo, f"GRU Alberche {Grupo.objects.count()}")
        )

    # Relaciones, como admin del grupo.
    def test_relaciones(self):
        self.como(self.lince)

        # Dos relaciones más cada vez.
        def mas_relaciones():
            numero = RelacionEntreGrupos.objects.count()
            relacionar(self.henares, self.sorbe, f"colabora {numero}")
            relacionar(self.jarama, self.henares, f"apoya {numero}")

        self.comprobar_consultas("/organizaciones/relaciones/", 6, mas_relaciones)

    # Invitaciones, como admin del grupo invitado.
    def test_invitaciones(self):
        self.como(self.erizo)
        with contratos_de_prueba(ALFA):

            # Dos invitaciones más cada vez.
            def mas_invitaciones():
                for _vez in range(2):
                    invitar("alfa.proyecto", InvitacionDeGrupo.objects.count() + 1, self.henares, self.segre, self.lince)

            mas_invitaciones()
            self.comprobar_consultas("/organizaciones/invitaciones/", 4, mas_invitaciones)


class PruebasDeQuienVeQue(PruebaDeGrupos):
    """Qué ve cada cual en el menú y en las fichas."""

    # Una persona sin admin no ve «Árbol» en el menú ni puede abrirlo; su admin sí.
    def test_arbol_solo_para_admins(self):
        respuesta = self.client.get("/organizaciones/")
        self.assertNotContains(respuesta, 'href="/organizaciones/arbol/"')
        self.assertContains(respuesta, "Invitaciones <span")
        self.assertEqual(self.client.get("/organizaciones/arbol/").status_code, 403)
        self.como(self.lince)
        respuesta = self.client.get("/organizaciones/arbol/")
        self.assertContains(respuesta, 'href="/organizaciones/arbol/"')
        # Lince administra GRU Henares: ve su rama, no los grupos de encima.
        self.assertContains(respuesta, "GRU Sorbe")
        self.assertNotContains(respuesta, "<td>GRU Tajo</td>", html=True)

    # Mis grupos: los directos y, como heredados, los que los contienen; nada de otras organizaciones.
    def test_mis_grupos(self):
        respuesta = self.client.get("/organizaciones/")
        self.assertContains(respuesta, "GRU Henares")
        self.assertContains(respuesta, "asamblea base")
        self.assertContains(respuesta, ">(por herencia)</span>", count=2)
        self.assertNotContains(respuesta, "GRU Sorbe")
        self.assertNotContains(respuesta, "ORG Ebro")

    # La ficha la ven los miembros (también los de subgrupos); no quien está en otra rama u organización.
    def test_ficha_solo_para_quien_esta(self):
        self.assertEqual(self.client.get(f"/organizaciones/grupo/{self.jarama.pk}/").status_code, 200)
        self.assertEqual(self.client.get(f"/organizaciones/grupo/{self.sorbe.pk}/").status_code, 403)
        respuesta = self.client.get(f"/organizaciones/grupo/{self.segre.pk}/")
        self.assertContains(respuesta, "solo la ven sus miembros", status_code=403)

    # Los miembros ven la lista de miembros, salvo que la organización lo cierre; los admins, siempre.
    def test_lista_de_miembros(self):
        url = f"/organizaciones/grupo/{self.henares.pk}/"
        self.assertContains(self.client.get(url), "Garza")
        self.tajo.miembros_ven_miembros = False
        self.tajo.save()
        respuesta = self.client.get(url)
        self.assertNotContains(respuesta, "Garza")
        self.assertContains(respuesta, "solo la ven los admins")
        self.como(self.lince)
        self.assertContains(self.client.get(url), "Garza")

    # Si el superadmin quita «grupos.ver_miembros» al rol usuario, la organización no puede devolverlo.
    def test_el_superadmin_manda(self):
        from permisos.models import PermisoDeRol

        PermisoDeRol.objects.filter(rol_id="usuario", permiso="grupos.ver_miembros").delete()
        cache.clear()
        self.assertNotContains(self.client.get(f"/organizaciones/grupo/{self.henares.pk}/"), "Garza")

    # Un miembro normal no ve los botones de gestión ni puede usarlos (403 con explicación).
    def test_miembro_no_gestiona(self):
        url = f"/organizaciones/grupo/{self.henares.pk}/"
        self.assertNotContains(self.client.get(url), "Admitir a una persona")
        respuesta = self.client.post(url, {"accion": "admitir", "alias": "Erizo", "rol": "usuario"})
        self.assertContains(respuesta, "grupos.admitir", status_code=403)


class PruebasDeGestion(PruebaDeGrupos):
    """Lo que hacen los admins desde las fichas."""

    # El admin del grupo admite, cambia el rol y saca; hacer admin a alguien pide otro permiso.
    def test_admitir_cambiar_rol_y_sacar(self):
        self.como(self.lince)
        url = f"/organizaciones/grupo/{self.henares.pk}/"
        self.assertRedirects(self.client.post(url, {"accion": "admitir", "alias": "erizo", "rol": "usuario"}), url)
        pertenencia = Pertenencia.objects.get(usuario=self.erizo, grupo=self.henares)
        respuesta = self.client.post(url, {"accion": "rol", "pertenencia": pertenencia.pk, "rol": Pertenencia.ADMIN_GRUPO})
        self.assertContains(respuesta, "grupos.nombrar_admin_grupo", status_code=403)
        self.assertRedirects(self.client.post(url, {"accion": "sacar", "pertenencia": pertenencia.pk}), url)
        self.assertFalse(Pertenencia.objects.filter(usuario=self.erizo, grupo=self.henares).exists())
        respuesta = self.client.post(url, {"accion": "admitir", "alias": "Nadie", "rol": "usuario"})
        self.assertContains(respuesta, "No hay nadie con ese alias.")

    # El admin de la organización sí nombra admins de grupo y puede mover un grupo; no dentro de sí mismo.
    def test_admin_de_organizacion(self):
        self.como(self.zorro)
        url = f"/organizaciones/grupo/{self.henares.pk}/"
        pertenencia = Pertenencia.objects.get(usuario=self.nutria, grupo=self.henares)
        self.client.post(url, {"accion": "rol", "pertenencia": pertenencia.pk, "rol": Pertenencia.ADMIN_GRUPO})
        pertenencia.refresh_from_db()
        self.assertEqual(pertenencia.rol, Pertenencia.ADMIN_GRUPO)
        datos = {"accion": "editar", "nombre": "GRU Henares", "descripcion": "", "ambito": "Alcalá"}
        self.assertRedirects(self.client.post(url, {**datos, "padre": self.gru_tajo.pk}), url)
        self.henares.refresh_from_db()
        self.assertEqual((self.henares.padre_id, self.henares.ambito), (self.gru_tajo.pk, "Alcalá"))
        respuesta = self.client.post(url, {**datos, "padre": self.sorbe.pk})
        self.assertContains(respuesta, "Escoja una opción válida")

    # El admin del grupo edita los datos pero no ve el campo para moverlo.
    def test_admin_de_grupo_no_mueve(self):
        self.como(self.lince)
        respuesta = self.client.get(f"/organizaciones/grupo/{self.henares.pk}/")
        self.assertContains(respuesta, "Cambiar los datos del grupo")
        self.assertNotContains(respuesta, 'name="padre"')

    # Crear un subgrupo lleva a su ficha.
    def test_crear_subgrupo(self):
        self.como(self.lince)
        respuesta = self.client.post(f"/organizaciones/grupo/{self.henares.pk}/", {"accion": "subgrupo", "nombre": "GRU Badiel"})
        nuevo = Grupo.objects.get(nombre="GRU Badiel")
        self.assertRedirects(respuesta, f"/organizaciones/grupo/{nuevo.pk}/")
        self.assertEqual(nuevo.padre, self.henares)

    # La ficha de la organización: su admin cambia el interruptor; nombrar admins es del superadmin.
    def test_ficha_de_organizacion(self):
        url = f"/organizaciones/organizacion/{self.tajo.pk}/"
        self.assertEqual(self.client.get(url).status_code, 403)
        self.como(self.zorro)
        self.assertNotContains(self.client.get(url), "Nombrar admin</summary>")
        self.client.post(url, {"accion": "datos", "nombre": "ORG Tajo", "descripcion": ""})
        self.tajo.refresh_from_db()
        self.assertFalse(self.tajo.miembros_ven_miembros)
        self.assertEqual(self.client.post(url, {"accion": "nombrar", "alias": "Lince"}).status_code, 403)
        self.como(self.superadmin)
        self.assertRedirects(self.client.post(url, {"accion": "nombrar", "alias": "Lince"}), url)
        respuesta = self.client.post(url, {"accion": "nombrar", "alias": "Erizo"})
        self.assertContains(respuesta, "hay que estar en alguno de sus grupos")
        self.client.post(url, {"accion": "quitar", "usuario": self.zorro.pk})
        self.assertFalse(self.tajo.admins.filter(usuario=self.zorro).exists())

    # El superadmin crea organizaciones desde «Árbol».
    def test_nueva_organizacion(self):
        self.como(self.superadmin)
        respuesta = self.client.post("/organizaciones/arbol/", {"nombre": "ORG Miño", "primer_grupo": "GRU Miño"})
        organizacion = self.tajo.__class__.objects.get(nombre="ORG Miño")
        self.assertRedirects(respuesta, f"/organizaciones/organizacion/{organizacion.pk}/")
        self.assertTrue(organizacion.grupos.filter(nombre="GRU Miño").exists())

    # Relaciones: el admin crea una entre grupos de su organización y la borra; otra organización, no.
    def test_relaciones(self):
        self.como(self.lince)
        datos = {"accion": "crear", "origen": self.henares.pk, "tipo": "colabora  con", "destino": self.jarama.pk}
        self.assertRedirects(self.client.post("/organizaciones/relaciones/", datos), "/organizaciones/relaciones/")
        relacion = RelacionEntreGrupos.objects.get()
        self.assertEqual(relacion.tipo, "colabora con")
        respuesta = self.client.post("/organizaciones/relaciones/", {**datos, "destino": self.segre.pk})
        self.assertContains(respuesta, "Escoja una opción válida")
        # Nutria la ve pero no puede borrarla.
        self.como(self.nutria)
        self.assertContains(self.client.get("/organizaciones/relaciones/"), "colabora con")
        self.assertEqual(self.client.post("/organizaciones/relaciones/", {"accion": "borrar", "relacion": relacion.pk}).status_code, 403)
        self.como(self.lince)
        self.client.post("/organizaciones/relaciones/", {"accion": "borrar", "relacion": relacion.pk})
        self.assertFalse(RelacionEntreGrupos.objects.exists())


class PruebasDeInvitaciones(PruebaDeGrupos):
    """La pantalla de invitaciones y su número en el menú."""

    # El número es de las pendientes que puede responder: Erizo (admin del grupo invitado) ve (1) y,
    # al aceptarla, (0) también en la zona que manda htmx (para poner el menú al día).
    def test_contador_y_aceptar(self):
        with contratos_de_prueba(ALFA):
            invitacion = invitar("alfa.proyecto", 7, self.henares, self.segre, self.lince, "Hagamos algo juntos")
            self.assertContains(self.client.get("/organizaciones/"), 'data-contador>(0)</span>')
            self.como(self.erizo)
            respuesta = self.client.get("/organizaciones/invitaciones/")
            self.assertContains(respuesta, 'data-contador>(1)</span>')
            self.assertContains(respuesta, "Un proyecto de mentira n.º 7")
            self.assertContains(respuesta, 'value="aceptar"')
            # La caché se invalida al terminar la transacción: aquí se ejecuta a mano lo que haría Django.
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post("/organizaciones/invitaciones/", {"accion": "aceptar", "invitacion": invitacion.pk})
            invitacion.refresh_from_db()
            self.assertEqual(invitacion.estado, InvitacionDeGrupo.ACEPTADA)
            zona = self.client.get("/organizaciones/invitaciones/", headers={"HX-Request": "true", "HX-Target": "zona"})
            self.assertContains(zona, 'id="contador-gruposinvitaciones" data-contador hx-swap-oob="true">(0)</span>')

    # Quien está en el grupo que invitó la ve en «Hechas» y puede retirarla, pero no responderla.
    def test_retirar(self):
        with contratos_de_prueba(ALFA):
            invitacion = invitar("alfa.proyecto", 7, self.henares, self.segre, self.lince)
            respuesta = self.client.get("/organizaciones/invitaciones/")
            self.assertContains(respuesta, 'value="retirar"')
            self.assertNotContains(respuesta, 'value="aceptar"')
            self.client.post("/organizaciones/invitaciones/", {"accion": "retirar", "invitacion": invitacion.pk})
            invitacion.refresh_from_db()
            self.assertEqual(invitacion.estado, InvitacionDeGrupo.RETIRADA)
            # Zorro (admin de ORG Tajo, en GRU Tajo) también la ve, entre las hechas por sus grupos.
            self.como(self.zorro)
            self.assertContains(self.client.get("/organizaciones/invitaciones/"), "Retirada")
            # El superadmin ve todas en una sola lista.
            self.como(self.superadmin)
            self.assertContains(self.client.get("/organizaciones/invitaciones/"), "Todas las invitaciones")
