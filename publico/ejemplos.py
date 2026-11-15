"""
Webs de ejemplo: la portada pública de la plataforma («Bienvenida», del superadmin) y la de ORG Tajo
(«Quiénes somos»), una página interna de ORG Tajo («Normas de convivencia»), la miniweb de GRU Henares
(«Calendario de la huerta», de Lince, que ven GRU Henares, GRU Sorbe y GRU Badiel) y la de GRU Jarama
(«Asambleas de zona»), y GRU Arga (de ORG Ebro) como grupo de actividad que publica «Taller de bicis» para
GRU Henares. Los crea y borra la orden «python manage.py ejemplos».
"""

from django.contrib.auth import get_user_model

from grupos.ejemplos import organizaciones_de_ejemplo
from grupos.models import Grupo, Organizacion

from . import servicios
from .models import Pagina, RelacionDeConsumo

# Título de la página de bienvenida de la plataforma (sirve para saber si ya están los ejemplos).
BIENVENIDA = "Bienvenida"


# Crea una página, le pone el texto y la publica (función interna).
def _publicada(usuario, ambito, titulo, texto, orden=10, publica=False):
    pagina = servicios.crear(usuario, ambito, titulo, orden, publica)
    pagina = servicios.guardar(usuario, pagina, texto, pagina.version)
    return servicios.publicar(usuario, pagina)


# Crea las webs de ejemplo si no están y existen las personas y los grupos de ejemplo.
def crear():
    personas = {u.alias: u for u in get_user_model().objects.filter(alias__in=["superadmin", "Lince", "Zorro"])}
    grupos = {g.nombre: g for g in Grupo.objects.filter(nombre__in=["GRU Henares", "GRU Jarama", "GRU Arga"])}
    tajo = Organizacion.objects.filter(nombre="ORG Tajo").first()
    if len(personas) < 3 or len(grupos) < 3 or tajo is None or Pagina.objects.filter(titulo=BIENVENIDA, organizacion__isnull=True).exists():
        return
    superadmin, lince, zorro = personas["superadmin"], personas["Lince"], personas["Zorro"]
    _publicada(
        superadmin, "p", BIENVENIDA,
        "## Una herramienta para asambleas\n\nOrganizaciones y grupos que se coordinan sin jerarquías: reuniones, "
        "proyectos, debates, consultas y actas.\n\n- Cada grupo decide qué hace público.\n- Para participar, pide entrar "
        "a tu organización.", orden=1,
    )
    _publicada(superadmin, "p", "Cómo participar", "## Cómo participar\n\n1. Habla con tu asamblea.\n2. Te darán una cuenta con un alias.", orden=2)
    _publicada(
        superadmin, f"o{tajo.pk}", "Quiénes somos",
        "## ORG Tajo\n\nAsambleas de barrio de la cuenca del Tajo. Nos reunimos los jueves.", orden=1, publica=True,
    )
    _publicada(superadmin, f"o{tajo.pk}", "Normas de convivencia", "## Normas de convivencia\n\n- Respeto.\n- Turnos de palabra.", orden=2)
    _publicada(
        superadmin, f"g{grupos['GRU Jarama'].pk}", "Asambleas de zona",
        "## Asambleas de zona\n\nEl primer sábado de cada mes, en el centro social.",
    )
    _publicada(
        lince, f"g{grupos['GRU Henares'].pk}", "Calendario de la huerta",
        "## Calendario de la huerta\n\n| Mes | Qué |\n|---|---|\n| Noviembre | Habas y ajos |\n| Diciembre | Poda |\n\n"
        "Más en la [carpeta compartida](https://drive.google.com/drive/folders/ejemplo).",
    )
    _publicada(zorro, f"g{grupos['GRU Arga'].pk}", "Taller de bicis", "## Taller de bicis\n\nArreglamos bicis los martes por la tarde. Trae la tuya.")
    relacion = servicios.proponer_relacion(zorro, grupos["GRU Arga"], grupos["GRU Henares"], "Para que la gente de GRU Henares vea el taller.")
    servicios.aceptar_relacion(lince, relacion)


# Borra las webs de ejemplo: las de la plataforma creadas por el superadmin de ejemplo y todas las de las
# organizaciones de ejemplo (con sus imágenes y relaciones).
def borrar():
    organizaciones = organizaciones_de_ejemplo()
    RelacionDeConsumo.objects.filter(productor__organizacion__in=organizaciones).delete()
    RelacionDeConsumo.objects.filter(consumidor__organizacion__in=organizaciones).delete()
    paginas = Pagina.objects.filter(organizacion__in=organizaciones) | Pagina.objects.filter(organizacion__isnull=True, creada_por__alias="superadmin")
    ficheros = [imagen.fichero.name for pagina in paginas for imagen in pagina.imagenes.all()]
    paginas.delete()
    servicios.borrar_ficheros(ficheros)
