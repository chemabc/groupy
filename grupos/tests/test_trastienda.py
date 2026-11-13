"""
Pruebas de la trastienda (el panel de Django) con usuarios y grupos: orden de las secciones, ayuda en
cada pantalla, jerarquía visible y número de consultas que no crece con las filas.
"""

from django.contrib import admin
from django.contrib.auth.models import Group

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from grupos.servicios import admitir, crear_grupo, crear_organizacion


class PruebasDeLaTrastienda(PruebaDePantalla):
    """Recorre la trastienda como superadmin, con un árbol de tres niveles."""

    # Superadmin para entrar y un árbol: ORG Tajo › GRU Tajo › GRU Jarama › GRU Henares, con Lince en
    # Henares (asamblea base).
    @classmethod
    def setUpTestData(cls):
        cls.usuario = crear_usuario_de_prueba("Águila", es_superadmin=True)
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.jarama = crear_grupo(cls.tajo, "GRU Jarama", padre=cls.general)
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.jarama)
        cls.lince = crear_usuario_de_prueba("Lince")
        admitir(cls.lince, cls.henares, es_base=True)

    # Añade cinco grupos más, cada uno con un usuario, para comprobar que las listas no hacen una
    # consulta por fila.
    def mas_datos(self):
        for numero in range(5):
            grupo = crear_grupo(self.tajo, f"GRU Extra {numero}", padre=self.jarama)
            admitir(crear_usuario_de_prueba(f"Extra {numero}"), grupo)

    # La portada sigue el orden acordado: usuarios, organizaciones y grupos, admins y lo interno. Los
    # «grupos» de Django no aparecen.
    def test_portada(self):
        respuesta = self.client.get("/trastienda/")
        secciones = [seccion["name"] for seccion in respuesta.context["app_list"]]
        self.assertEqual(
            secciones,
            ["Usuarios", "Organizaciones y grupos", "Admins (de organización y de grupo)", "Roles y permisos", "Funcionamiento interno"],
        )
        self.assertEqual([tabla["object_name"] for tabla in respuesta.context["app_list"][0]["models"]], ["Usuario", "Pertenencia"])
        self.assertContains(respuesta, "Trastienda técnica: solo para emergencias")
        self.assertNotIn(Group, admin.site._registry)

    # Las listas tienen ayuda, muestran el camino completo y no crecen en consultas con las filas.
    def test_listas(self):
        for direccion, consultas in [
            ("/trastienda/usuarios/usuario/", 4),
            ("/trastienda/grupos/grupo/", 5),
            ("/trastienda/grupos/pertenencia/", 6),
            ("/trastienda/grupos/admindegrupo/", 5),
            ("/trastienda/grupos/organizacion/", 4),
        ]:
            with self.subTest(direccion=direccion):
                respuesta = self.comprobar_consultas(direccion, consultas, None)
                self.assertContains(respuesta, "border-left: 4px solid")
        # La lista de grupos va en orden de árbol: cada grupo justo después de su padre.
        respuesta = self.client.get("/trastienda/grupos/grupo/")
        caminos = [grupo.camino for grupo in respuesta.context["cl"].result_list]
        self.assertEqual(caminos, ["GRU Tajo", "GRU Tajo › GRU Jarama", "GRU Tajo › GRU Jarama › GRU Henares"])
        # Los desplegables de grupos de otras fichas también, con el camino completo.
        respuesta = self.client.get("/trastienda/grupos/relacionentregrupos/add/")
        opciones = [etiqueta for _valor, etiqueta in respuesta.context["adminform"].form.fields["origen"].choices][1:]
        self.assertEqual(opciones[0], "ORG Tajo › GRU Tajo")
        self.assertEqual(opciones[-1], "ORG Tajo › GRU Tajo › GRU Jarama › GRU Henares")

    # Lo mismo, después de añadir filas: se mide una lista y luego otra con más datos.
    def test_listas_con_mas_filas(self):
        self.comprobar_consultas("/trastienda/grupos/grupo/", 5, self.mas_datos)

    # La ficha de un usuario muestra todos sus grupos, también los heredados.
    def test_ficha_de_usuario(self):
        respuesta = self.client.get(f"/trastienda/usuarios/usuario/{self.lince.pk}/change/")
        self.assertContains(respuesta, "ORG Tajo › GRU Tajo › GRU Jarama › GRU Henares (directamente, asamblea base)")
        self.assertContains(respuesta, "ORG Tajo › GRU Tajo (heredado")

    # La ficha del grupo general muestra sus subgrupos y los miembros que le llegan de ellos.
    def test_ficha_de_grupo(self):
        respuesta = self.client.get(f"/trastienda/grupos/grupo/{self.general.pk}/change/")
        self.assertContains(respuesta, "ORG Tajo › GRU Tajo › GRU Jarama › GRU Henares")
        self.assertContains(respuesta, "Lince <span")

    # Nombrar admin de grupo a quien ya está en el grupo le cambia el rol, sin duplicar la pertenencia.
    def test_nombrar_admin_de_grupo(self):
        respuesta = self.client.post(
            "/trastienda/grupos/admindegrupo/add/", {"usuario": self.lince.pk, "grupo": self.henares.pk}
        )
        self.assertEqual(respuesta.status_code, 302)
        pertenencias = self.lince.pertenencias.all()
        self.assertEqual([(p.grupo, p.rol, p.es_base) for p in pertenencias], [(self.henares, "admin_grupo", True)])

    # Las fichas llevan «Guardar», «Guardar y continuar editando», «Cancelar» (vuelve a la lista) y
    # «Eliminar»; no «Guardar y añadir otro».
    def test_botones_de_la_ficha(self):
        respuesta = self.client.get(f"/trastienda/grupos/grupo/{self.henares.pk}/change/")
        self.assertContains(respuesta, 'name="_save"')
        self.assertContains(respuesta, 'name="_continue"')
        self.assertContains(respuesta, 'class="cancelar">Cancelar</a>')
        self.assertContains(respuesta, 'class="deletelink"')
        self.assertNotContains(respuesta, 'name="_addanother"')

    # En la ficha de un rol, cada permiso lleva su explicación y su código aparte.
    def test_permisos_de_un_rol(self):
        respuesta = self.client.get("/trastienda/permisos/rol/admin_grupo/change/")
        self.assertContains(respuesta, "Editar los datos del grupo <code>grupos.editar_grupo</code>")

