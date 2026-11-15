"""
Lo que el módulo de grupos le cuenta al editor colaborativo para su biblioteca (plantillas, fragmentos,
cabeceras y pies, e imágenes; ver base/editor.py y editor/src/biblioteca.mjs).

- ÁMBITOS de una persona: toda la plataforma («comun»), cada organización en la que está («o<número>») y
  cada grupo en el que está, también los que contienen a los suyos («g<número>»). En los que administra
  lleva «cambiar»: el superadmin, lo común; quien es admin de una organización, lo de su organización. Lo
  demás solo se usa. Va en el pase (contrato: ambitos_del_editor).
- PERSONAS para compartir: el editor no conoce a nadie; al compartir algo con una persona suelta, el
  navegador pregunta aquí, que solo devuelve a quien se puede ver (como en las listas de miembros) y con el
  número que el editor conoce (base.editor.id_para_editor), nunca el de la plataforma.
"""

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from base.editor import id_para_editor

from .acceso import alcance_de, grupos_visibles, ve_miembros
from .models import AdminDeOrganizacion, Contencion, Grupo, Pertenencia

# Cuántas personas se devuelven como mucho al buscar.
MAXIMO_DE_PERSONAS = 10


# Los ámbitos de una persona en la biblioteca del editor: [{id, nombre, cambiar}]. Dos consultas (sus grupos
# con su organización y las organizaciones que administra).
#   - usuario: quien va a entrar en el editor.
def ambitos_para_editor(usuario):
    ambitos = [{"id": "comun", "nombre": "Toda la plataforma", "cambiar": usuario.is_superuser}]
    administradas = set(AdminDeOrganizacion.objects.filter(usuario=usuario).values_list("organizacion_id", flat=True))
    suyos = Contencion.objects.filter(descendiente__pertenencias__usuario=usuario).values("antecesor_id")
    grupos = Grupo.objects.filter(pk__in=suyos).select_related("organizacion").order_by("organizacion__nombre", "nombre")
    organizaciones = {}
    for grupo in grupos:
        organizaciones.setdefault(grupo.organizacion_id, grupo.organizacion.nombre)
    for numero, nombre in organizaciones.items():
        ambitos.append({"id": f"o{numero}", "nombre": nombre, "cambiar": numero in administradas})
    ambitos += [{"id": f"g{grupo.pk}", "nombre": grupo.nombre, "cambiar": False} for grupo in grupos]
    return ambitos


# Busca personas por su alias para compartir algo de la biblioteca con ellas. Devuelve
# {"personas": [{id, nombre}]}: como mucho 10, solo de los grupos cuyos miembros ve quien busca (todas, si
# es superadmin), y con el número del editor. Lo llama la pantalla de la biblioteca («documentos»).
#   - GET «buscar»: al menos dos letras del alias.
@require_GET
def personas_para_editor(request):
    texto = request.GET.get("buscar", "").strip()
    if len(texto) < 2:
        return JsonResponse({"personas": []})
    usuarios = get_user_model().objects.filter(alias__icontains=texto, activo=True).exclude(pk=request.user.pk)
    if not request.user.is_superuser:
        alcance = alcance_de(request.user)
        visibles = [grupo.pk for grupo in grupos_visibles(alcance) if ve_miembros(request.user, grupo, alcance)]
        usuarios = usuarios.filter(pk__in=Pertenencia.objects.filter(grupo_id__in=visibles).values("usuario_id"))
    encontrados = usuarios.order_by("alias")[:MAXIMO_DE_PERSONAS]
    return JsonResponse({"personas": [{"id": id_para_editor(persona), "nombre": persona.alias} for persona in encontrados]})
