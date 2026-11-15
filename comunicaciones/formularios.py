"""
Formularios de la sección «Comunicaciones» y de «Plataforma → Catálogos comunes → Niveles de aviso».
"""

from django import forms
from django.contrib.auth import get_user_model

from base.formularios import CampoDePersonas

from .models import NivelDeAviso


class FormularioDeAviso(forms.Form):
    """Aviso de una administración a grupos y personas."""

    administracion = forms.ChoiceField(label="En nombre de", help_text="La administración que avisa: la de un grupo que administras, la de tu organización…")
    nivel = forms.ModelChoiceField(label="Nivel", queryset=NivelDeAviso.objects.all(), empty_label=None, help_text="Cuánta atención pide. Se ve con su color.")
    asunto = forms.CharField(label="Asunto", max_length=120, help_text="De qué va, en pocas palabras.")
    texto = forms.CharField(label="Texto", widget=forms.Textarea(attrs={"rows": 4}), help_text="El aviso.")
    grupos = forms.TypedMultipleChoiceField(
        label="A los grupos", coerce=int, required=False, widget=forms.SelectMultiple(attrs={"size": 6}),
        help_text="Cada grupo con todos sus subgrupos. Mantén pulsado Ctrl para elegir varios.",
    )
    alias = forms.CharField(
        label="A las personas", required=False, help_text="Alias separados por comas, si quieres avisar a alguien suelto.",
    )
    permite_responder = forms.BooleanField(
        label="Se puede responder", required=False,
        help_text="Si se marca, el aviso lleva un enlace para abrir una conversación con esta administración.",
    )

    # Prepara los desplegables.
    #   - administraciones: (clave, nombre) de las que puede usar quien escribe.
    #   - grupos: (id, «ORG › camino») de los grupos que alcanzan.
    def __init__(self, *args, administraciones, grupos, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["administracion"].choices = administraciones
        self.fields["grupos"].choices = grupos

    # Comprueba que existen los alias y deja los usuarios en cleaned_data["personas"].
    def clean_alias(self):
        Usuario = get_user_model()
        personas, desconocidos = [], []
        for alias in filter(None, (trozo.strip() for trozo in self.cleaned_data["alias"].split(","))):
            try:
                personas.append(Usuario._default_manager.get_by_natural_key(alias))
            except Usuario.DoesNotExist:
                desconocidos.append(alias)
        if desconocidos:
            raise forms.ValidationError(f"No hay nadie con estos alias: {', '.join(desconocidos)}.")
        self.cleaned_data["personas"] = personas
        return self.cleaned_data["alias"]


class FormularioDeConversacion(forms.Form):
    """Conversación nueva con una administración."""

    administracion = forms.ChoiceField(
        label="A", help_text="La administración de uno de tus grupos (o de uno que los contiene), la de tu organización o el superadmin."
    )
    asunto = forms.CharField(label="Asunto", max_length=120, help_text="De qué trata, en pocas palabras.")
    texto = forms.CharField(label="Mensaje", widget=forms.Textarea(attrs={"rows": 4}), help_text="Lo que quieres contar o preguntar.")

    # Prepara el desplegable de administraciones: (clave, nombre).
    def __init__(self, *args, administraciones, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["administracion"].choices = administraciones


class FormularioDeMensaje(forms.Form):
    """Respuesta en una conversación."""

    texto = forms.CharField(label="Respuesta", widget=forms.Textarea(attrs={"rows": 3}), help_text="Tu mensaje.")


class FormularioDeNivel(forms.ModelForm):
    """Nivel de aviso: nombre, descripción, color y orden."""

    class Meta:
        model = NivelDeAviso
        fields = ["nombre", "descripcion", "color", "orden"]
        widgets = {"color": forms.TextInput(attrs={"type": "color"})}


class FormularioDeSala(forms.Form):
    """Mensaje en la sala de un grupo."""

    texto = forms.CharField(
        label="Mensaje", max_length=4000, widget=forms.Textarea(attrs={"rows": 2}), help_text="Lo lee todo el grupo."
    )


class FormularioAPersona(forms.Form):
    """Primer mensaje (o uno más) a una persona, elegida con el selector de personas."""

    persona = CampoDePersonas(
        label="A", vacio="Nadie todavía", error_fuera="No compartes grupo con esta persona (o hay un bloqueo)",
        help_text="Alguien que comparte algún grupo contigo. Si su organización no enseña la lista, escribe su alias exacto.",
    )
    texto = forms.CharField(label="Mensaje", max_length=4000, widget=forms.Textarea(attrs={"rows": 4}), help_text="Solo lo leerá esa persona.")

    # Prepara el selector: la dirección de la lista y quién se puede elegir.
    #   - url_de_la_lista: dirección que devuelve la lista (comunicaciones:personas_para_escribir).
    #   - permitidas: función que devuelve los ids de las personas a las que se puede escribir.
    def __init__(self, *args, url_de_la_lista, permitidas, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["persona"].permitidas = permitidas
        self.fields["persona"].widget.url_de_la_lista = url_de_la_lista


class FormularioDeMensajeAPersona(forms.Form):
    """Mensaje en una conversación entre dos personas."""

    texto = forms.CharField(label="Mensaje", max_length=4000, widget=forms.Textarea(attrs={"rows": 2}), help_text="Solo lo lee la otra persona.")
