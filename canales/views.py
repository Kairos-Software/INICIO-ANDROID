"""
Pantalla de canales del panel: resumen, importar una lista M3U y volver a
verificar todas las fuentes. Editar un canal puntual sigue en /admin/.
"""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from usuarios.decoradores import requiere_permiso
from usuarios.permisos import chequear_permiso

from . import consultas, servicios
from .forms import ImportarListaForm
from .verificacion import verificar_varias


@requiere_permiso('ver_canales')
def inicio(request):
    form = ImportarListaForm()
    resultado = None
    if request.method == 'POST':
        if not chequear_permiso(request.user, 'importar_canales'):
            raise PermissionDenied
        form = ImportarListaForm(request.POST, request.FILES)
        if form.is_valid():
            # Se muestra el resultado en la misma respuesta (con el detalle de
            # las caídas), sin redirigir: no hay nada que guardar para después.
            resultado = servicios.importar_m3u(
                form.texto, origen=form.cleaned_data['archivo'].name,
                usuario=request.user, verificar=verificar_varias,
            )
            messages.success(request, f'Lista importada: {resultado}')
            form = ImportarListaForm()

    return render(request, 'canales/inicio.html', {
        'form': form,
        'resultado': resultado,
        'resumen': consultas.resumen(),
        'caidas': consultas.fuentes_caidas(),
        'puede_importar': chequear_permiso(request.user, 'importar_canales'),
    })


@require_POST
@requiere_permiso('importar_canales')
def verificar(request):
    resultado = servicios.verificar_fuentes_guardadas(verificar_varias, usuario=request.user)
    messages.success(request, f'Verificación terminada. {resultado}')
    return redirect('canales:inicio')
