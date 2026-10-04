"""
"Mi perfil" desde la app. No requiere permisos: cada uno maneja lo suyo.

    GET   /api/v1/perfil/                   -> mis datos y mis permisos
    PATCH /api/v1/perfil/                   -> modificar mis datos (solo lo que cambia)
    GET   /api/v1/perfil/opciones/          -> opciones para el formulario (ej: géneros)
    POST  /api/v1/perfil/cambiar-password/  {"old_password", "new_password1", "new_password2"}
"""

from django.contrib.auth import get_user_model, update_session_auth_hash
from rest_framework.decorators import api_view
from rest_framework.response import Response

from usuarios import servicios
from usuarios.forms import CambiarPasswordForm, PerfilForm
from usuarios.models import Usuario

from .. import tokens
from ..errores import validar_formulario
from ..formularios import datos_para_edicion, datos_planos
from ..models import TokenAcceso
from .serializers import PerfilSerializer


@api_view(['GET', 'PATCH'])
def perfil(request):
    usuario = request.user
    if request.method == 'PATCH':
        usuario = get_user_model().objects.get(pk=usuario.pk)   # copia fresca, como en la web
        form = PerfilForm(datos_para_edicion(usuario, PerfilForm, request.data), request.FILES, instance=usuario)
        validar_formulario(form)
        usuario = servicios.actualizar_perfil(form)
    return Response(PerfilSerializer(usuario, context={'request': request}).data)


@api_view(['GET'])
def opciones(request):
    """Las opciones de los campos de elegir que tiene el perfil."""
    return Response({'genero': [{'valor': valor, 'texto': texto} for valor, texto in Usuario.Genero.choices]})


@api_view(['POST'])
def cambiar_password(request):
    form = CambiarPasswordForm(request.user, datos_planos(request.data))
    validar_formulario(form)
    servicios.cambiar_password_propia(request.user, form.cleaned_data['new_password1'])

    # Como en la web: la sesión actual sigue abierta; las de otros dispositivos se cierran
    if isinstance(request.auth, TokenAcceso):
        tokens.mantener_tras_cambio_de_password(request.auth)
    else:
        update_session_auth_hash(request._request, request.user)
    return Response({'detalle': 'Tu contraseña se cambió.'})
