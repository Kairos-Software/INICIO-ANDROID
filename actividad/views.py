from django.core.paginator import Paginator
from django.shortcuts import render

from usuarios.decoradores import requiere_permiso

from . import consultas
from .models import Accion

REGISTROS_POR_PAGINA = 50


@requiere_permiso('ver_actividad')
def lista(request):
    filtros = {
        'texto': request.GET.get('q', '').strip(),
        'accion': request.GET.get('accion', ''),
        'modulo': request.GET.get('modulo', ''),
        'desde': request.GET.get('desde', ''),
        'hasta': request.GET.get('hasta', ''),
        'usuario_id': request.GET.get('usuario', '') if request.GET.get('usuario', '').isdigit() else '',
    }
    registros = consultas.buscar_actividad(**filtros)
    pagina = Paginator(registros, REGISTROS_POR_PAGINA).get_page(request.GET.get('pagina'))

    parametros = request.GET.copy()
    parametros.pop('pagina', None)

    return render(request, 'actividad/lista.html', {
        'pagina': pagina,
        'filtros': filtros,
        'hay_filtros': any(filtros.values()),
        'acciones': Accion.choices,
        'modulos': consultas.modulos_registrados(),
        'parametros': parametros.urlencode(),
    })
