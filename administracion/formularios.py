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
