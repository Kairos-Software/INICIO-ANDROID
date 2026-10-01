"""
Recuperar la contraseña con un código enviado por mail (sin sesión).

  Paso 1  solicitar       -> escribe su usuario o email; se manda el código
  Paso 2  verificar       -> escribe el código de 6 dígitos
  Paso 3  nueva_password  -> elige la contraseña nueva

El avance entre pasos se guarda en la sesión (clave SESION). Nunca se le
muestra a quien pide si la cuenta existe o no.
"""

import time

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render

from .. import servicios
from ..forms import CodigoRecuperacionForm, NuevaPasswordForm, SolicitarRecuperacionForm, ip_cliente
from ..models import INTENTOS_MAXIMOS_CODIGO_RECUPERACION

SESION = 'recuperacion'
MINUTOS_PARA_ELEGIR_PASSWORD = 10


def _datos(request):
    return request.session.get(SESION) or {}


def _guardar(request, **datos):
    request.session[SESION] = {**_datos(request), **datos}


def solicitar(request):
    form = SolicitarRecuperacionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        identificador = form.cleaned_data['identificador']
        try:
            usuario = servicios.solicitar_codigo_recuperacion(identificador)
        except servicios.OperacionNoPermitida as error:
            form.add_error(None, str(error))
        else:
            request.session[SESION] = {
                'identificador': identificador,
                'usuario_id': usuario.pk if usuario else None,
                'intentos': 0,
            }
            return redirect('usuarios:recuperar_codigo')

    return render(request, 'usuarios/recuperar/solicitar.html', {'form': form})


def verificar(request):
    datos = _datos(request)
    if 'identificador' not in datos:
        return redirect('usuarios:recuperar')

    form = CodigoRecuperacionForm(request.POST or None)

    if request.method == 'POST' and request.POST.get('accion') == 'reenviar':
        try:
            usuario = servicios.solicitar_codigo_recuperacion(datos['identificador'])
        except servicios.OperacionNoPermitida as error:
            messages.error(request, str(error))
        else:
            _guardar(request, usuario_id=usuario.pk if usuario else None, intentos=0)
            messages.info(request, 'Si los datos son correctos, te mandamos un código nuevo.')
        return redirect('usuarios:recuperar_codigo')

    if request.method == 'POST' and form.is_valid():
        if servicios.verificar_codigo_recuperacion(datos.get('usuario_id'), form.cleaned_data['codigo']):
            request.session[SESION] = {'verificado_id': datos['usuario_id'], 'verificado_en': time.time()}
            return redirect('usuarios:recuperar_nueva')

        # También se cuentan los intentos en la sesión, para cuando la cuenta
        # no existe (y así se comporta igual que cuando existe)
        intentos = datos.get('intentos', 0) + 1
        if intentos >= INTENTOS_MAXIMOS_CODIGO_RECUPERACION:
            request.session.pop(SESION, None)
            messages.error(request, 'Demasiados intentos con un código incorrecto. Pedí un código nuevo.')
            return redirect('usuarios:recuperar')
        _guardar(request, intentos=intentos)
        form.add_error('codigo', 'El código es incorrecto o ya venció.')

    return render(request, 'usuarios/recuperar/codigo.html', {'form': form})


def nueva_password(request):
    datos = _datos(request)
    vencido = time.time() - datos.get('verificado_en', 0) > MINUTOS_PARA_ELEGIR_PASSWORD * 60
    usuario = get_user_model().objects.filter(pk=datos.get('verificado_id'), is_active=True).first()
    if usuario is None or vencido:
        request.session.pop(SESION, None)
        if datos.get('verificado_id'):
            messages.error(request, 'Pasó demasiado tiempo. Pedí un código nuevo.')
        return redirect('usuarios:recuperar')

    form = NuevaPasswordForm(usuario, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        servicios.establecer_password_recuperada(usuario, form.cleaned_data['new_password1'], ip_cliente(request))
        request.session.pop(SESION, None)
        messages.success(request, 'Listo, tu contraseña se cambió. Ya podés ingresar con la nueva.')
        return redirect('usuarios:login')

    return render(request, 'usuarios/recuperar/nueva.html', {'form': form, 'usuario': usuario})
