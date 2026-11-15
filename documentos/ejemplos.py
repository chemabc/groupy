"""
Documentos de ejemplo: en la asamblea base de Nutria (GRU Henares), un orden del día de Lince y el acta que sale
de él, ya aprobada (sus dos acuerdos pasan al registro de decisiones), y el orden del día de la próxima
reunión, en borrador. Además, un PDF subido («Plano del solar») y un enlace a otra web. Los crea y borra la
orden «python manage.py ejemplos».
"""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from grupos.ejemplos import organizaciones_de_ejemplo
from grupos.models import Pertenencia

from . import servicios
from .models import Documento, VersionDeArchivo

# Un PDF muy pequeño pero válido (una página en blanco), para el archivo de ejemplo.
PDF_DE_EJEMPLO = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"
)

# Título del orden del día de ejemplo (sirve para saber si ya están).
PRIMERO = "Orden del día de la asamblea de noviembre"


# Crea los documentos de ejemplo, si no están ya y existen Lince y Nutria (con su asamblea base).
def crear():
    personas = {u.alias: u for u in get_user_model().objects.filter(alias__in=["Lince", "Nutria"])}
    base = Pertenencia.objects.filter(usuario=personas.get("Nutria"), es_base=True).select_related("grupo").first() if "Nutria" in personas else None
    lince = personas.get("Lince")
    if base is None or lince is None or Documento.objects.filter(titulo=PRIMERO).exists():
        return
    odd = servicios.crear(lince, Documento.ODD, PRIMERO, grupo=base.grupo, visibilidad="grupo:0")
    odd = servicios.guardar(lince, odd, odd.titulo, "## Puntos\n\n1. Lectura del acta anterior\n2. El huerto: dónde y cuándo\n3. Ruegos y preguntas", odd.version)
    acta = servicios.acta_desde(lince, odd)
    texto = acta.texto.replace("## Asistentes\n\n", "## Asistentes\n\nLince, Nutria, Garza y 6 personas más.\n\n")
    texto = texto.replace("- [consenso] \n", "- [consenso] El huerto irá en el solar de la calle Mayor\n- [votación 7-1-1] Las asambleas pasan a los jueves\n")
    texto = texto.replace(f"## {servicios.TEMAS}\n\n- \n", f"## {servicios.TEMAS}\n\n- ¿Pedimos ayuda al distrito para el agua?\n")
    acta = servicios.guardar(lince, acta, acta.titulo, texto, acta.version)
    servicios.aprobar(lince, acta)
    servicios.crear(lince, Documento.ODD, "Orden del día de la asamblea de diciembre", grupo=base.grupo, visibilidad="grupo:0")
    # El archivo de ejemplo no pasa por el antivirus (puede no estar arrancado al crear los ejemplos).
    with override_settings(ANTIVIRUS=""):
        servicios.subir_archivo(
            lince, SimpleUploadedFile("plano-del-solar.pdf", PDF_DE_EJEMPLO), "Plano del solar", grupo=base.grupo, visibilidad="grupo:0"
        )
    servicios.enlazar(
        lince, "Carpeta compartida del huerto", url="https://drive.google.com/drive/folders/ejemplo", grupo=base.grupo, visibilidad="grupo:0"
    )


# Borra los documentos de las organizaciones de ejemplo (con su registro de cambios, sus comentarios y los
# ficheros de sus archivos).
def borrar():
    documentos = Documento.objects.filter(grupo__organizacion__in=organizaciones_de_ejemplo())
    ficheros = list(VersionDeArchivo.objects.filter(documento__in=documentos).values_list("fichero", flat=True))
    documentos.delete()
    servicios.borrar_ficheros(ficheros)
