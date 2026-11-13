"""
Roles, permisos, cometidos y excepciones en la trastienda (el panel de Django). Las pantallas de verdad
llegan con las pantallas del superadmin.

En la ficha de cada rol se marcan sus permisos, agrupados por módulo, con su explicación. Los cambios
invalidan solos la caché de permisos (permisos/senales.py).
"""

from django import forms
from django.contrib import admin
from django.utils.html import format_html

from base.registro import registro
from base.trastienda import ConAyuda
from grupos.admin import ElegirGrupoConCamino

from .models import Cometido, ExcepcionDePermiso, PermisoDeRol, Rol


# Opciones para elegir permisos: agrupadas por módulo y, en cada una, la explicación y el código.
# Ejemplo: («Organizaciones y grupos», [(«grupos.invitar», «Invitar a un grupo… grupos.invitar»), …]).
#   - con_formato: el código va en <code> (para las casillas); sin formato, entre paréntesis (para los
#     desplegables, que no admiten HTML).
def opciones_de_permisos(con_formato=True):
    por_modulo = {}
    for codigo, permiso in sorted(registro.permisos.items()):
        modulo = registro.modulos[codigo.split(".")[0]].verbose_name
        # format_html: la explicación como texto y el código en <code>, para que se vea más discreto.
        texto = format_html("{} <code>{}</code>", permiso.descripcion, codigo) if con_formato else f"{permiso.descripcion} ({codigo})"
        por_modulo.setdefault(str(modulo), []).append((codigo, texto))
    return list(por_modulo.items())


class FormularioDeRol(forms.ModelForm):
    """Ficha de un rol con la lista de permisos para marcar."""

    permisos_del_rol = forms.MultipleChoiceField(
        label="Permisos",
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Lo que puede hacer quien tiene este rol. El superadmin puede hacerlo todo, sin marcar nada.",
    )

    class Meta:
        model = Rol
        fields = ["codigo", "nombre", "descripcion", "nivel"]

    # Prepara la lista de permisos y marca los que ya tiene el rol.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["permisos_del_rol"].choices = opciones_de_permisos()
        if self.instance.pk:
            self.initial["permisos_del_rol"] = list(self.instance.permisos.values_list("permiso", flat=True))


@admin.register(Rol)
class RolEnLaTrastienda(ConAyuda, admin.ModelAdmin):
    """Roles: los del sistema y los personalizados, con sus permisos."""

    ayuda = (
        "Un rol es el nivel de poder de una persona en un grupo o en una organización. Hay tres del "
        "sistema, que no se pueden borrar: «Usuario» (cualquier miembro: vale en su grupo y en todos los "
        "que lo contienen), «Admin del grupo» (solo en ese grupo) y «Admin de la organización» (en ella y "
        "en todos sus grupos). El superadmin no es un rol: puede hacerlo todo.\n\n"
        "Se puede: crear roles de grupo nuevos (por ejemplo, «Tesorería») y, en cualquier rol, marcar o "
        "desmarcar sus permisos. Para dar un rol personalizado a alguien, cambia el rol de su pertenencia "
        "(en la ficha del usuario o del grupo).\n\n"
        "Cuando un módulo nuevo trae permisos, se dan solos a los roles que dice su contrato; después ya "
        "no se tocan."
    )
    form = FormularioDeRol
    list_display = ["nombre", "codigo", "nivel", "del_sistema", "numero_de_permisos"]

    # Columna «permisos»: cuántos tiene.
    @admin.display(description="permisos")
    def numero_de_permisos(self, rol):
        return rol.permisos.count()

    # El código no cambia una vez creado; en los del sistema, tampoco el nivel.
    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return []
        return ["codigo", "nivel"] if obj.del_sistema else ["codigo"]

    # Los roles del sistema no se pueden borrar.
    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and not (obj and obj.del_sistema)

    # Guarda el rol y pone al día sus permisos: añade los marcados y quita los desmarcados.
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        marcados = set(form.cleaned_data["permisos_del_rol"])
        actuales = set(obj.permisos.values_list("permiso", flat=True))
        obj.permisos.filter(permiso__in=actuales - marcados).delete()
        PermisoDeRol.objects.bulk_create([PermisoDeRol(rol=obj, permiso=codigo) for codigo in marcados - actuales])
        if marcados != actuales:
            # bulk_create no lanza señales: se avisa a mano de que los permisos han cambiado.
            from .servicios import invalidar_todos

            invalidar_todos()


class FormularioDeExcepcion(forms.ModelForm):
    """Ficha de una excepción, con el permiso elegido de la lista de permisos declarados."""

    permiso = forms.ChoiceField(label="permiso", help_text="El permiso que se da o se quita.")

    class Meta:
        model = ExcepcionDePermiso
        fields = ["usuario", "grupo", "permiso", "concede", "motivo"]

    # Prepara la lista de permisos.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["permiso"].choices = [("", "---------"), *opciones_de_permisos(con_formato=False)]


@admin.register(ExcepcionDePermiso)
class ExcepcionEnLaTrastienda(ConAyuda, ElegirGrupoConCamino, admin.ModelAdmin):
    """Excepciones individuales: dar o quitar un permiso a una persona en un grupo."""

    ayuda = (
        "Dar o quitar un permiso suelto a una persona en un grupo concreto, por encima de lo que digan "
        "sus roles. Solo vale en ese grupo (no se hereda) y, si hay que elegir, quitar gana a dar. El "
        "motivo queda a la vista del grupo."
    )
    form = FormularioDeExcepcion
    list_display = ["usuario", "grupo", "permiso", "concede", "creada_el"]
    list_filter = ["concede"]


@admin.register(Cometido)
class CometidoEnLaTrastienda(ConAyuda, ElegirGrupoConCamino, admin.ModelAdmin):
    """Cometidos de cada persona en cosas concretas."""

    ayuda = (
        "Cometidos: la función de una persona en algo concreto (facilitar un debate, tomar acta de una "
        "reunión, coordinar un proyecto…). Pueden dar permisos sobre eso concreto. El grupo indica dónde "
        "vive aquello: sus miembros pueden ver quién tiene cada cometido.\n\n"
        "Se reparten desde la aplicación, en cada cosa; aquí solo se consultan."
    )
    list_display = ["usuario", "codigo", "ancla_tipo", "ancla_id", "grupo", "desde"]
    list_filter = ["codigo"]

    # Los cometidos no se crean a mano: necesitan algo concreto (un debate, una reunión…).
    def has_add_permission(self, request):
        return False
