"""
Formularios del módulo «publico».
"""

from django import forms

from grupos.models import Grupo


class FormularioDePagina(forms.Form):
    """Crear una página (dónde, título, orden y si es pública) o cambiar sus datos (sin «dónde»)."""

    ambito = forms.ChoiceField(label="Dónde", help_text="La web de un grupo, la de una organización o, si eres superadmin, la portada de la plataforma.")
    titulo = forms.CharField(label="Título", max_length=120, help_text="Es el nombre de la pestaña: «Quiénes somos», «Calendario».")
    orden = forms.IntegerField(label="Orden", min_value=0, max_value=999, initial=10, help_text="Posición de la pestaña: los números bajos salen antes.")
    publica = forms.BooleanField(
        label="Pública (sale en la portada, sin sesión)", required=False,
        help_text="Solo para las páginas de una organización (las de la plataforma siempre lo son; las de un grupo, nunca).",
    )

    # Prepara el formulario.
    #   - ambitos: (clave, nombre) donde se puede crear; None al cambiar una que ya existe.
    #   - publica_posible: si se puede marcar «pública» (al cambiar una de una organización).
    def __init__(self, *args, ambitos, publica_posible=True, **kwargs):
        super().__init__(*args, **kwargs)
        if ambitos is None:
            del self.fields["ambito"]
        else:
            self.fields["ambito"].choices = ambitos
        if not publica_posible:
            del self.fields["publica"]


class FormularioDeImagen(forms.Form):
    """Subir una imagen a una página."""

    imagen = forms.ImageField(
        label="Imagen", help_text="PNG, JPG, WebP o GIF, hasta 5 MB.",
        widget=forms.ClearableFileInput(attrs={"accept": ".png,.jpg,.jpeg,.webp,.gif"}),
    )


class FormularioDeRelacion(forms.Form):
    """Proponer que uno de mis grupos publique para otro grupo."""

    productor = forms.ModelChoiceField(label="Grupo que publica", queryset=Grupo.objects.none(), help_text="Uno de los grupos que administras.")
    consumidor = forms.ModelChoiceField(
        label="Grupo que las recibe", queryset=Grupo.objects.none(),
        help_text="Lo verán ese grupo y los que cuelgan de él, cuando su administración lo acepte.",
    )
    mensaje = forms.CharField(label="Mensaje", max_length=300, required=False, help_text="Por qué lo propones, para quien tiene que aceptarlo.")

    # Prepara los desplegables.
    #   - productores: los grupos que administra quien propone.
    def __init__(self, *args, productores, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["productor"].queryset = Grupo.objects.filter(pk__in=[g.pk for g in productores]).select_related("organizacion").order_by("organizacion__nombre", "nombre")
        self.fields["consumidor"].queryset = Grupo.objects.select_related("organizacion").order_by("organizacion__nombre", "nombre")
        for campo in ("productor", "consumidor"):
            self.fields[campo].label_from_instance = lambda g: f"{g.organizacion.nombre} › {g.nombre}"
