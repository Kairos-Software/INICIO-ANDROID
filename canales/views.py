"""
Pantallas de canales del panel:

  /canales/                         resumen, subir una lista, verificar todas (de a tandas) e importaciones anteriores
  /canales/importaciones/<id>/      el avance y el detalle de una lista: qué se agregó, qué no y por qué
  /canales/catalogo/                todos los canales como los ve la app, con filtros para quitar los que no sirven
  /canales/canal/<id>/editar/       nombre, logo, categoría... de un canal, y sus fuentes

Lo que tarda (verificar) se hace de a tandas: la página llama una y otra
vez a las direcciones ".../lote/" (responden JSON) y va mostrando el avance.
"""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from usuarios.decoradores import requiere_permiso
from usuarios.permisos import chequear_permiso

from . import consultas, servicios
from .forms import CanalForm, FuentesFormSet, ImportarListaForm, QuitarCanalesForm
from .models import Canal, Contenido, EntradaImportada, Idioma, Importacion
from .verificacion import verificar_url, verificar_varias

CANALES_POR_PAGINA = 120
ENTRADAS_POR_PAGINA = 100


def _parametros_sin_pagina(request):
    parametros = request.GET.copy()
    parametros.pop('pagina', None)
    return parametros.urlencode()


@requiere_permiso('ver_canales')
def inicio(request):
    form = ImportarListaForm()
    if request.method == 'POST':
        if not chequear_permiso(request.user, 'importar_canales'):
            raise PermissionDenied
        form = ImportarListaForm(request.POST, request.FILES)
        if form.is_valid():
            # Solo analiza (segundos). La verificación la va pidiendo la
            # pantalla de la importación, de a tandas.
            importacion = servicios.crear_importacion(
                form.texto, form.cleaned_data['archivo'].name, request.user, **form.opciones())
            return redirect(f'{importacion_url(importacion)}?empezar=1')

    return render(request, 'canales/inicio.html', {
        'form': form,
        'resumen': consultas.resumen(),
        'importaciones': consultas.ultimas_importaciones(),
        'puede_importar': chequear_permiso(request.user, 'importar_canales'),
    })


def importacion_url(importacion):
    return reverse('canales:importacion', args=[importacion.pk])


# ── Una importación ──────────────────────────────────────────────────

@requiere_permiso('ver_canales')
def importacion(request, pk):
    importacion = get_object_or_404(Importacion.objects.select_related('usuario'), pk=pk)
    filtros = {
        'texto': request.GET.get('q', '').strip(),
        'estado': request.GET.get('estado', ''),
        'idioma': request.GET.get('idioma', ''),
        'contenido': request.GET.get('contenido', ''),
    }
    entradas = importacion.entradas.select_related('canal')
    if filtros['texto']:
        entradas = entradas.filter(Q(nombre__icontains=filtros['texto']) | Q(nombre_original__icontains=filtros['texto'])
                                   | Q(categoria__icontains=filtros['texto']))
    if filtros['estado'] in EntradaImportada.Estado.values:
        entradas = entradas.filter(estado=filtros['estado'])
    if filtros['idioma'] == 'sin_dato':
        entradas = entradas.filter(idioma='')
    elif filtros['idioma'] in ('es', 'otro'):
        entradas = entradas.filter(idioma=filtros['idioma'])
    if filtros['contenido'] in EntradaImportada.Contenido.values:
        entradas = entradas.filter(contenido=filtros['contenido'])

    return render(request, 'canales/importacion.html', {
        'importacion': importacion,
        'avance': servicios.progreso(importacion),
        'pagina': Paginator(entradas, ENTRADAS_POR_PAGINA).get_page(request.GET.get('pagina')),
        'filtros': filtros,
        'hay_filtros': any(filtros.values()),
        'parametros': _parametros_sin_pagina(request),
        'estados': EntradaImportada.Estado.choices,
        'contenidos': EntradaImportada.Contenido.choices,
        'puede_importar': chequear_permiso(request.user, 'importar_canales'),
        'empezar': request.GET.get('empezar') == '1',
        'tamanio_lote': servicios.TAMANIO_LOTE,
    })


@require_POST
@requiere_permiso('importar_canales')
def importacion_lote(request, pk):
    """Verifica la próxima tanda y responde el avance (JSON). La pantalla la llama en bucle."""
    importacion = get_object_or_404(Importacion, pk=pk)
    return JsonResponse(servicios.procesar_lote(importacion, verificar_varias))


@require_POST
@requiere_permiso('importar_canales')
def importacion_reintentar(request, pk):
    importacion = get_object_or_404(Importacion, pk=pk)
    cantidad = servicios.reintentar_caidas(importacion, request.user)
    if not cantidad:
        messages.info(request, 'No hay canales que no hayan funcionado para reintentar.')
        return redirect(importacion_url(importacion))
    return redirect(f'{importacion_url(importacion)}?empezar=1')


@require_POST
@requiere_permiso('importar_canales')
def importacion_borrar(request, pk):
    """Borra el informe. Los canales que se agregaron con esa lista quedan."""
    importacion = get_object_or_404(Importacion, pk=pk)
    importacion.delete()
    messages.success(request, f'Se borró el informe de "{importacion.archivo}". Los canales agregados siguen cargados.')
    return redirect('canales:inicio')


# ── Volver a verificar todas las fuentes, de a tandas ────────────────

@require_POST
@requiere_permiso('importar_canales')
def verificar_lote(request):
    try:
        desde = int(request.POST.get('desde', 0))
    except ValueError:
        desde = 0
    return JsonResponse(servicios.verificar_lote_de_fuentes(verificar_varias, desde, usuario=request.user))


# ── Catálogo ─────────────────────────────────────────────────────────

def _filtros_catalogo(datos):
    return {
        'texto': datos.get('q', '').strip(),
        'categoria': datos.get('categoria', ''),
        'idioma': datos.get('idioma', ''),
        'estado': datos.get('estado', ''),
        'sin_logo': datos.get('sin_logo') == '1',
        'origen': datos.get('origen', ''),
        'contenido': datos.get('contenido', ''),
    }


@requiere_permiso('ver_canales')
def catalogo(request):
    filtros = _filtros_catalogo(request.GET)
    pagina = Paginator(consultas.catalogo(**filtros), CANALES_POR_PAGINA).get_page(request.GET.get('pagina'))
    for canal in pagina:
        canal.no_se_ve = consultas.por_que_no_se_ve(canal)
    return render(request, 'canales/catalogo.html', {
        'pagina': pagina,
        'grupos': consultas.agrupar_por_categoria(pagina),
        'filtros': filtros,
        'hay_filtros': any(filtros.values()),
        'parametros': _parametros_sin_pagina(request),
        'categorias': consultas.categorias_con_canales(),
        'origenes': consultas.origenes(),
        'idiomas': Idioma.choices,
        'contenidos': Contenido.choices,
        'puede_editar': chequear_permiso(request.user, 'importar_canales'),
        'resumen': consultas.resumen(),
    })


def _canales_elegidos(request):
    """Los canales marcados, o todos los que coinciden con el filtro (si se pidió "todos")."""
    if request.POST.get('todos_del_filtro') == '1':
        pks = consultas.catalogo(**_filtros_catalogo(request.POST)).values_list('pk', flat=True)
    else:
        pks = [pk for pk in request.POST.getlist('canal') if pk.isdigit()]
    return Canal.objects.filter(pk__in=list(pks))


def _volver(request):
    """A dónde volver (la misma página y filtros del catálogo). Solo direcciones de este sitio."""
    volver = request.POST.get('volver') or request.GET.get('volver') or ''
    if not url_has_allowed_host_and_scheme(volver, allowed_hosts={request.get_host()}):
        volver = reverse('canales:catalogo')
    return volver


def _volver_al_catalogo(request):
    return redirect(_volver(request))


@require_POST
@requiere_permiso('importar_canales')
def catalogo_quitar(request):
    form = QuitarCanalesForm(request.POST)
    motivo = form.cleaned_data['motivo'] if form.is_valid() else ''
    cantidad = servicios.quitar_canales(_canales_elegidos(request), motivo, request.user)
    if cantidad:
        messages.success(request, f'Se quitaron {cantidad} canal(es) de la app.')
    else:
        messages.info(request, 'No se quitó ningún canal (no había ninguno elegido, o ya estaban quitados).')
    return _volver_al_catalogo(request)


@require_POST
@requiere_permiso('importar_canales')
def catalogo_mostrar(request):
    cantidad = servicios.mostrar_canales(_canales_elegidos(request), request.user)
    if cantidad:
        messages.success(request, f'{cantidad} canal(es) vuelven a la app (si tienen alguna fuente que ande).')
    else:
        messages.info(request, 'No había ningún canal quitado entre los elegidos.')
    return _volver_al_catalogo(request)


# ── Editar un canal ──────────────────────────────────────────────────

@requiere_permiso('importar_canales')
def canal_editar(request, pk):
    canal = get_object_or_404(Canal.objects.select_related('categoria'), pk=pk)
    form = CanalForm(request.POST or None, instance=canal)
    fuentes = FuentesFormSet(request.POST or None, queryset=canal.fuentes.all(), prefix='fuentes')
    if request.method == 'POST' and form.is_valid() and fuentes.is_valid():
        canal, nueva = servicios.guardar_canal(form, fuentes, request.user, verificar_url)
        messages.success(request, f'Se guardó "{canal.nombre}".')
        if nueva is not None:
            if nueva.estado == nueva.Estado.CAIDA:
                messages.warning(request, f'La fuente nueva se agregó, pero no funciona: {nueva.error}')
            else:
                messages.success(request, f'Fuente nueva agregada ({nueva.get_tipo_display()}, '
                                          f'{nueva.get_estado_display().lower()}).')
        return redirect(_volver(request))
    return render(request, 'canales/editar.html', {
        'canal': canal,
        'form': form,
        'fuentes': fuentes,
        'volver': _volver(request),
    })
