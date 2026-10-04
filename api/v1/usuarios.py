"""
Gestión de usuarios desde la app. Mismos permisos y mismas reglas que la web.

    GET    /api/v1/usuarios/                       ver_usuarios      ?q=&rol=&estado=activos|inactivos&pagina=
    POST   /api/v1/usuarios/                       crear_usuarios
    GET    /api/v1/usuarios/opciones/              crear o editar    roles y opciones para los formularios
    GET    /api/v1/usuarios/<id>/                  ver_usuarios
    PATCH  /api/v1/usuarios/<id>/                  editar_usuarios   (solo lo que cambia)
    DELETE /api/v1/usuarios/<id>/                  eliminar_usuarios
    POST   /api/v1/usuarios/<id>/estado/           editar_usuarios   {"activo": true|false}
    POST   /api/v1/usuarios/<id>/restablecer-password/  restablecer_password_usuarios

Igual que en la web, nunca aparecen los superusuarios ni uno mismo.
"""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from usuarios import consultas, servicios
from usuarios.forms import RestablecerPasswordForm, UsuarioCrearForm, UsuarioForm
from usuarios.models import Usuario
from usuarios.permisos import puede_otorgar_rol

from ..errores import DatosInvalidos, validar_formulario
from ..formularios import datos_para_edicion, datos_planos
from ..paginacion import paginar
from ..permisos import exigir_permiso
from .serializers import UsuarioDetalleSerializer, UsuarioListaSerializer


def _obtener(request, pk):
    # Siempre desde usuarios_gestionables (ver usuarios/consultas.py)
    return get_object_or_404(consultas.usuarios_gestionables(request.user), pk=pk)


def _detalle(request, usuario, codigo=status.HTTP_200_OK):
    return Response(UsuarioDetalleSerializer(usuario, context={'request': request}).data, status=codigo)


@api_view(['GET', 'POST'])
def lista(request):
    if request.method == 'POST':
        return _crear(request)

    exigir_permiso(request.user, 'ver_usuarios')
    rol = request.query_params.get('rol', '')
    if rol not in ('', 'sin_rol') and not rol.isdigit():
        raise DatosInvalidos({'rol': ['Tiene que ser el id de un rol o "sin_rol".']})
    usuarios = consultas.buscar_usuarios(
        request.user,
        texto=request.query_params.get('q', '').strip(),
        rol=rol,
        estado=request.query_params.get('estado', ''),
    )
    return paginar(request, usuarios, UsuarioListaSerializer)


def _crear(request):
    exigir_permiso(request.user, 'crear_usuarios')
    datos = datos_planos(request.data)
    datos.setdefault('debe_cambiar_password', True)   # en la web viene tildado
    form = UsuarioCrearForm(datos, request.FILES)
    validar_formulario(form)
    try:
        usuario = servicios.crear_usuario(form, request.user)
    except servicios.OperacionNoPermitida as error:
        raise DatosInvalidos({'rol': [str(error)]})
    return _detalle(request, usuario, status.HTTP_201_CREATED)


@api_view(['GET'])
def opciones(request):
    """Lo que la app necesita para armar los formularios de alta y edición."""
    exigir_permiso(request.user, 'crear_usuarios', 'editar_usuarios')

    def lista_opciones(choices):
        return [{'valor': valor, 'texto': texto} for valor, texto in choices]

    return Response({
        'roles': [
            {'id': rol.pk, 'nombre': rol.nombre, 'descripcion': rol.descripcion,
             'puede_asignar': puede_otorgar_rol(rol, request.user)}
            for rol in consultas.roles_para_filtro()
        ],
        'tipo_documento': lista_opciones(Usuario.TipoDocumento.choices),
        'genero': lista_opciones(Usuario.Genero.choices),
    })


@api_view(['GET', 'PATCH', 'DELETE'])
def detalle(request, pk):
    # El permiso se chequea ANTES de buscar: sin permiso, ni siquiera se
    # sabe si el usuario existe
    if request.method == 'GET':
        exigir_permiso(request.user, 'ver_usuarios')
        return _detalle(request, _obtener(request, pk))

    if request.method == 'PATCH':
        exigir_permiso(request.user, 'editar_usuarios')
        usuario = _obtener(request, pk)
        form = UsuarioForm(datos_para_edicion(usuario, UsuarioForm, request.data), request.FILES, instance=usuario)
        validar_formulario(form)
        try:
            usuario = servicios.actualizar_usuario(form, request.user)
        except servicios.OperacionNoPermitida as error:
            raise DatosInvalidos({'rol': [str(error)]})
        return _detalle(request, usuario)

    exigir_permiso(request.user, 'eliminar_usuarios')
    servicios.eliminar_usuario(_obtener(request, pk), request.user)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def cambiar_estado(request, pk):
    exigir_permiso(request.user, 'editar_usuarios')
    usuario = _obtener(request, pk)
    activo = datos_planos(request.data).get('activo')
    if not isinstance(activo, bool):
        raise DatosInvalidos({'activo': ['Tiene que ser true o false.']})
    servicios.cambiar_estado(usuario, activo, request.user)
    return _detalle(request, usuario)


@api_view(['POST'])
def restablecer_password(request, pk):
    exigir_permiso(request.user, 'restablecer_password_usuarios')
    usuario = _obtener(request, pk)
    datos = datos_planos(request.data)
    datos.setdefault('obligar_cambio', True)   # en la web viene tildado
    form = RestablecerPasswordForm(usuario, datos)
    validar_formulario(form)
    servicios.restablecer_password(usuario, form.cleaned_data['password1'], form.cleaned_data['obligar_cambio'],
                                   request.user)
    return Response({'detalle': f'Se asignó una contraseña nueva a {usuario.get_full_name()}.'})
