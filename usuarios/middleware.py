"""
Capa que impide ver nada sin iniciar sesión (premisa 13: nada es público por defecto).

Se basa en LoginRequiredMiddleware de Django: toda vista exige sesión, salvo las marcadas con
@login_not_required (la pantalla de entrada ya lo está). Lo público (fase 8) se marcará así a propósito.
Está en config/settings.py, en MIDDLEWARE.
"""

from django.contrib.auth.middleware import LoginRequiredMiddleware
from django.http import HttpResponse


class EntradaObligatoria(LoginRequiredMiddleware):
    """
    Manda a la pantalla de entrada a quien no ha iniciado sesión. Añade dos cosas a la de Django:
    entiende las peticiones de htmx y deja pasar la barra de depuración.
    """

    # Django la llama antes de cada vista. Deja pasar sin mirar la sesión:
    #   - las vistas marcadas con @login_not_required. La de Django carga antes el usuario (una consulta)
    #     aunque la vista no lo necesite; aquí se mira primero la marca y se ahorra esa consulta;
    #   - las direcciones internas de la barra de depuración (solo existen en desarrollo), que el
    #     navegador pide por su cuenta para pintar la barra.
    def process_view(self, request, view_func, view_args, view_kwargs):
        if not getattr(view_func, "login_required", True) or request.path.startswith("/__debug__/"):
            return None
        return super().process_view(request, view_func, view_args, view_kwargs)

    # Respuesta para quien no ha iniciado sesión. Normalmente, una redirección a la entrada. Pero si la
    # petición viene de htmx (por ejemplo, al navegar con la sesión ya caducada), htmx metería la
    # pantalla de entrada dentro de la zona central; con la cabecera HX-Redirect, htmx carga la
    # pantalla de entrada como página entera.
    def handle_no_permission(self, request, view_func):
        redireccion = super().handle_no_permission(request, view_func)
        if request.headers.get("HX-Request") != "true":
            return redireccion
        respuesta = HttpResponse(status=200)
        respuesta["HX-Redirect"] = redireccion.url
        return respuesta
