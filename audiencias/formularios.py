"""
Formularios de la pantalla «Configuración → Visibilidad».
"""

from django import forms

# Hasta dónde se puede subir: (número de niveles, explicación). Pocos grupos tienen más de seis niveles.
ALTURAS = [
    (0, "Solo el propio grupo (y sus subgrupos)"),
    (1, "Hasta el grupo padre"),
    (2, "Hasta el grupo abuelo"),
    (3, "Hasta 3 niveles por encima"),
    (4, "Hasta 4 niveles por encima"),
    (5, "Hasta 5 niveles por encima"),
    (6, "Hasta 6 niveles por encima"),
]


class FormularioDeVisibilidad(forms.Form):
    """Qué niveles de visibilidad ofrece una organización a quien publica algo en ella."""

    altura_maxima = forms.TypedChoiceField(
        label="Hasta dónde se puede subir",
        coerce=int,
        choices=ALTURAS,
        help_text=(
            "Al elegir «mi grupo y los de arriba», hasta qué grupo se puede abrir. Cada nivel incluye a todas "
            "las personas de ese grupo y de todos sus subgrupos (también los grupos hermanos)."
        ),
    )
    permite_toda_la_organizacion = forms.BooleanField(
        label="Permitir «toda la organización»",
        required=False,
        help_text="Si se puede publicar para todas las personas de todos los grupos de la organización.",
    )
    permite_publico = forms.BooleanField(
        label="Permitir lo público",
        required=False,
        help_text="Si se puede publicar para cualquiera, también sin cuenta. Lo público nunca muestra alias.",
    )
