"""
La trastienda: el panel de Django, reordenado para que se entienda la jerarquía de la información.

Django agrupa las tablas por módulo y en orden alfabético. Aquí se agrupan por lo que significan para
quien administra, en este orden: usuarios, organizaciones y grupos, admins y, al final, lo técnico. Las
tablas de un módulo nuevo que no estén en SECCIONES salen en «Otros», para que ninguna quede oculta.

Es solo para emergencias técnicas del superadmin: las pantallas de verdad se hacen en la interfaz propia
(docs/diseno.md, apartado 4). Se activa en config/apps.py.
"""

from django.contrib import admin
from django.urls import reverse

# Secciones de la portada de la trastienda, en orden: nombre visible y tablas («módulo.Modelo»).
SECCIONES = [
    ("Usuarios", ["usuarios.Usuario", "grupos.Pertenencia"]),
    ("Organizaciones y grupos", ["grupos.Organizacion", "grupos.Grupo", "grupos.RelacionEntreGrupos", "grupos.InvitacionDeGrupo"]),
    ("Admins (de organización y de grupo)", ["grupos.AdminDeOrganizacion", "grupos.AdminDeGrupo"]),
    ("Roles y permisos", ["permisos.Rol", "permisos.ExcepcionDePermiso", "permisos.Cometido"]),
    ("Visibilidad", ["audiencias.ConfiguracionDeVisibilidad", "audiencias.Audiencia"]),
    ("Clasificación", ["etiquetas.Etiqueta", "tipologias.Tipologia"]),
    ("Funcionamiento interno", ["eventos_sw.AvisoPendiente"]),
]

# Explicación de la portada.
AYUDA_DE_INICIO = (
    "Trastienda técnica: solo para emergencias. El trabajo diario se hace en la aplicación.\n\n"
    "«Usuarios»: las cuentas con seudónimo (alias) y sus pertenencias, es decir, en qué grupos está cada "
    "persona. En la ficha de cada usuario se ven todos sus grupos, también los que contienen a los suyos.\n\n"
    "«Organizaciones y grupos»: cada organización es independiente y tiene grupos; cada grupo puede "
    "contener subgrupos a cualquier profundidad (general → zona → centro → …). También las relaciones "
    "libres entre grupos y las invitaciones a grupos de otras organizaciones.\n\n"
    "«Admins»: quién administra cada organización y cada grupo.\n\n"
    "«Roles y permisos»: qué puede hacer cada rol (también los roles que cree el superadmin), las "
    "excepciones de una persona en un grupo y los cometidos de cada cual en cosas concretas.\n\n"
    "«Visibilidad»: qué niveles ofrece cada organización y las audiencias (quién ve cada cosa).\n\n"
    "«Funcionamiento interno»: avisos pendientes entre módulos; normalmente no hay que tocar nada."
)


class Trastienda(admin.AdminSite):
    """El panel de Django con nombre propio, una portada explicada y las tablas agrupadas por SECCIONES."""

    site_header = "Trastienda de Asambleas"
    site_title = "Trastienda"
    index_title = "Inicio"
    index_template = "trastienda/inicio.html"

    # Portada: añade la explicación general.
    def index(self, request, extra_context=None):
        return super().index(request, {**(extra_context or {}), "ayuda_de_inicio": AYUDA_DE_INICIO})

    # Lista de secciones y tablas que pinta la portada (y el menú lateral). Rehace la de Django
    # siguiendo SECCIONES. Si se pide la página de un solo módulo (app_label), se deja como la de Django.
    def get_app_list(self, request, app_label=None):
        de_django = super().get_app_list(request, app_label)
        if app_label:
            return de_django
        tablas = {f"{modulo['app_label']}.{tabla['object_name']}": tabla for modulo in de_django for tabla in modulo["models"]}
        portada = reverse("admin:index", current_app=self.name)
        secciones = []
        for numero, (nombre, claves) in enumerate(SECCIONES):
            incluidas = [tablas.pop(clave) for clave in claves if clave in tablas]
            if incluidas:
                secciones.append({"name": nombre, "app_label": f"seccion{numero}", "app_url": portada, "models": incluidas})
        if tablas:
            secciones.append({"name": "Otros", "app_label": "otros", "app_url": portada, "models": list(tablas.values())})
        return secciones
