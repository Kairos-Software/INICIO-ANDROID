"""
Pantallas de canales del panel:

  /canales/                         resumen, subir una lista, verificar todas (de a tandas) e importaciones anteriores
  /canales/importaciones/<id>/      la prueba de una lista: el avance, qué es apto, qué no y por qué, y cargar las aptas
  /canales/catalogo/                canales en vivo y películas, con filtros para quitar los que no sirven
  /canales/series/                  series agrupadas, con búsqueda, filtros y paginación
  /canales/series/detalle/          temporadas, capítulos, disponibilidad y fuentes de una serie
  /canales/canal/<id>/editar/       nombre, logo, categoría... de un canal, y sus fuentes
  /canales/probar/                  probar una dirección suelta y, si anda, agregarla como canal
  /canales/lo-mas-visto/            lo más visto (canales, películas y series), sin datos de clientes

Lo que tarda (verificar) se hace de a tandas: la página llama una y otra
vez a las direcciones ".../lote/" (responden JSON) y va mostrando el avance.
"""

from functools import partial

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from usuarios.decoradores import requiere_permiso
from usuarios.permisos import chequear_permiso

from . import consultas, estadisticas, servicios
from .clasificar import formato, idioma_y_pais, limpiar_nombre
from .forms import CanalForm, CanalNuevoForm, FuentesFormSet, ImportarListaForm, ProbarLinkForm, QuitarCanalesForm
from .models import Canal, Contenido, EntradaImportada, Fuente, Idioma, Importacion
from .verificacion import Resultado, verificar_url, verificar_varias

CANALES_POR_PAGINA = 120
ENTRADAS_POR_PAGINA = 100
SERIES_POR_PAGINA = 24


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
        'causa': request.GET.get('causa', ''),
        'idioma': request.GET.get('idioma', ''),
        'contenido': request.GET.get('contenido', ''),
    }
    entradas = importacion.entradas.select_related('canal')
    if filtros['texto']:
        entradas = entradas.filter(Q(nombre__icontains=filtros['texto']) | Q(nombre_original__icontains=filtros['texto'])
                                   | Q(categoria__icontains=filtros['texto']))
    if filtros['estado'] in EntradaImportada.Estado.values:
        entradas = entradas.filter(estado=filtros['estado'])
    if filtros['causa'] in EntradaImportada.Causa.values:
        entradas = entradas.filter(estado=EntradaImportada.Estado.RECHAZADA, causa=filtros['causa'])
    if filtros['idioma'] == 'sin_dato':
        entradas = entradas.filter(idioma='')
    elif filtros['idioma'] in ('es', 'otro'):
        entradas = entradas.filter(idioma=filtros['idioma'])
    if filtros['contenido'] in EntradaImportada.Contenido.values:
        entradas = entradas.filter(contenido=filtros['contenido'])

    return render(request, 'canales/importacion.html', {
        'importacion': importacion,
        'avance': servicios.progreso(importacion),
        'por_causa': servicios.por_causa(importacion),
        'pagina': Paginator(entradas, ENTRADAS_POR_PAGINA).get_page(request.GET.get('pagina')),
        'filtros': filtros,
        'hay_filtros': any(filtros.values()),
        'parametros': _parametros_sin_pagina(request),
        'estados': EntradaImportada.Estado.choices,
        'causas': EntradaImportada.Causa.choices,
        'contenidos': EntradaImportada.Contenido.choices,
        'puede_importar': chequear_permiso(request.user, 'importar_canales'),
        'empezar': request.GET.get('empezar') == '1',
        'tamanio_lote': servicios.TAMANIO_LOTE,
    })


@require_POST
@requiere_permiso('importar_canales')
def importacion_lote(request, pk):
    """Prueba la próxima tanda y responde el avance (JSON). La pantalla la llama en bucle."""
    importacion = get_object_or_404(Importacion, pk=pk)
    verificar = partial(verificar_varias, a_fondo=True) if importacion.a_fondo else verificar_varias
    return JsonResponse(servicios.procesar_lote(importacion, verificar))


@require_POST
@requiere_permiso('importar_canales')
def importacion_cargar(request, pk):
    """Carga la próxima tanda de aptas y responde el avance (JSON). La pantalla la llama en bucle."""
    importacion = get_object_or_404(Importacion, pk=pk)
    return JsonResponse(servicios.cargar_lote(importacion))


@require_POST
@requiere_permiso('importar_canales')
def importacion_reintentar(request, pk):
    importacion = get_object_or_404(Importacion, pk=pk)
    cantidad = servicios.reintentar_caidas(importacion, request.user)
    if not cantidad:
        messages.info(request, 'No hay nada para volver a probar.')
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
    if filtros['contenido'] not in (Contenido.VIVO, Contenido.PELICULA):
        filtros['contenido'] = Contenido.VIVO
    pagina = Paginator(consultas.catalogo(**filtros), CANALES_POR_PAGINA).get_page(request.GET.get('pagina'))
    for canal in pagina:
        canal.no_se_ve = consultas.por_que_no_se_ve(canal)
    return render(request, 'canales/catalogo.html', {
        'pagina': pagina,
        'grupos': consultas.agrupar_por_categoria(pagina),
        'filtros': filtros,
        'hay_filtros': any(valor for clave, valor in filtros.items() if clave != 'contenido'),
        'parametros': _parametros_sin_pagina(request),
        'categorias': consultas.categorias_con_canales(filtros['contenido']),
        'origenes': consultas.origenes(filtros['contenido']),
        'idiomas': Idioma.choices,
        'contenidos': Contenido.choices,
        'puede_editar': chequear_permiso(request.user, 'importar_canales'),
        'resumen': consultas.resumen(),
    })


@requiere_permiso('ver_canales')
def series(request):
    """Series agrupadas, sin repetir un bloque por cada capítulo importado."""
    filtros = _filtros_catalogo(request.GET)
    del filtros['contenido']
    if filtros['estado'] not in ('en_app', 'incompleta', 'fuera'):
        filtros['estado'] = ''
    pagina = Paginator(consultas.series(**filtros), SERIES_POR_PAGINA).get_page(request.GET.get('pagina'))
    return render(request, 'canales/series.html', {
        'pagina': pagina,
        'filtros': filtros,
        'hay_filtros': any(filtros.values()),
        'parametros': _parametros_sin_pagina(request),
        'categorias': consultas.categorias_con_canales(Contenido.SERIE),
        'origenes': consultas.origenes(Contenido.SERIE),
    })


@requiere_permiso('ver_canales')
def serie_detalle(request):
    nombre = request.GET.get('nombre', '').strip()
    if not nombre:
        raise Http404('Falta el nombre de la serie.')

    serie = next(
        (item for item in consultas.series(texto=nombre) if item.nombre.casefold() == nombre.casefold()),
        None,
    )
    if serie is None:
        raise Http404('No se encontró la serie.')

    serie.temporadas_ordenadas = []
    for numero in serie.numeros_de_temporada:
        capitulos = serie.temporadas[numero]
        for capitulo in capitulos:
            capitulo.no_se_ve = consultas.por_que_no_se_ve(capitulo.canal)
        serie.temporadas_ordenadas.append((numero, capitulos))

    return render(request, 'canales/serie_detalle.html', {
        'serie': serie,
        'puede_editar': chequear_permiso(request.user, 'importar_canales'),
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


# ── Probar un link y agregarlo a mano ────────────────────────────────

@requiere_permiso('importar_canales')
def probar(request):
    """
    Paso 1: se pega una dirección y se prueba (igual que al importar: formato
    real, como la app y como VLC, YouTube y páginas con yt-dlp).
    Paso 2: si anda (o si se quiere agregar igual), se completan nombre,
    logo, categoría... y se crea el canal.
    """
    prueba = ProbarLinkForm(request.POST if request.POST.get('paso') == 'probar' else None)
    resultado = canal_form = None
    motivo = ''
    ya_cargada = None

    if request.POST.get('paso') == 'agregar':
        prueba = ProbarLinkForm(request.POST)
        if prueba.is_valid():
            datos = prueba.cleaned_data
            resultado = Resultado(estado=request.POST.get('estado', Fuente.Estado.SIN_VERIFICAR),
                                  error=request.POST.get('error', '')[:200], tipo=request.POST.get('tipo', ''),
                                  user_agent=request.POST.get('ua_que_anduvo', '')[:300])
            canal_form = CanalNuevoForm(request.POST)
            if canal_form.is_valid():
                canal = servicios.crear_canal_a_mano(canal_form, datos['url'], resultado, datos['user_agent'],
                                                     datos['referer'], request.user)
                messages.success(request, f'Se agregó "{canal.nombre}".')
                return redirect(reverse('canales:canal_editar', args=[canal.pk]))
    elif prueba.is_bound and prueba.is_valid():
        datos = prueba.cleaned_data
        ya_cargada = Fuente.objects.filter(url=datos['url'], canal__eliminado_en__isnull=True).select_related('canal').first()
        resultado = verificar_url(datos['url'], formato(datos['url']) or 'hls', datos['user_agent'], datos['referer'],
                                  a_fondo=True)
        causa, motivo = servicios.juzgar(resultado, Importacion(solo_espanol=True))
        # Sugerencias para el canal: lo que dijo YouTube / la página, o lo que se deduce de la dirección
        nombre = limpiar_nombre(resultado.titulo) if resultado.titulo else ''
        idioma, pais = idioma_y_pais(nombre)
        canal_form = CanalNuevoForm(initial={'nombre': nombre, 'logo': resultado.imagen, 'idioma': idioma,
                                             'pais': pais, 'contenido': Contenido.VIVO})

    return render(request, 'canales/probar.html', {
        'prueba': prueba,
        'resultado': resultado,
        'canal_form': canal_form,
        'ya_cargada': ya_cargada,
        'tipo_texto': dict(Fuente.Tipo.choices).get(resultado.tipo, resultado.tipo) if resultado else '',
        'no_pasa': motivo if prueba.is_bound and resultado and resultado.estado != Fuente.Estado.CAIDA else '',
    })


@require_POST
@requiere_permiso('importar_canales')
def limpiar_nombres(request):
    renombrados, juntados = servicios.limpiar_nombres(request.user)
    if renombrados or juntados:
        messages.success(request, f'Listo: {renombrados} canal(es) renombrado(s) y {juntados} repetido(s) '
                                  f'juntado(s) con su canal (sus fuentes quedaron como alternativas).')
    else:
        messages.info(request, 'Los nombres ya estaban limpios.')
    return redirect('canales:inicio')


# ── Lo más visto ─────────────────────────────────────────────────────

_PESTANIAS_VISTO = [
    ('vivo', 'En vivo', 'bi-broadcast'),
    ('pelicula', 'Películas', 'bi-film'),
    ('serie', 'Series', 'bi-collection-play'),
]


@requiere_permiso('ver_estadisticas')
def lo_mas_visto(request):
    try:
        dias = int(request.GET.get('dias', 30))
    except ValueError:
        dias = 30
    if dias not in estadisticas.PERIODOS:
        dias = 30
    tipo = request.GET.get('tipo', 'vivo')
    if tipo not in Contenido.values:
        tipo = 'vivo'
    ranking = estadisticas.lo_mas_visto(dias)
    return render(request, 'canales/lo_mas_visto.html', {
        'dias': dias,
        'periodos': estadisticas.PERIODOS,
        'tipo': tipo,
        'pestanias': [(clave, nombre, icono, ranking.totales[clave]) for clave, nombre, icono in _PESTANIAS_VISTO],
        'filas': getattr(ranking, tipo),
        'total': ranking.totales[tipo],
        'puestos': estadisticas.PUESTOS,
        'puede_editar': chequear_permiso(request.user, 'importar_canales'),
    })
