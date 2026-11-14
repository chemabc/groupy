"""
Pantallas del módulo «usuarios»: entrar, salir, preferencias, mis datos y contraseña.
"""

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from base.preferencias import PREFERENCIAS, es_valida

from .formularios import FormularioDeCorreo, FormularioDeEntrada
from .models import Usuario


class Entrar(LoginView):
    """
    Pantalla de entrada: alias y contraseña. Es la única que se ve sin sesión (la vista de Django ya
    viene marcada así). Quien ya ha iniciado sesión pasa directamente a la aplicación.
    """

    template_name = "usuarios/entrar.html"
    authentication_form = FormularioDeEntrada
    redirect_authenticated_user = True


# Pantalla «Configuración de mi cuenta → Usabilidad»: botones para elegir el tema, la letra y la densidad. Al pulsarlos,
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


# Pantalla «Configuración de mi cuenta → Contraseña»: cambia la contraseña pidiendo la actual. Al cambiarla no se cierra
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


# Pantalla «Configuración de mi cuenta → Mis datos → Datos»: cada dato de la cuenta, con quién lo ve y, si
# se puede, el formulario para cambiarlo (de momento, solo el correo alternativo; el alias lo cambia la
# administración). Es la que abre el botón «Editar» de «Inicio → Mis datos». Cuesta 1 consulta al guardar
# y ninguna al mirar.
#   - POST «correo_alternativo»: el correo nuevo (o vacío, para quitarlo).
def datos(request):
    usuario = request.user
    formulario = FormularioDeCorreo(request.POST or None, instance=usuario)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        return redirect(f"{request.path}?guardado=1")
    filas = [
        {"dato": "Alias", "valor": usuario.alias, "quien": "Las personas de tus grupos y quien administra tus grupos.", "cambiar": "Lo cambia la administración: pídelo en «Comunicaciones → Conversaciones → Con la administración»."},
        {"dato": "En la plataforma desde", "valor": f"{usuario.activado_el:%d/%m/%Y}", "quien": "Las personas de tus grupos.", "cambiar": "No se cambia."},
        {"dato": "Cómo se creó la cuenta", "valor": usuario.get_origen_display(), "quien": "Tú y el superadmin.", "cambiar": "No se cambia."},
        {"dato": "Correo alternativo", "valor": usuario.correo_alternativo or "—", "quien": "Tú y el superadmin (para ayudarte a recuperar la cuenta).", "cambiar": "Aquí abajo."},
    ]
    return render(request, "usuarios/datos.html", {"filas": filas, "formulario": formulario, "guardado": "guardado" in request.GET})
