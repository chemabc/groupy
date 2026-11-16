"""
Formularios del módulo «documentos».
"""

from django import forms

from .models import Documento, LimitesDeDocumento


# El campo «Descripción» de los formularios de crear y cambiar un documento (texto, archivo o enlace).
def campo_de_descripcion():
    return forms.CharField(
        label="Descripción", max_length=300, required=False,
        widget=forms.Textarea(attrs={"rows": 2, "maxlength": 300}),
        help_text="De qué trata, en una o dos frases (opcional). Se ve en la lista de documentos al pulsar ⓘ.",
    )


class FormularioDeDocumentoNuevo(forms.Form):
    """
    Crear un documento: tipo, título, descripción y, si no cuelga de nada, quién lo ve (el grupo se elige antes, arriba
    de la pantalla). Si cuelga de algo (una reunión), toma su grupo y su visibilidad, y ese campo no sale.
    """

    tipo = forms.ChoiceField(
        label="Tipo", choices=[(c, n) for c, n in Documento.TIPOS if c in Documento.ESCRITOS],
        help_text="El acta se crea mejor desde su orden del día, que copia los puntos.",
    )
    titulo = forms.CharField(label="Título", max_length=200, help_text="«Orden del día de la asamblea del jueves».")
    descripcion = campo_de_descripcion()
    formato = forms.ChoiceField(
        label="Se escribe en", choices=Documento.FORMATOS, initial=Documento.MARKDOWN,
        help_text="Markdown es lo sencillo (## título, - punto, **negrita**). Typst sirve para maquetar a mano. El PDF sale igual de bien con los dos.",
    )
    visibilidad = forms.ChoiceField(label="Quién lo ve", help_text="Todo nace privado. Quien lo ve puede leerlo y comentarlo.")

    # Prepara el desplegable de visibilidad.
    #   - visibilidades: opciones del selector de audiencias del grupo elegido, o None si cuelga de algo.
    def __init__(self, *args, visibilidades, **kwargs):
        super().__init__(*args, **kwargs)
        if visibilidades is None:
            del self.fields["visibilidad"]
        else:
            self.fields["visibilidad"].choices = visibilidades


class FormularioDeArchivo(forms.Form):
    """Subir un archivo: el fichero, su nombre, su descripción y, si no cuelga de nada, quién lo ve."""

    archivo = forms.FileField(
        label="Archivo",
        help_text="PDF, imagen (PNG, JPG, WebP, GIF), documento abierto (odt, ods, odp, odg) o texto (txt, csv, md), hasta 20 MB. Nunca formatos de Microsoft (docx, xlsx…).",
        widget=forms.ClearableFileInput(attrs={"accept": ".pdf,.png,.jpg,.jpeg,.webp,.gif,.odt,.ods,.odp,.odg,.txt,.csv,.md"}),
    )
    titulo = forms.CharField(label="Nombre", max_length=200, required=False, help_text="Cómo se verá en las listas. Si lo dejas vacío, el nombre del archivo.")
    descripcion = campo_de_descripcion()
    visibilidad = forms.ChoiceField(label="Quién lo ve", help_text="Todo nace privado.")

    # Prepara el desplegable de visibilidad (o lo quita, si cuelga de algo y toma su visibilidad).
    def __init__(self, *args, visibilidades, **kwargs):
        super().__init__(*args, **kwargs)
        if visibilidades is None:
            del self.fields["visibilidad"]
        else:
            self.fields["visibilidad"].choices = visibilidades


class FormularioDeVersion(forms.Form):
    """Subir otra versión de un archivo (las anteriores se guardan)."""

    archivo = forms.FileField(label="Versión nueva", help_text="Del mismo tipo o de otro admitido. Las versiones anteriores se guardan.")


class FormularioDeEnlace(forms.Form):
    """
    Un enlace: su nombre, su descripción y adónde lleva, a otra web (Drive…) o a otro documento de la plataforma (uno de
    los dos). También sirve para cambiar el nombre y la descripción de un archivo (solo_nombre).
    """

    titulo = forms.CharField(label="Nombre", max_length=200, required=False, help_text="Cómo se verá en las listas.")
    descripcion = campo_de_descripcion()
    url = forms.URLField(
        label="Dirección", max_length=1000, required=False, assume_scheme="https",
        help_text="De otra web: «https://drive.google.com/…». Déjala vacía si enlazas un documento de aquí.",
    )
    documento = forms.ModelChoiceField(
        label="O un documento de aquí", queryset=Documento.objects.none(), required=False, empty_label="(ninguno)",
        help_text="Un texto escrito en el editor que ya ves (los más recientes primero).",
    )
    visibilidad = forms.ChoiceField(label="Quién lo ve", help_text="Todo nace privado.")

    # Prepara los desplegables.
    #   - documentos: los que se pueden enlazar (consulta).
    #   - visibilidades: opciones de quién lo ve, o None si no se elige (cuelga de algo, o se cambia uno ya hecho).
    #   - solo_nombre: para cambiar el nombre de un archivo (sin dirección ni documento).
    def __init__(self, *args, documentos, visibilidades, solo_nombre=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["documento"].queryset = documentos
        self.fields["documento"].label_from_instance = lambda d: f"{d.titulo} ({d.grupo.nombre})"
        if visibilidades is None:
            del self.fields["visibilidad"]
        else:
            self.fields["visibilidad"].choices = visibilidades
        if solo_nombre:
            del self.fields["url"], self.fields["documento"]

    # Un enlace lleva a un sitio, y solo a uno; un archivo solo cambia de nombre.
    def clean(self):
        datos = super().clean()
        if "url" in self.fields and bool(datos.get("url")) == bool(datos.get("documento")):
            raise forms.ValidationError("Pon una dirección o elige un documento de aquí (uno de los dos).")
        return datos


class FormularioDeLimites(forms.ModelForm):
    """Cuántas personas escriben y comentan a la vez, en un nivel (plataforma, organización, grupo o documento). Vacío: sin límite en ese nivel."""

    class Meta:
        model = LimitesDeDocumento
        fields = ["max_escritores", "max_comentaristas"]
