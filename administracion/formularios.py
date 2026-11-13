"""
Formularios de la sección «Usuarios» del superadmin.
"""

from django import forms

from grupos.models import Organizacion


# Organizaciones para los desplegables: lista de (número, nombre), en orden. Una consulta. Las vistas la
# cargan una vez y la pasan al formulario y a lo que más la necesite (los nombres de la tabla).
def organizaciones():
    return list(Organizacion.objects.order_by("nombre").values_list("pk", "nombre"))


class FormularioDeAlta(forms.Form):
    """Alta de una persona en la bóveda: nombre real, correo oficial y organización."""

    nombre = forms.CharField(
        label="Nombre real", max_length=150, help_text="Nombre y apellidos. Solo se verá dentro de su ficha."
    )
    correo_oficial = forms.EmailField(
        label="Correo oficial",
        help_text="El de su organización. Se borra al validarla (queda solo su huella, para que no se repita).",
    )
    organizacion = forms.TypedChoiceField(
        label="Organización",
        coerce=int,
        help_text="Si la organización tiene dominios permitidos, el correo debe ser de uno de ellos.",
    )

    # Prepara el desplegable de organizaciones.
    #   - organizaciones: la lista de (número, nombre), ya cargada por la vista.
    def __init__(self, *args, organizaciones, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organizacion"].choices = [("", "---------"), *organizaciones]


class FormularioDePersona(forms.Form):
    """Ficha de una persona de la bóveda: nombre, organización y, si hace falta, un correo nuevo."""

    nombre = forms.CharField(label="Nombre real", max_length=150, help_text="Nombre y apellidos reales.")
    organizacion = forms.TypedChoiceField(
        label="Organización", coerce=int, empty_value=None, required=False, help_text="Organización en la que se dio de alta."
    )
    correo_oficial = forms.EmailField(
        label="Correo oficial",
        required=False,
        help_text=(
            "Mientras está pendiente, su correo oficial (se puede corregir). Si ya está validada, el correo se "
            "borró: escribe aquí uno nuevo solo si hay que cambiarlo, y tendrá que validarse otra vez."
        ),
    )

    # Prepara el desplegable de organizaciones.
    #   - organizaciones: la lista de (número, nombre), ya cargada por la vista.
    def __init__(self, *args, organizaciones, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organizacion"].choices = [("", "---------"), *organizaciones]


class FormularioDeDominios(forms.Form):
    """Dominios de correo permitidos de una organización, uno por línea."""

    organizacion = forms.IntegerField(widget=forms.HiddenInput)
    dominios = forms.CharField(
        label="Dominios",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Uno por línea (o separados por comas), sin la arroba: «educa.madrid.org». Vacío: cualquier dominio.",
    )


# Permisos para los desplegables, agrupados por módulo: [(nombre del módulo, [(código, descripción)])].
# Sale del registro (en memoria), sin consultas.
def permisos_por_modulo():
    from base.registro import registro

    grupos = {}
    for codigo, permiso in sorted(registro.permisos.items()):
        modulo = registro.modulos[codigo.split(".")[0]].verbose_name
        grupos.setdefault(modulo, []).append((codigo, f"{permiso.descripcion} ({codigo})"))
    return sorted(grupos.items())


class FormularioDeRol(forms.Form):
    """Rol nuevo: código interno, nombre visible y para qué sirve. Los roles nuevos son de grupo."""

    codigo = forms.RegexField(
        label="Código", max_length=40, regex=r"^[a-z][a-z0-9_]*$",
        error_messages={"invalid": "Solo minúsculas sin tildes, números y «_», empezando por letra."},
        help_text="Nombre interno, sin espacios ni tildes («tesoreria»). No se puede cambiar después.",
    )
    nombre = forms.CharField(label="Nombre", max_length=60, help_text="Como se verá: «Tesorería».")
    descripcion = forms.CharField(
        label="Descripción", required=False, widget=forms.Textarea(attrs={"rows": 2}), help_text="Para qué sirve, en lenguaje llano."
    )


class FormularioDeDatosDeRol(forms.Form):
    """Cambiar el nombre y la descripción de un rol."""

    nombre = forms.CharField(label="Nombre", max_length=60, help_text="Como se verá en las listas.")
    descripcion = forms.CharField(
        label="Descripción", required=False, widget=forms.Textarea(attrs={"rows": 2}), help_text="Para qué sirve."
    )


class FormularioDePersonaGrupoYPermiso(forms.Form):
    """Una persona (por su alias), un grupo y un permiso. Base de las excepciones y de «Explicar»."""

    alias = forms.CharField(label="Alias", max_length=30, help_text="El alias de la persona.")
    grupo = forms.TypedChoiceField(label="Grupo", coerce=int, help_text="El grupo donde se mira el permiso.")
    permiso = forms.ChoiceField(label="Permiso", help_text="Agrupados por módulo.")

    # Prepara los desplegables.
    #   - grupos: (id, «ORG › camino») de todos los grupos.
    def __init__(self, *args, grupos, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["grupo"].choices = [("", "---------"), *grupos]
        self.fields["permiso"].choices = [("", "---------"), *permisos_por_modulo()]

    # Comprueba que el alias existe y deja el usuario en cleaned_data["usuario"].
    def clean_alias(self):
        from django.contrib.auth import get_user_model

        Usuario = get_user_model()
        try:
            self.cleaned_data["usuario"] = Usuario._default_manager.get_by_natural_key(self.cleaned_data["alias"])
        except Usuario.DoesNotExist:
            raise forms.ValidationError("No hay nadie con ese alias.") from None
        return self.cleaned_data["alias"]


class FormularioDeExcepcion(FormularioDePersonaGrupoYPermiso):
    """Excepción individual: dar o quitar un permiso a una persona en un grupo, con su motivo."""

    concede = forms.TypedChoiceField(
        label="Qué se hace", coerce=lambda valor: valor == "dar", widget=forms.RadioSelect,
        choices=[("dar", "Dárselo"), ("quitar", "Quitárselo (gana a cualquier rol)")], initial="dar",
        help_text="Solo vale en ese grupo, no en sus subgrupos ni en los de encima.",
    )
    motivo = forms.CharField(
        label="Motivo", widget=forms.Textarea(attrs={"rows": 2}), help_text="Por qué se hace. Queda a la vista del grupo."
    )
