"""
Iniciar y cerrar sesión desde la app.

    POST /api/v1/login/   {"username": "...", "password": "...", "dispositivo": "Samsung A54"}
      -> 200 {"token": "...", "tipo": "Bearer", "vence": "...", "usuario": {...perfil...}}

    POST /api/v1/logout/  (con el token) -> 204, el token deja de servir

El login usa el mismo LoginForm de la web: mismo bloqueo por intentos
fallidos, mismo registro de actividad, mismo "usuario o email".
"""

from django.contrib.auth.signals import user_logged_in, user_logged_out
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.mantenimiento import estado_actual
from usuarios.forms import LoginForm

from .. import tokens
from ..autenticacion import TokenBearer
from ..errores import ErrorApi, validar_formulario
from ..formularios import datos_planos
from ..permisos import error_mantenimiento
from .serializers import PerfilSerializer

# Códigos de error del LoginForm -> los de la API
CODIGOS_LOGIN = {'invalid_login': 'credenciales_invalidas', 'inactive': 'cuenta_inactiva',
                 'bloqueado': 'login_bloqueado'}


@api_view(['POST'])
@authentication_classes([])       # no hace falta (ni se mira) un token para iniciar sesión
@permission_classes([AllowAny])
def login(request):
    datos = datos_planos(request.data)
    form = LoginForm(request._request, data={'username': datos.get('username', ''),
                                             'password': datos.get('password', '')})
    if not form.is_valid():
        if 'username' in form.errors or 'password' in form.errors:
            validar_formulario(form)   # faltó el usuario o la contraseña: errores por campo
        error = form.non_field_errors().as_data()[0]
        raise ErrorApi(error.messages[0], CODIGOS_LOGIN.get(error.code, 'credenciales_invalidas'))

    usuario = form.get_user()
    estado = estado_actual()
    if estado['activo'] and not usuario.is_superuser:
        raise error_mantenimiento(estado)

    clave, token = tokens.crear_token(usuario, datos.get('dispositivo', ''))
    # Lo mismo que hace Django al entrar por la web: actualiza el último
    # ingreso y queda en el registro de actividad
    user_logged_in.send(sender=usuario.__class__, request=request._request, user=usuario)
    return Response({
        'token': clave,
        'tipo': TokenBearer.palabra_clave,
        'vence': tokens.vencimiento(token),
        'usuario': PerfilSerializer(usuario, context={'request': request}).data,
    })


@api_view(['POST'])
@authentication_classes([TokenBearer])
@permission_classes([IsAuthenticated])   # cerrar sesión se puede siempre (aun en mantenimiento)
def logout(request):
    tokens.revocar(request.auth)
    user_logged_out.send(sender=request.user.__class__, request=request._request, user=request.user)
    return Response(status=status.HTTP_204_NO_CONTENT)
