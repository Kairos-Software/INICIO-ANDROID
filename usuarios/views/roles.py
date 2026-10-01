"""
Pantallas de roles (paquetes de permisos): lista, alta, edición y baja.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .. import consultas, servicios
from ..decoradores import requiere_permiso
from ..forms import RolForm
from ..models import Rol
from ..permisos import chequear_permiso, grilla_permisos_rol


@requiere_permiso('ver_roles')
def lista(request):
    return render(request, 'usuarios/roles/lista.html', {
        'roles': consultas.roles_con_uso(),
    })


@requiere_permiso('crear_roles')
def crear(request):
    return _formulario(request, rol=None)


@requiere_permiso('ver_roles')
def editar(request, pk):
    # Con 'ver_roles' se puede ver; para guardar hace falta 'editar_roles'
    return _formulario(request, rol=get_object_or_404(Rol, pk=pk))


def _formulario(request, rol):
    creando = rol is None
    puede_guardar = creando or chequear_permiso(request.user, 'editar_roles')
    form = RolForm(request.POST or None, instance=rol)
    actuales = rol.get_permisos() if rol else set()
    if request.method == 'POST':
        marcados = set(request.POST.getlist('permisos'))
        # Los checkboxes bloqueados no se envían: para volver a mostrar la
        # pantalla (si hubo un error) se combinan igual que al guardar.
        a_mostrar = servicios.combinar_permisos(actuales, marcados, request.user)
    else:
        marcados = a_mostrar = actuales

    if request.method == 'POST':
        if not puede_guardar:
            messages.error(request, 'No tenés permiso para modificar roles.')
            return redirect('usuarios:roles_editar', pk=rol.pk)
        if form.is_valid():
            rol = servicios.guardar_rol(form, marcados, request.user)
            messages.success(request, f'Rol "{rol}" {"creado" if creando else "guardado"}.')
            return redirect('usuarios:roles_lista')

    return render(request, 'usuarios/roles/formulario.html', {
        'form': form,
        'rol': rol,
        'creando': creando,
        'puede_guardar': puede_guardar,
        'puede_eliminar': rol is not None and chequear_permiso(request.user, 'eliminar_roles'),
        'grilla': grilla_permisos_rol(a_mostrar, request.user),
        'cantidad_usuarios': rol.usuarios.count() if rol else 0,
    })


@requiere_permiso('eliminar_roles')
def eliminar(request, pk):
    rol = get_object_or_404(Rol, pk=pk)
    if request.method == 'POST':
        nombre = str(rol)
        cantidad = servicios.eliminar_rol(rol, request.user)
        detalle = f' {cantidad} usuario(s) pasaron a permisos personalizados.' if cantidad else ''
        messages.success(request, f'Rol "{nombre}" eliminado.{detalle}')
        return redirect('usuarios:roles_lista')

    return render(request, 'usuarios/roles/eliminar.html', {
        'rol': rol,
        'usuarios': rol.usuarios.order_by('first_name', 'username')[:10],
        'cantidad_usuarios': rol.usuarios.count(),
    })
