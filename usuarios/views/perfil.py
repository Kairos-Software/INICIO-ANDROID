"""
"Mi perfil": cada usuario ve y edita sus propios datos y cambia su contraseña.
No requiere permisos: cualquier usuario con sesión tiene acceso a lo suyo.
"""

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .. import servicios
from ..catalogo_permisos import MODULOS_PERMISOS
from ..forms import (
    SECCIONES_PERFIL, SECCIONES_PERFIL_SOLO_LECTURA, CambiarPasswordForm, PerfilForm,
    datos_usuario,
)
from ..permisos import permisos_efectivos


@login_required
def ver(request):
    usuario = request.user
    propios = permisos_efectivos(usuario)
    # Solo los módulos donde tiene algún permiso, con la descripción de cada uno
    mis_permisos = [
        (modulo, [descripcion for codigo, descripcion in permisos if codigo in propios])
        for modulo, permisos in MODULOS_PERMISOS
    ]
    return render(request, 'usuarios/perfil/ver.html', {
        'secciones': datos_usuario(usuario, SECCIONES_PERFIL),
        'secciones_cuenta': datos_usuario(usuario, SECCIONES_PERFIL_SOLO_LECTURA),
        'mis_permisos': [(m, lista) for m, lista in mis_permisos if lista],
    })


@login_required
def editar(request):
    # Copia fresca: si el formulario vuelve con errores, el menú (que usa
    # request.user) no muestra datos a medio guardar
    usuario = get_user_model().objects.get(pk=request.user.pk)
    form = PerfilForm(request.POST or None, request.FILES or None, instance=usuario)
    if request.method == 'POST' and form.is_valid():
        servicios.actualizar_perfil(form)
        messages.success(request, 'Tus datos se guardaron.')
        return redirect('usuarios:perfil')
    return render(request, 'usuarios/perfil/editar.html', {'form': form})


@login_required
def cambiar_password(request):
    obligatorio = request.user.debe_cambiar_password
    form = CambiarPasswordForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        servicios.cambiar_password_propia(request.user, form.cleaned_data['new_password1'])
        # Mantiene esta sesión abierta (las de otros dispositivos se cierran)
        update_session_auth_hash(request, request.user)
        messages.success(request, 'Tu contraseña se cambió.')
        return redirect('core:inicio' if obligatorio else 'usuarios:perfil')

    return render(request, 'usuarios/perfil/cambiar_password.html', {
        'form': form,
        'obligatorio': obligatorio,
    })
