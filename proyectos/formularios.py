"""
Formularios del módulo «proyectos».
"""

from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from etiquetas.formularios import CampoDeEtiquetas

from .models import Proyecto, Recurso, Tarea


# Campo de fecha con el calendario del navegador.
def _fecha():
    return forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class FormularioDeProyecto(forms.ModelForm):
    """Datos de un proyecto (o subproyecto) y quién lo ve."""

    visibilidad = forms.ChoiceField(label="Quién lo ve", help_text="Todo nace privado. Las opciones dependen de lo que permite la organización.")

    class Meta:
        model = Proyecto
        fields = ["titulo", "objetivo_general", "objetivos_especificos", "alcance", "riesgos", "inicio", "limite"]
        widgets = {
            "objetivo_general": forms.Textarea(attrs={"rows": 2}),
            "objetivos_especificos": forms.Textarea(attrs={"rows": 3}),
            "alcance": forms.Textarea(attrs={"rows": 2}),
            "riesgos": forms.Textarea(attrs={"rows": 2}),
            "inicio": _fecha(),
            "limite": _fecha(),
        }

    # Prepara el desplegable de visibilidad (en lo personal no hay que elegir: solo lo ve quien lo crea),
    # las etiquetas (solo en los de grupo) y la casilla de las tareas modelo (solo al crear, si su tipo
    # propone alguna).
    #   - visibilidades: (clave, explicación) del selector de audiencias, o None si es personal.
    #   - organizacion: la del grupo, para sugerir sus etiquetas; None si es personal (sin etiquetas).
    #   - tareas_modelo: las tareas modelo que propone su tipo (al crear).
    def __init__(self, *args, visibilidades, organizacion=None, tareas_modelo=(), **kwargs):
        super().__init__(*args, **kwargs)
        if visibilidades is None:
            del self.fields["visibilidad"]
        else:
            self.fields["visibilidad"].choices = visibilidades
        if organizacion is not None:
            self.fields["etiquetas"] = CampoDeEtiquetas(organizacion=organizacion)
        if tareas_modelo:
            titulos = ", ".join(f"«{tarea.titulo}»" for tarea in tareas_modelo)
            self.fields["con_tareas_modelo"] = forms.BooleanField(
                label=f"Crear las {len(tareas_modelo)} tareas modelo de su tipo" if len(tareas_modelo) > 1 else "Crear la tarea modelo de su tipo",
                required=False, initial=True, help_text=f"{titulos}. Te quedan a ti como responsable; luego puedes encargarlas a otras personas.",
            )

    # Los datos del proyecto (sin la visibilidad, que no es un campo que se copie tal cual).
    def datos_del_proyecto(self):
        return {campo: self.cleaned_data[campo] for campo in self.Meta.fields}


class CampoDeAlias(forms.CharField):
    """Cuadro donde se escribe el alias de una persona; devuelve la persona (o error si no existe)."""

    # Busca la persona por su alias (sin distinguir mayúsculas).
    def clean(self, valor):
        valor = super().clean(valor)
        if not valor:
            return None
        persona = get_user_model().objects.filter(alias__iexact=valor.strip()).first()
        if persona is None:
            raise forms.ValidationError(f"No hay nadie con el alias «{valor}».")
        return persona


class FormularioDeTarea(forms.ModelForm):
    """Datos de una tarea: qué, para cuándo, quién se encarga y quién colabora (por alias)."""

    responsable = CampoDeAlias(label="Responsable", help_text="El alias de quien se encarga. Vacío: tú.", required=False)
    colaboradores = forms.CharField(
        label="Colaboran", required=False, help_text="Alias de quienes ayudan, separados por comas. Opcional."
    )
    visibilidad = forms.ChoiceField(label="Quién la ve", required=False, help_text="Solo en las tareas sueltas de un grupo.")
    espera_a = forms.ModelMultipleChoiceField(
        label="Espera a", queryset=Tarea.objects.none(), required=False, widget=forms.CheckboxSelectMultiple,
        help_text="Tareas que tienen que estar hechas antes. Mientras no lo estén, esta queda bloqueada sola.",
    )

    class Meta:
        model = Tarea
        fields = ["titulo", "descripcion", "limite", "estado"]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3}), "limite": _fecha()}

    # Prepara los campos según dónde está la tarea.
    #   - visibilidades: opciones de visibilidad (tarea suelta) o None (en un proyecto o personal).
    #   - personal: si es personal (sin responsable ni colaboradores que elegir).
    #   - candidatas: tareas del mismo árbol a las que puede esperar (consulta), o None si no está en un
    #     proyecto (entonces no hay dependencias).
    def __init__(self, *args, visibilidades=None, personal=False, candidatas=None, **kwargs):
        super().__init__(*args, **kwargs)
        if candidatas is None:
            del self.fields["espera_a"]
        else:
            self.fields["espera_a"].queryset = candidatas
            self.fields["espera_a"].label_from_instance = lambda otra: f"{otra.titulo} ({otra.proyecto.titulo}, {otra.get_estado_display().lower()})"
            if self.instance.pk and "espera_a" not in self.initial:
                self.initial["espera_a"] = [otra.pk for otra in self.instance.espera_a.all()]
        if visibilidades is None:
            del self.fields["visibilidad"]
        else:
            self.fields["visibilidad"].choices = visibilidades
            self.fields["visibilidad"].required = True
        if personal:
            del self.fields["responsable"]
            del self.fields["colaboradores"]
        elif self.instance.pk:
            self.initial.setdefault("responsable", self.instance.responsable.alias)
            self.initial.setdefault("colaboradores", ", ".join(p.alias for p in self.instance.colaboradores.all()))

    # Convierte la lista de alias de quienes colaboran en personas (sin distinguir mayúsculas). Una
    # consulta.
    def clean_colaboradores(self):
        alias = [a.strip() for a in self.cleaned_data.get("colaboradores", "").split(",") if a.strip()]
        if not alias:
            return []
        condicion = Q()
        for uno in alias:
            condicion |= Q(alias__iexact=uno)
        personas = {p.alias.lower(): p for p in get_user_model().objects.filter(condicion)}
        faltan = [a for a in alias if a.lower() not in personas]
        if faltan:
            raise forms.ValidationError(f"No hay nadie con estos alias: {', '.join(faltan)}.")
        return list(personas.values())

    # Los datos de la tarea para el servicio. Sin responsable escrita, quien la crea (o la que tenía).
    #   - usuario: quien rellena el formulario.
    def datos_de_la_tarea(self, usuario):
        datos = {campo: self.cleaned_data[campo] for campo in self.Meta.fields}
        if "responsable" in self.fields:
            datos["responsable"] = self.cleaned_data.get("responsable") or (self.instance.responsable if self.instance.pk else usuario)
        return datos



class FormularioDeRecurso(forms.ModelForm):
    """Un recurso que le hace falta a un proyecto: qué, cuánto y de dónde sale."""

    class Meta:
        model = Recurso
        fields = ["nombre", "cantidad", "origen"]
