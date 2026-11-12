"""
Pantallas del módulo «usuarios»: entrar, salir, preferencias y contraseña.
"""

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_POST

from base.preferencias import PREFERENCIAS, es_valida

from .formularios import FormularioDeEntrada
from .models import Usuario


class Entrar(LoginView):
    """
    Pantalla de entrada: alias y contraseña. Es la única que se ve sin sesión (la vista de Django ya
    viene marcada así). Quien ya ha iniciado sesión pasa directamente a la aplicación.
    """

    template_name = "usuarios/entrar.html"
    authentication_form = FormularioDeEntrada
    redirect_authenticated_user = True


# Pantalla «Mi cuenta → Preferencias»: botones para elegir el tema, la letra y la densidad. Al pulsarlos,
# el navegador aplica el cambio al momento y lo guarda con guardar_preferencia (ver interfaz.js).
def preferencias(request):
    return render(request, "usuarios/preferencias.html", {"preferencias": PREFERENCIAS})


# Guarda una preferencia en la cuenta de quien ha iniciado sesión. La llama el almacén «preferencias» de
# base/static/base/interfaz.js cada vez que se cambia el tema, la letra o la densidad. Responde sin
# contenido (código 204), porque el navegador ya ha aplicado el cambio. Cuesta una sola consulta.
#   - POST «clave»: «tema», «letra» o «densidad».
#   - POST «valor»: la opción elegida.
@require_POST
def guardar_preferencia(request):
    clave = request.POST.get("clave", "")
    valor = request.POST.get("valor", "")
    if not es_valida(clave, valor):
        return HttpResponseBadRequest("Preferencia no válida.")
    Usuario.objects.filter(pk=request.user.pk).update(**{clave: valor})
    return HttpResponse(status=204)


# Pantalla «Mi cuenta → Contraseña»: cambia la contraseña pidiendo la actual. Al cambiarla no se cierra
# la sesión (update_session_auth_hash) y se muestra un aviso en la misma pantalla.
def contrasena(request):
    formulario = PasswordChangeForm(request.user, request.POST or None)
    cambiada = False
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        update_session_auth_hash(request, formulario.user)
        cambiada = True
        formulario = PasswordChangeForm(request.user)
    return render(request, "usuarios/contrasena.html", {"formulario": formulario, "cambiada": cambiada})
