"""Iniciar y cerrar sesión."""

from django.contrib import messages
from django.contrib.auth import views as auth_views

from core.mantenimiento import estado_actual

from ..forms import LoginForm


class LoginView(auth_views.LoginView):
    template_name = 'usuarios/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        # En mantenimiento solo entran los superusuarios: al resto se le avisa
        # acá, en vez de dejarlo entrar y mostrarle la pantalla de mantenimiento
        if not form.get_user().is_superuser and estado_actual()['activo']:
            form.add_error(None, 'El sistema está en mantenimiento. Por ahora solo pueden ingresar '
                                 'los administradores.')
            return self.form_invalid(form)

        # Django pisa last_login al entrar: guardamos el anterior para mostrarlo
        anterior = form.get_user().last_login
        respuesta = super().form_valid(form)
        self.request.session['ingreso_anterior'] = anterior.isoformat() if anterior else None
        if not form.cleaned_data.get('recordarme'):
            # Sin "mantener sesión": se cierra al cerrar el navegador
            self.request.session.set_expiry(0)
        return respuesta


class LogoutView(auth_views.LogoutView):
    # Django solo permite cerrar sesión por POST (evita que un link externo
    # te desloguee). El botón del menú es un pequeño formulario.

    def post(self, request, *args, **kwargs):
        respuesta = super().post(request, *args, **kwargs)
        messages.info(request, 'Cerraste sesión.')
        return respuesta
