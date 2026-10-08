"""
Pantallas de canales del panel:

  /canales/                         resumen, subir una lista, verificar todas (de a tandas) e importaciones anteriores
  /canales/importaciones/<id>/      la prueba de una lista: el avance, qué es apto, qué no y por qué, y cargar las aptas
  /canales/catalogo/                canales en vivo y películas, con filtros para quitar los que no sirven
  /canales/series/                  series agrupadas, con búsqueda, filtros y paginación
  /canales/como-en-la-app/          lo que ve un cliente: categorías con cuántos tienen y cuáles son (para ordenar)
  /canales/series/detalle/          temporadas, capítulos, disponibilidad y fuentes de una serie
  /canales/canal/<id>/editar/       nombre, logo, categoría... de un canal, y sus fuentes
  /canales/probar/                  probar una dirección suelta y, si anda, agregarla como canal
  /canales/lo-mas-visto/            lo más visto (canales, películas y series), sin datos de clientes
  /canales/categorias/              ordenar las categorías: crear, renombrar, juntar, borrar y el orden en la app
  (y en el catálogo y en Series: mover a otra categoría y cambiar el tipo de lo elegido)

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

from . import consultas, estadisticas, organizar, servicios
from .clasificar import formato, idioma_y_pais, limpiar_nombre
from .forms import CanalForm, CanalNuevoForm, FuentesFormSet, ImportarListaForm, ProbarLinkForm, QuitarCanalesForm
from .models import Canal, Categoria, Contenido, EntradaImportada, Fuente, Idioma, Importacion
from .verificacion import Resultado, verificar_url, verificar_varias

CANALES_POR_PAGINA = 120
ENTRADAS_POR_PAGINA = 100
SERIES_POR_PAGINA = 24
COMO_EN_LA_APP_POR_PAGINA = 150


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
        'todas_las_categorias': Categoria.objects.order_by('nombre'),
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
        'puede_editar': chequear_permiso(request.user, 'importar_canales'),
        'todas_las_categorias': Categoria.objects.order_by('nombre'),
    })


@requiere_permiso('ver_canales')
def como_en_la_app(request):
    """
    Lo que ve un cliente, como en la app: las categorías con cuántos tienen
    ("Kids 5") y, al elegir una, cuáles son. Para ordenar viendo lo mismo que él.
    """
    contenido = request.GET.get('contenido', '')
    if contenido not in Contenido.values:
        contenido = Contenido.VIVO
    grupos = [
        {
            'clave': str(categoria.pk) if categoria else 'ninguna',
            'categoria': categoria,
            'nombre': consultas.nombre_en_la_app(categoria.nombre if categoria else ''),
            'cantidad': len(items),
            'items': items,
        }
        for categoria, items in consultas.como_en_la_app(contenido)
    ]
    # Dos categorías que en la app se llaman igual ("AR | Deportes" y "Deportes"): marcarlas
    veces = {}
    for grupo in grupos:
        veces[grupo['nombre'].casefold()] = veces.get(grupo['nombre'].casefold(), 0) + 1
    for grupo in grupos:
        grupo['repetida'] = veces[grupo['nombre'].casefold()] > 1
        grupo['otro_nombre'] = (grupo['categoria'] is not None
                                and grupo['categoria'].nombre.strip() != grupo['nombre'])

    pedida = request.GET.get('categoria', '')
    elegida = next((g for g in grupos if g['clave'] == pedida), grupos[0] if grupos else None)
    return render(request, 'canales/como_en_la_app.html', {
        'contenido': contenido,
        'grupos': grupos,
        'elegida': elegida,
        'pagina': Paginator(elegida['items'] if elegida else [], COMO_EN_LA_APP_POR_PAGINA).get_page(
            request.GET.get('pagina')),
        'parametros': _parametros_sin_pagina(request),
        'total': sum(g['cantidad'] for g in grupos),
        'puede_editar': chequear_permiso(request.user, 'importar_canales'),
        'todas_las_categorias': Categoria.objects.order_by('nombre'),
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


def _categoria_elegida(request):
    """La categoría de destino: una nueva (si se escribió) o una de la lista. None = sin categoría."""
    nueva = request.POST.get('nueva_categoria', '').strip()
    if nueva:
        return organizar.categoria_por_nombre(nueva, usuario=request.user)
    elegida = request.POST.get('categoria', '')
    if elegida == 'ninguna':
        return None
    if not elegida.isdigit():
        raise organizar.NoSePuede('Elegí una categoría o escribí una nueva.')
    return get_object_or_404(Categoria, pk=elegida)


@require_POST
@requiere_permiso('importar_canales')
def catalogo_categoria(request):
    """Mueve lo elegido a otra categoría (o a una nueva)."""
    try:
        categoria = _categoria_elegida(request)
    except organizar.NoSePuede as error:
        messages.error(request, str(error))
        return _volver_al_catalogo(request)
    cantidad = organizar.mover_a_categoria(_canales_elegidos(request), categoria, request.user)
    messages.success(request, f'Se movieron {cantidad} a "{categoria or "Sin categoría"}".' if cantidad
                     else 'No se movió nada (ya estaban en esa categoría, o no había ninguno elegido).')
    return _volver_al_catalogo(request)


def _avisar_cambio_de_tipo(request, cantidad, sin_numero, contenido):
    if not cantidad:
        messages.info(request, 'No había ninguno elegido.')
        return
    destino = {Contenido.VIVO: 'canales en vivo', Contenido.PELICULA: 'películas', Contenido.SERIE: 'series'}[contenido]
    messages.success(request, f'{cantidad} pasaron a {destino}.')
    if sin_numero:
        messages.warning(request, f'{sin_numero} no dicen temporada y capítulo en el nombre ("S01 E01"): la app '
                                  f'los toma como series de un solo capítulo y no los muestra. Elegilos y pasalos '
                                  f'a serie escribiendo el nombre de la serie, o editales el nombre.')


@require_POST
@requiere_permiso('importar_canales')
def catalogo_contenido(request):
    """Cambia el tipo de lo elegido: en vivo, película o serie (con nombre de serie: los numera)."""
    contenido = request.POST.get('contenido', '')
    try:
        temporada = max(1, min(int(request.POST.get('temporada') or 1), 99))
    except ValueError:
        messages.error(request, 'La temporada tiene que ser un número.')
        return _volver_al_catalogo(request)
    try:
        cantidad, sin_numero = organizar.cambiar_contenido(
            _canales_elegidos(request), contenido, request.POST.get('nombre_serie', ''), temporada, request.user)
    except organizar.NoSePuede as error:
        messages.error(request, str(error))
        return _volver_al_catalogo(request)
    _avisar_cambio_de_tipo(request, cantidad, sin_numero, contenido)
    return _volver_al_catalogo(request)


@require_POST
@requiere_permiso('importar_canales')
def series_acciones(request):
    """Sobre series enteras (todos sus capítulos): moverlas de categoría o pasarlas a películas."""
    capitulos = organizar.capitulos_de(request.POST.getlist('serie'))
    try:
        if request.POST.get('accion') == 'mover':
            categoria = _categoria_elegida(request)
            cantidad = organizar.mover_a_categoria(capitulos, categoria, request.user)
            messages.success(request, f'Se movieron {cantidad} capítulo(s) a "{categoria or "Sin categoría"}".'
                             if cantidad else 'No se movió nada (ya estaban en esa categoría).')
        elif request.POST.get('accion') == 'a_peliculas':
            cantidad, _ = organizar.cambiar_contenido(capitulos, Contenido.PELICULA, usuario=request.user)
            _avisar_cambio_de_tipo(request, cantidad, 0, Contenido.PELICULA)
    except organizar.NoSePuede as error:
        messages.error(request, str(error))
    volver = request.POST.get('volver') or ''
    if not url_has_allowed_host_and_scheme(volver, allowed_hosts={request.get_host()}):
        volver = reverse('canales:series')
    return redirect(volver)


# ── Categorías ───────────────────────────────────────────────────────

def _accion_de_categorias(request):
    """Hace lo que se pidió en la página de categorías y devuelve el mensaje (o lanza NoSePuede)."""
    accion = request.POST.get('accion', '')
    if accion == 'crear':
        categoria = organizar.crear_categoria(request.POST.get('nombre', ''), request.user)
        return f'Se creó "{categoria}". Ahora elegí qué va adentro desde el catálogo ("Mover a categoría").'
    if accion == 'renombrar':
        categoria = get_object_or_404(Categoria, pk=request.POST.get('categoria', '0'))
        viejo = categoria.nombre
        final = organizar.renombrar_categoria(categoria, request.POST.get('nombre', ''), request.user)
        return f'"{viejo}" ahora se llama "{final}".' if final.pk == categoria.pk else f'Ya existía "{final}": se juntaron.'
    if accion == 'juntar':
        elegidas = Categoria.objects.filter(pk__in=[pk for pk in request.POST.getlist('elegida') if pk.isdigit()])
        final = organizar.juntar_categorias(list(elegidas), request.POST.get('destino', ''), request.user)
        return f'Se juntaron en "{final}". Las listas que traigan esos nombres van a ir a "{final}".'
    if accion == 'borrar':
        categoria = get_object_or_404(Categoria, pk=request.POST.get('categoria', '0'))
        cantidad = organizar.borrar_categoria(categoria, request.user)
        return f'Se borró "{categoria}"' + (f' y {cantidad} quedaron sin categoría.' if cantidad else '.')
    if accion == 'ordenar':
        ordenes = {int(clave[6:]): int(valor or 0) for clave, valor in request.POST.items()
                   if clave.startswith('orden_') and clave[6:].isdigit() and (valor or '0').isdigit()}
        cantidad = organizar.ordenar_categorias(ordenes, request.user)
        return f'Se guardó el orden ({cantidad} cambiaron).' if cantidad else 'El orden ya estaba así.'
    raise organizar.NoSePuede('No se entendió qué hacer.')


@requiere_permiso('importar_canales')
def categorias(request):
    """Crear, renombrar, juntar, borrar y ordenar las categorías."""
    if request.method == 'POST':
        try:
            messages.success(request, _accion_de_categorias(request))
        except organizar.NoSePuede as error:
            messages.error(request, str(error))
        volver = request.POST.get('volver') or ''
        if not url_has_allowed_host_and_scheme(volver, allowed_hosts={request.get_host()}):
            volver = reverse('canales:categorias')
        return redirect(volver)

    lista = list(organizar.categorias_con_cantidades())
    return render(request, 'canales/categorias.html', {
        'categorias': lista,
        'parecidas': organizar.categorias_parecidas(lista),
    })


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
