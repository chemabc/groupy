"""
Organizaciones, grupos, pertenencias y admins en la trastienda (el panel de Django), solo para
emergencias técnicas. Las pantallas de verdad llegan con las pantallas del superadmin.

El orden de las secciones lo fija config/trastienda.py. Aquí se decide qué muestra cada tabla, con un
texto de ayuda en cada una (base/trastienda.py). Para que se entienda la jerarquía, cada grupo se
muestra con su camino completo («ORG Tajo › GRU Tajo › GRU Jarama › GRU Henares»).

Ojo: lo que se cambia aquí no pasa por grupos/servicios.py, así que no avisa con eventos_sw (salvo crear
o mover grupos, que avisa el propio modelo).
"""

from django import forms
from django.apps import apps
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import Count, OuterRef, Subquery
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from base.trastienda import ConAyuda

from .models import (
    AdminDeGrupo,
    AdminDeOrganizacion,
    Grupo,
    InvitacionDeGrupo,
    Organizacion,
    Pertenencia,
    RelacionEntreGrupos,
    camino,
    orden_de_arbol,
)
from .servicios import grupos_de


# Texto completo de un grupo con su organización: «ORG Tajo › GRU Tajo › GRU Jarama». El grupo debe
# venir de una consulta con_camino() y con la organización cargada.
def nombre_completo(grupo):
    return f"{grupo.organizacion.nombre} › {grupo.camino}"


# Lista de grupos (ya con camino) como líneas HTML, una por grupo. Para los campos de solo lectura.
#   - grupos: grupos con camino.
#   - nota: función opcional que añade un comentario a cada línea.
def lineas_de_grupos(grupos, nota=lambda grupo: ""):
    lineas = format_html_join(
        "", "<li>{}{}</li>", ((nombre_completo(grupo), nota(grupo)) for grupo in grupos)
    )
    return format_html("<ul style='margin:0;padding-left:1.2em'>{}</ul>", lineas) if lineas else "—"


class ElegirGrupoConCamino:
    """
    Añadido para las fichas y tablas de la trastienda con un desplegable de grupos: cada opción se ve
    con su camino completo y en orden de árbol, para no confundir grupos de nombre parecido. Cuesta una
    sola consulta.
    """

    # Django la llama para cada campo que apunta a otra tabla. A los desplegables de grupos les da ya la
    # consulta (si no, Django tomaría el orden de la lista de grupos, que necesita el camino y fallaría).
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.related_model is Grupo:
            kwargs["queryset"] = Grupo.objects.en_orden_de_arbol().select_related("organizacion")
        campo = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.related_model is Grupo and campo is not None:
            campo.label_from_instance = nombre_completo
        return campo


class ElegirRol:
    """
    Añadido para las fichas y tablas de la trastienda con el rol de una pertenencia: lo muestra como un
    desplegable con los roles de grupo que existen (los del sistema y los personalizados). La tabla de
    roles es del módulo «permisos» y se busca por su nombre, sin importarlo.
    """

    # Django la llama para cada campo. Cambia el campo «rol» por un desplegable.
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "rol":
            roles = apps.get_model("permisos", "Rol").objects.filter(nivel="grupo")
            return forms.ChoiceField(
                label="rol", choices=[(rol.codigo, rol.nombre) for rol in roles], help_text=db_field.help_text
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)


# ── Usuarios ─────────────────────────────────────────────────────────────────────────────────────────


class PertenenciasDelUsuario(ElegirRol, ElegirGrupoConCamino, admin.TabularInline):
    """En la ficha de un usuario: los grupos en los que está directamente, con su rol."""

    model = Pertenencia
    fk_name = "usuario"
    fields = ["grupo", "rol", "es_base", "desde"]
    extra = 0
    verbose_name = "pertenencia"
    verbose_name_plural = "Pertenencias: grupos en los que está directamente"


# El módulo «usuarios» registra su ficha sin saber nada de grupos (está en una capa inferior). Aquí se
# toma esa ficha y se amplía con las pertenencias y la lista de todos sus grupos.
ModeloDeUsuario = get_user_model()
FichaDeUsuarioBase = type(admin.site._registry[ModeloDeUsuario])
admin.site.unregister(ModeloDeUsuario)


@admin.register(ModeloDeUsuario)
class UsuarioConGrupos(FichaDeUsuarioBase):
    """La ficha de usuario de «usuarios», con su asamblea base, sus pertenencias y todos sus grupos."""

    inlines = [PertenenciasDelUsuario]
    list_display = ["alias", "asamblea_base", "es_superadmin", "activo", "activado_el", "last_login"]
    fields = [*FichaDeUsuarioBase.fields, "todos_sus_grupos", "administra"]
    readonly_fields = [*FichaDeUsuarioBase.readonly_fields, "todos_sus_grupos", "administra"]

    # Lista de usuarios: añade a cada uno el camino de su asamblea base, en la misma consulta.
    def get_queryset(self, request):
        base = Pertenencia.objects.filter(usuario=OuterRef("pk"), es_base=True)
        return super().get_queryset(request).annotate(
            camino_de_la_base=Subquery(base.annotate(texto=camino("grupo")).values("texto")[:1])
        )

    # Columna «asamblea base» de la lista.
    @admin.display(description="asamblea base", ordering="camino_de_la_base")
    def asamblea_base(self, usuario):
        return usuario.camino_de_la_base or "—"

    # Campo de solo lectura: todos los grupos de los que es miembro, también los que contienen a los
    # suyos (la pertenencia se hereda hacia arriba), en orden de árbol.
    @admin.display(description="todos sus grupos")
    def todos_sus_grupos(self, usuario):
        if usuario.pk is None:
            return "—"
        directas = {pertenencia.grupo_id: pertenencia for pertenencia in usuario.pertenencias.all()}
        grupos = Grupo.objects.en_orden_de_arbol().select_related("organizacion").filter(pk__in=grupos_de(usuario))

        # Comentario de cada grupo: si está directamente (y con qué) o porque contiene a uno de los suyos.
        def nota(grupo):
            pertenencia = directas.get(grupo.pk)
            if pertenencia is None:
                return " (heredado: contiene a uno de sus grupos)"
            marcas = ["directamente"]
            if pertenencia.es_base:
                marcas.append("asamblea base")
            if pertenencia.rol == Pertenencia.ADMIN_GRUPO:
                marcas.append("admin del grupo")
            return f" ({', '.join(marcas)})"

        return lineas_de_grupos(grupos, nota)

    # Campo de solo lectura: de qué organizaciones y grupos es admin.
    @admin.display(description="es admin de")
    def administra(self, usuario):
        if usuario.pk is None:
            return "—"
        organizaciones = [f"{admin_org.organizacion} (organización)" for admin_org in usuario.organizaciones_que_administra.select_related("organizacion")]
        grupos = Grupo.objects.en_orden_de_arbol().select_related("organizacion").filter(
            pertenencias__usuario=usuario, pertenencias__rol=Pertenencia.ADMIN_GRUPO
        )
        textos = organizaciones + [f"{nombre_completo(grupo)} (grupo)" for grupo in grupos]
        return format_html_join("", "<div>{}</div>", ((texto,) for texto in textos)) if textos else "—"


@admin.register(Pertenencia)
class PertenenciaEnLaTrastienda(ConAyuda, ElegirRol, ElegirGrupoConCamino, admin.ModelAdmin):
    """Todas las pertenencias: quién está en cada grupo, con su rol."""

    ayuda = (
        "Cada fila dice que un usuario está directamente en un grupo, con su rol (usuario o admin del "
        "grupo), si es su asamblea base (su grupo más local; solo una por persona) y desde cuándo.\n\n"
        "Quien está en un grupo es también miembro de todos los grupos que lo contienen, aunque eso no se "
        "apunta aquí: se calcula. En la ficha de cada usuario se ven todos sus grupos.\n\n"
        "Normalmente es más cómodo cambiar las pertenencias desde la ficha del usuario o del grupo."
    )
    list_display = ["usuario", "grupo_completo", "rol", "es_base", "desde"]
    list_filter = ["rol", "es_base", "grupo__organizacion"]
    search_fields = ["usuario__alias_normalizado", "grupo__nombre"]
    list_select_related = ["usuario", "grupo__organizacion"]

    # Añade el camino del grupo y su clave de orden a cada fila, en la misma consulta, y después ordena.
    # (No se parte de super().get_queryset(), porque ese ya ordena, antes de que exista la clave.)
    def get_queryset(self, request):
        consulta = Pertenencia.objects.annotate(camino=camino("grupo"), orden=orden_de_arbol("grupo"))
        return consulta.order_by(*self.get_ordering(request))

    # Orden de la lista: por usuario y, dentro, en orden de árbol.
    def get_ordering(self, request):
        return ["usuario__alias_normalizado", "grupo__organizacion__nombre", "orden"]

    # Columna «grupo» con el camino completo.
    @admin.display(description="grupo", ordering="orden")
    def grupo_completo(self, pertenencia):
        return f"{pertenencia.grupo.organizacion} › {pertenencia.camino}"


# ── Organizaciones y grupos ──────────────────────────────────────────────────────────────────────────


@admin.register(Organizacion)
class OrganizacionEnLaTrastienda(ConAyuda, admin.ModelAdmin):
    """Organizaciones, con su número de grupos y, en la ficha, su árbol de grupos y sus admins."""

    ayuda = (
        "Cada organización es independiente de las demás y tiene al menos un grupo. Nadie pertenece a una "
        "organización sin estar en uno de sus grupos.\n\n"
        "En la ficha se ve su árbol de grupos (cada grupo con su camino completo) y quién la administra. "
        "Los grupos se crean y se mueven en «Grupos»; los admins, en «Admins de organización»."
    )
    list_display = ["nombre", "numero_de_grupos", "creada_el"]
    search_fields = ["nombre"]
    fields = ["nombre", "descripcion", "creada_el", "arbol_de_grupos", "admins_de_la_organizacion"]
    readonly_fields = ["arbol_de_grupos", "admins_de_la_organizacion"]

    # Añade el número de grupos a cada fila, en la misma consulta.
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(cuantos_grupos=Count("grupos"))

    # Columna «grupos».
    @admin.display(description="grupos", ordering="cuantos_grupos")
    def numero_de_grupos(self, organizacion):
        return organizacion.cuantos_grupos

    # Campo de solo lectura: todos sus grupos en orden de árbol.
    @admin.display(description="árbol de grupos")
    def arbol_de_grupos(self, organizacion):
        if organizacion.pk is None:
            return "—"
        grupos = organizacion.grupos.en_orden_de_arbol().select_related("organizacion")
        return lineas_de_grupos(grupos)

    # Campo de solo lectura: quién la administra.
    @admin.display(description="admins")
    def admins_de_la_organizacion(self, organizacion):
        if organizacion.pk is None:
            return "—"
        return ", ".join(str(admin_org.usuario) for admin_org in organizacion.admins.select_related("usuario")) or "—"


class PertenenciasDelGrupo(ElegirRol, admin.TabularInline):
    """En la ficha de un grupo: quién está directamente en él, con su rol."""

    model = Pertenencia
    fk_name = "grupo"
    fields = ["usuario", "rol", "es_base", "desde"]
    extra = 0
    verbose_name = "miembro directo"
    verbose_name_plural = "Miembros directos (los de sus subgrupos, más arriba)"


@admin.register(Grupo)
class GrupoEnLaTrastienda(ConAyuda, ElegirGrupoConCamino, admin.ModelAdmin):
    """Grupos en orden de árbol, con su camino, sus subgrupos y todos sus miembros."""

    ayuda = (
        "Los grupos de todas las organizaciones, en orden de árbol: cada uno con su camino completo, desde "
        "la organización hasta él («ORG Tajo › GRU Tajo › GRU Jarama › GRU Henares»).\n\n"
        "Un grupo puede contener subgrupos a cualquier profundidad (por ejemplo, general → zona → centro → "
        "…). Para meter un grupo dentro de otro, elige su «grupo padre», que debe ser de la misma "
        "organización. Quien está en un grupo es también miembro de todos los que lo contienen.\n\n"
        "En la ficha se ven sus subgrupos, sus miembros directos (que se pueden cambiar) y los miembros que "
        "le llegan desde sus subgrupos."
    )
    list_display = ["grupo_completo", "miembros_directos", "ambito"]
    list_filter = ["organizacion"]
    search_fields = ["nombre"]
    list_select_related = ["organizacion"]
    inlines = [PertenenciasDelGrupo]
    fields = ["organizacion", "padre", "nombre", "descripcion", "ambito", "creado_el", "camino_completo", "subgrupos", "miembros_por_sus_subgrupos"]
    readonly_fields = ["camino_completo", "subgrupos", "miembros_por_sus_subgrupos"]

    # Añade el camino, la clave de orden y el número de miembros directos a cada fila, en la misma
    # consulta.
    # (No se parte de super().get_queryset(), porque ese ya ordena, antes de que exista la clave.)
    def get_queryset(self, request):
        consulta = Grupo.objects.en_orden_de_arbol().annotate(cuantos_miembros=Count("pertenencias"))
        return consulta.order_by(*self.get_ordering(request))

    # Orden de la lista: por organización y en orden de árbol. Ojo: Django usa este orden también en los
    # desplegables de grupos de otras fichas, por eso todas usan ElegirGrupoConCamino.
    def get_ordering(self, request):
        return ["organizacion__nombre", "orden"]

    # Al editar un grupo, la organización ya no se puede cambiar.
    def get_readonly_fields(self, request, obj=None):
        fijos = super().get_readonly_fields(request, obj)
        return [*fijos, "organizacion"] if obj else fijos

    # Columna «grupo» con el camino completo.
    @admin.display(description="grupo", ordering="orden")
    def grupo_completo(self, grupo):
        return nombre_completo(grupo)

    # Columna «miembros directos».
    @admin.display(description="miembros directos", ordering="cuantos_miembros")
    def miembros_directos(self, grupo):
        return grupo.cuantos_miembros

    # Campo de solo lectura: el camino del grupo en su organización.
    @admin.display(description="camino")
    def camino_completo(self, grupo):
        return nombre_completo(grupo) if grupo.pk else "—"

    # Campo de solo lectura: todos sus subgrupos, a cualquier profundidad.
    @admin.display(description="subgrupos")
    def subgrupos(self, grupo):
        if grupo.pk is None:
            return "—"
        debajo = Grupo.objects.en_orden_de_arbol().select_related("organizacion").filter(ascendencia__antecesor=grupo)
        return lineas_de_grupos(debajo.exclude(pk=grupo.pk))

    # Campo de solo lectura: quién es miembro del grupo por estar en uno de sus subgrupos.
    @admin.display(description="miembros por sus subgrupos")
    def miembros_por_sus_subgrupos(self, grupo):
        if grupo.pk is None:
            return "—"
        pertenencias = (
            Pertenencia.objects.filter(grupo__ascendencia__antecesor=grupo)
            .exclude(grupo=grupo)
            .select_related("usuario", "grupo")
            .order_by("usuario__alias_normalizado")
        )
        filas = ((pertenencia.usuario, pertenencia.grupo) for pertenencia in pertenencias)
        return format_html_join("", "<div>{} <span style='color:var(--body-quiet-color)'>(en {})</span></div>", filas) or "—"


@admin.register(RelacionEntreGrupos)
class RelacionEnLaTrastienda(ConAyuda, ElegirGrupoConCamino, admin.ModelAdmin):
    """Relaciones libres entre grupos."""

    ayuda = (
        "Relaciones libres entre dos grupos, de la misma organización o de otra («colabora con», «nació "
        "de»…). Sirven para dibujar el grafo de grupos. No dan ni quitan permisos: lo único que cuenta para "
        "los permisos es que un grupo contenga a otro (su «grupo padre»)."
    )
    list_display = ["origen", "tipo", "destino"]


@admin.register(InvitacionDeGrupo)
class InvitacionEnLaTrastienda(ConAyuda, ElegirGrupoConCamino, admin.ModelAdmin):
    """Invitaciones entre grupos de organizaciones distintas."""

    ayuda = (
        "Invitaciones de un grupo a un grupo de otra organización para algo concreto (de momento, un "
        "proyecto conjunto). Las acepta o rechaza el admin del grupo invitado. Aceptar no mete a nadie en "
        "ningún grupo: solo abre lo invitado.\n\n"
        "Se crean y se responden desde la aplicación; aquí solo se consultan."
    )
    list_display = ["grupo_que_invita", "grupo_invitado", "ancla_tipo", "ancla_id", "estado", "creada_el"]
    list_filter = ["estado"]

    # Las invitaciones no se crean a mano: necesitan algo a lo que invitar (un proyecto).
    def has_add_permission(self, request):
        return False


# ── Admins ───────────────────────────────────────────────────────────────────────────────────────────


@admin.register(AdminDeOrganizacion)
class AdminDeOrganizacionEnLaTrastienda(ConAyuda, admin.ModelAdmin):
    """Admins de cada organización."""

    ayuda = (
        "Quién administra cada organización (admin_org). No se hereda: se nombra para cada organización, y "
        "la persona debe estar en alguno de sus grupos. Deja de serlo si sale del último.\n\n"
        "Para nombrar a alguien, pulsa «Añadir» y elige la persona y la organización."
    )
    list_display = ["usuario", "organizacion", "desde"]
    list_filter = ["organizacion"]


class FormularioDeAdminDeGrupo(forms.ModelForm):
    """
    Formulario para nombrar admin de grupo: persona y grupo. Si la persona ya está en el grupo, no es un
    error: el formulario pasa a trabajar sobre esa pertenencia y solo le cambia el rol.
    """

    class Meta:
        model = AdminDeGrupo
        fields = ["usuario", "grupo"]

    # Tras comprobar los campos, busca si la persona ya está en el grupo y, si es así, usa esa
    # pertenencia (así no choca con la regla de una pertenencia por persona y grupo). En los dos casos,
    # el rol pasa a ser admin del grupo desde hoy.
    def clean(self):
        datos = super().clean()
        existente = AdminDeGrupo._base_manager.filter(usuario=datos.get("usuario"), grupo=datos.get("grupo")).first()
        if existente is not None:
            self.instance = existente
        self.instance.rol = Pertenencia.ADMIN_GRUPO
        self.instance.rol_desde = timezone.localdate()
        return datos


@admin.register(AdminDeGrupo)
class AdminDeGrupoEnLaTrastienda(ConAyuda, ElegirRol, ElegirGrupoConCamino, admin.ModelAdmin):
    """Admins de cada grupo: las pertenencias con rol «admin del grupo»."""

    ayuda = (
        "Quién administra cada grupo (admin_grupo): cuida la estructura del grupo, no filtra. No se hereda "
        "a los subgrupos.\n\n"
        "Para nombrar a alguien, pulsa «Añadir» y elige la persona y el grupo; si aún no estaba en el "
        "grupo, entra en él. Para quitarle el cargo, abre su fila y cambia el rol a «Usuario»: sigue en el "
        "grupo."
    )
    form = FormularioDeAdminDeGrupo
    list_display = ["usuario", "grupo_completo", "rol_desde"]
    list_filter = ["grupo__organizacion"]
    list_select_related = ["usuario", "grupo__organizacion"]

    # Añade el camino del grupo y su clave de orden a cada fila, en la misma consulta, y después ordena
    # (sin partir de super().get_queryset(), que ya ordena antes de que exista la clave).
    def get_queryset(self, request):
        consulta = AdminDeGrupo.objects.annotate(camino=camino("grupo"), orden=orden_de_arbol("grupo"))
        return consulta.order_by(*self.get_ordering(request))

    # Orden de la lista: en orden de árbol.
    def get_ordering(self, request):
        return ["grupo__organizacion__nombre", "orden"]

    # Al añadir se eligen persona y grupo; al editar, solo se puede cambiar el rol.
    def get_fields(self, request, obj=None):
        return ["usuario", "grupo"] if obj is None else ["usuario", "grupo", "rol", "rol_desde"]

    # Al editar, la persona, el grupo y la fecha no se cambian.
    def get_readonly_fields(self, request, obj=None):
        return [] if obj is None else ["usuario", "grupo", "rol_desde"]

    # Al editar se usa el formulario normal (con el rol), no el de nombrar.
    def get_form(self, request, obj=None, **kwargs):
        if obj is not None:
            kwargs["form"] = forms.ModelForm
        return super().get_form(request, obj, **kwargs)

    # Al editar, si se cambia el rol, se apunta desde qué día lo tiene.
    def save_model(self, request, obj, form, change):
        if change and "rol" in form.changed_data:
            obj.rol_desde = timezone.localdate()
        super().save_model(request, obj, form, change)

    # Columna «grupo» con el camino completo.
    @admin.display(description="grupo", ordering="orden")
    def grupo_completo(self, pertenencia):
        return f"{pertenencia.grupo.organizacion} › {pertenencia.camino}"
