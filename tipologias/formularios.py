"""
Formularios de la pantalla «Configuración → Tipologías».
"""

from django import forms

from .models import Campo


class FormularioDeTipologia(forms.Form):
    """Nuevo tipo o subtipo: nombre, descripción, de qué es subtipo y de quién es."""

    nombre = forms.CharField(label="Nombre", max_length=80, help_text="Como se verá en las listas: «Concentración».")
    descripcion = forms.CharField(
        label="Descripción", required=False, widget=forms.Textarea(attrs={"rows": 2}), help_text="Para qué sirve, en una o dos frases."
    )
    padre = forms.TypedChoiceField(
        label="Subtipo de", coerce=int, empty_value=None, required=False,
        help_text="Vacío: un tipo principal. Si eliges uno, el nuevo hereda sus campos.",
    )
    organizacion = forms.TypedChoiceField(
        label="De quién", coerce=int, empty_value=None, required=False,
        help_text="«Común» sirve en todas las organizaciones (solo el superadmin). Si no, solo en esa organización.",
    )

    # Prepara los desplegables con lo que la persona puede elegir (lo calcula la vista).
    #   - padres: (id, camino) de las tipologías de la familia.
    #   - organizaciones: (número, nombre) de las que gestiona.
    #   - comun: si puede crear tipos comunes (el superadmin).
    def __init__(self, *args, padres, organizaciones, comun, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["padre"].choices = [("", "— Ninguno (tipo principal) —"), *padres]
        self.fields["organizacion"].choices = ([("", "Común (todas las organizaciones)")] if comun else []) + list(organizaciones)
        if not comun:
            self.fields["organizacion"].required = True


class FormularioDeEdicion(forms.Form):
    """Cambiar el nombre y la descripción de un tipo."""

    nombre = forms.CharField(label="Nombre", max_length=80, help_text="Como se verá en las listas.")
    descripcion = forms.CharField(label="Descripción", required=False, widget=forms.Textarea(attrs={"rows": 2}), help_text="Para qué sirve.")


class FormularioDeCampo(forms.Form):
    """Nuevo campo de un tipo."""

    nombre = forms.CharField(label="Pregunta", max_length=80, help_text="Lo que se pide: «Número de asistentes previstos».")
    tipo = forms.ChoiceField(label="Tipo de dato", choices=Campo.TIPOS, help_text="Qué clase de respuesta es.")
    obligatorio = forms.BooleanField(label="Obligatorio", required=False, help_text="Si hay que rellenarlo para guardar.")
    ayuda = forms.CharField(label="Explicación", max_length=200, required=False, help_text="Texto de ayuda bajo el campo (opcional).")
    opciones = forms.CharField(
        label="Opciones", required=False, widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Solo para «Lista de opciones»: una por línea.",
    )


class FormularioDeTareaModelo(forms.Form):
    """Nueva tarea modelo de un tipo de proyecto."""

    titulo = forms.CharField(label="Tarea", max_length=200, help_text="Qué hay que hacer: «Pedir permiso al distrito».")
    descripcion = forms.CharField(
        label="Descripción", required=False, widget=forms.Textarea(attrs={"rows": 2}), help_text="Detalles o consejos (opcional)."
    )
    dias = forms.IntegerField(
        label="Plazo en días", required=False, min_value=0, max_value=3650,
        help_text="Días desde que se crea el proyecto hasta su fecha límite. Vacío: sin fecha.",
    )
    espera_a_la_anterior = forms.BooleanField(
        label="Espera a la anterior", required=False, help_text="Queda bloqueada hasta que esté hecha la tarea anterior de la lista.",
    )
