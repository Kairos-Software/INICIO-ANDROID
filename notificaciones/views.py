"""Las notificaciones propias: cada usuario ve solo las suyas (no requiere permisos)."""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import servicios


@login_required
def lista(request):
    solo_no_leidas = request.GET.get('ver') == 'no_leidas'
    qs = request.user.notificaciones.all()
    if solo_no_leidas:
        qs = qs.filter(leida_en__isnull=True)
    pagina = Paginator(qs, 30).get_page(request.GET.get('pagina'))
    return render(request, 'notificaciones/lista.html', {
        'pagina': pagina,
        'solo_no_leidas': solo_no_leidas,
        'parametros': 'ver=no_leidas' if solo_no_leidas else '',
    })


@login_required
def abrir(request, pk):
    """La marca como leída y lleva a donde apunta (o a la lista si no apunta a nada)."""
    notificacion = get_object_or_404(request.user.notificaciones, pk=pk)
    servicios.marcar_leida(notificacion)
    if notificacion.url and url_has_allowed_host_and_scheme(notificacion.url, allowed_hosts={request.get_host()}):
        return redirect(notificacion.url)
    return redirect('notificaciones:lista')


@require_POST
@login_required
def marcar_todas(request):
    servicios.marcar_todas_leidas(request.user)
    destino = request.POST.get('volver', '')
    if destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        return redirect(destino)
    return redirect('notificaciones:lista')
