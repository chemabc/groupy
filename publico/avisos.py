"""
Notificaciones del módulo «publico» (las reparte «comunicaciones»; ver su contrato en publico/apps.py). Se
preparan unos segundos después del cambio, así que releen los datos.
"""

from django.urls import reverse

from base.contrato import AvisoPreparado
from grupos.models import Contencion, Pertenencia

from .models import Pagina, RelacionDeConsumo
from .servicios import PUBLICAR


# «GRU Huerta ha publicado «Calendario de siembra» en su web.» La primera vez que se publica una página
# interna, a quienes pueden verla: las personas del grupo y de lo que cuelga de él, y de los grupos que la
# reciben por una relación de publicación y consumo (y lo que cuelga de ellos). Si es de toda la
# organización, a las personas de sus grupos. Nunca a quien la publicó.
#   - pagina_id: la página.
#   - autor_id: quien la publicó.
def publicada(pagina_id, autor_id=None, **resto):
    pagina = Pagina.objects.select_related("grupo", "organizacion").filter(pk=pagina_id, publicada_el__isnull=False).first()
    if pagina is None or pagina.publica:
        return []
    if pagina.grupo_id:
        raices = {pagina.grupo_id} | set(
            RelacionDeConsumo.objects.filter(productor_id=pagina.grupo_id, estado=RelacionDeConsumo.ACEPTADA).values_list("consumidor_id", flat=True)
        )
        grupos = Contencion.objects.filter(antecesor_id__in=raices).values("descendiente_id")
        personas = Pertenencia.objects.filter(grupo_id__in=grupos)
    else:
        personas = Pertenencia.objects.filter(grupo__organizacion_id=pagina.organizacion_id)
    usuarios = tuple(sorted(set(personas.exclude(usuario_id=autor_id).values_list("usuario_id", flat=True))))
    texto = f"{pagina.duena} ha publicado «{pagina.titulo}» en su web."
    return [AvisoPreparado(usuarios=usuarios, texto=texto, enlace=reverse("publico:pagina", args=[pagina.pk]))]


# «GRU Huerta quiere publicar sus páginas para GRU Henares.» A la administración del grupo que las
# recibiría, que es quien la acepta.
#   - relacion_id: la relación propuesta.
def relacion_propuesta(relacion_id, **resto):
    from permisos.servicios import puede

    relacion = RelacionDeConsumo.objects.select_related("productor", "consumidor").filter(pk=relacion_id, estado=RelacionDeConsumo.PROPUESTA).first()
    if relacion is None:
        return []
    candidatos = Pertenencia.objects.filter(grupo_id=relacion.consumidor_id, rol=Pertenencia.ADMIN_GRUPO).select_related("usuario")
    usuarios = tuple(p.usuario_id for p in candidatos if puede(p.usuario, PUBLICAR, grupo=relacion.consumidor_id))
    texto = f"{relacion.productor.nombre} quiere publicar sus páginas para {relacion.consumidor.nombre}. Acéptalo o recházalo en «Publicación y consumo»."
    return [AvisoPreparado(usuarios=usuarios, texto=texto, enlace=reverse("publico:relaciones"))]
