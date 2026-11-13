"""
Formularios de la sección «Organizaciones y grupos». Solo recogen y comprueban lo escrito; lo que se hace
con ello está en grupos/servicios.py, y quién puede hacerlo lo decide la vista (grupos/views.py).
"""

from django import forms
from django.contrib.auth import get_user_model


class FormularioDeGrupo(forms.Form):
    """Datos de un grupo: nombre, descripción, ámbito y, a veces, el grupo padre."""

    nombre = forms.CharField(label="Nombre", max_length=100, help_text="No puede repetirse dentro de la organización.")
    descripcion = forms.CharField(
        label="Descripción", required=False, widget=forms.Textarea(attrs={"rows": 2}), help_text="Para qué existe el grupo y qué hace."
    )
    ambito = forms.CharField(
        label="Ámbito geográfico", max_length=100, required=False, help_text="Zona que abarca (un barrio, un municipio…). Opcional."
    )
    padre = forms.TypedChoiceField(
        label="Grupo padre", coerce=int, empty_value=None, required=False,
        help_text="Grupo que lo contiene. Moverlo cambia quién cuenta como miembro de qué. Solo el admin de la organización.",
    )

    # Prepara el desplegable del padre con los grupos posibles, o lo quita si no se puede cambiar.
    #   - padres: (id, camino) de los grupos de la organización que pueden contenerlo, o None para no
    #     ofrecer el campo.
    def __init__(self, *args, padres=None, **kwargs):
        super().__init__(*args, **kwargs)
        if padres is None:
            del self.fields["padre"]
        else:
            self.fields["padre"].choices = [("", "— Ninguno (grupo principal) —"), *padres]


class FormularioDeOrganizacion(forms.Form):
    """Datos de una organización y si sus miembros ven la lista de miembros de sus grupos."""

    nombre = forms.CharField(label="Nombre", max_length=100, help_text="No puede repetirse.")
    descripcion = forms.CharField(
        label="Descripción", required=False, widget=forms.Textarea(attrs={"rows": 2}), help_text="Qué es y a qué se dedica."
    )
    miembros_ven_miembros = forms.BooleanField(
        label="Los miembros ven la lista de miembros de sus grupos",
        required=False,
        help_text=(
            "Si se desmarca, en todos los grupos de la organización solo los admins ven quién está. Marcarlo no "
            "sirve si el superadmin ha quitado al rol «usuario» el permiso «grupos.ver_miembros»."
        ),
    )


class FormularioDeOrganizacionNueva(forms.Form):
    """Organización nueva con su primer grupo (toda organización tiene al menos uno). Solo el superadmin."""

    nombre = forms.CharField(label="Nombre de la organización", max_length=100, help_text="Por ejemplo, «ORG Miño».")
    primer_grupo = forms.CharField(label="Nombre de su primer grupo", max_length=100, help_text="Su grupo general, por ejemplo «GRU Miño».")
    descripcion = forms.CharField(
        label="Descripción", required=False, widget=forms.Textarea(attrs={"rows": 2}), help_text="Qué es y a qué se dedica."
    )


class FormularioDeAlias(forms.Form):
    """Una persona, por su alias exacto (se compara sin tildes ni mayúsculas)."""

    alias = forms.CharField(label="Alias", max_length=30, help_text="El alias de la persona, tal como lo usa para entrar.")

    # Comprueba que el alias existe y deja el usuario en cleaned_data["usuario"].
    def clean_alias(self):
        Usuario = get_user_model()
        try:
            self.cleaned_data["usuario"] = Usuario._default_manager.get_by_natural_key(self.cleaned_data["alias"])
        except Usuario.DoesNotExist:
            raise forms.ValidationError("No hay nadie con ese alias.") from None
        return self.cleaned_data["alias"]


class FormularioDeAdmision(FormularioDeAlias):
    """Admitir a una persona en el grupo: su alias y con qué rol."""

    rol = forms.ChoiceField(label="Rol", help_text="«Usuario» para un miembro normal. Hacer admin a alguien pide un permiso aparte.")

    # Prepara el desplegable de roles con los que puede dar quien admite.
    #   - roles: pares (código, nombre).
    def __init__(self, *args, roles, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rol"].choices = roles


class FormularioDeRelacion(forms.Form):
    """Relación libre entre dos grupos de la misma organización."""

    origen = forms.TypedChoiceField(label="Grupo", coerce=int, help_text="Uno de los grupos que puedes editar.")
    tipo = forms.CharField(label="Relación", max_length=50, help_text="En pocas palabras: «colabora con», «nació de»…")
    destino = forms.TypedChoiceField(label="Con el grupo", coerce=int, help_text="Debe ser de la misma organización.")
    descripcion = forms.CharField(label="Detalles", required=False, widget=forms.Textarea(attrs={"rows": 2}), help_text="Opcional.")

    # Prepara los desplegables.
    #   - origenes: (id, «ORG › camino») de los grupos que puede editar.
    #   - destinos: (id, «ORG › camino») de los grupos con los que puede relacionarlos.
    def __init__(self, *args, origenes, destinos, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["origen"].choices = origenes
        self.fields["destino"].choices = destinos
