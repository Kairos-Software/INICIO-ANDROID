"""
La app Android para descargar.

    /descargar/          -> PÚBLICA: baja la última APK publicada. Es corta a
                            propósito: se escribe con el control remoto en la
                            app "Downloader" de la TV. Sin un código de cliente
                            válido la app no sirve, por eso no pide sesión.
    /app-android/        -> (con sesión) la página del panel: link, instrucciones
                            y, con el permiso publicar_app, subir versiones.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from actividad.models import Accion
from actividad.registro import registrar
from usuarios.permisos import chequear_permiso

from .forms import VersionAppForm
from .models import VersionApp

TIPO_APK = 'application/vnd.android.package-archive'


def descargar(request, pk=None):
    if pk:
        # Una versión puntual: las ocultas solo para quien publica
        versiones = VersionApp.objects.all()
        if not chequear_permiso(request.user, 'publicar_app'):
            versiones = versiones.filter(publicada=True)
        version = get_object_or_404(versiones, pk=pk)
    else:
        version = VersionApp.ultima()
    if version is None or not version.archivo:
        raise Http404('Todavía no hay una versión de la app para descargar.')
    try:
        archivo = version.archivo.open('rb')
    except FileNotFoundError:
        raise Http404('No se encontró el archivo de la app.')
    return FileResponse(archivo, as_attachment=True, filename=version.nombre_descarga, content_type=TIPO_APK)


@login_required
def pagina(request):
    puede_publicar = chequear_permiso(request.user, 'publicar_app')
    form = VersionAppForm()
    if request.method == 'POST':
        if not puede_publicar:
            raise PermissionDenied
        form = VersionAppForm(request.POST, request.FILES)
        if form.is_valid():
            version = form.save(commit=False)
            version.subida_por = request.user
            version.save()
            registrar(request.user, Accion.CREAR, f'Publicó la versión {version.version} de la app', objeto=version,
                      modulo='descargas')
            messages.success(request, f'Versión {version.version} publicada: desde ahora es la que se descarga.')
            return redirect('descargas:pagina')

    return render(request, 'descargas/pagina.html', {
        'ultima': VersionApp.ultima(),
        'versiones': VersionApp.objects.all()[:20] if puede_publicar else None,
        'form': form,
        'puede_publicar': puede_publicar,
        'link': request.build_absolute_uri('/descargar/'),
    })


@require_POST
@login_required
def cambiar_publicada(request, pk):
    if not chequear_permiso(request.user, 'publicar_app'):
        raise PermissionDenied
    version = get_object_or_404(VersionApp, pk=pk)
    version.publicada = not version.publicada
    version.save(update_fields=['publicada'])
    registrar(request.user, Accion.EDITAR,
              f'{"Publicó" if version.publicada else "Despublicó"} la versión {version.version} de la app',
              objeto=version, modulo='descargas')
    messages.success(request, f'Versión {version.version} {"publicada" if version.publicada else "despublicada"}.')
    return redirect('descargas:pagina')
