"""
Lo que el sistema BUSCA de los canales (capa Base).
"""

from django.db.models import Count, Exists, OuterRef, Prefetch, Q

from .models import Canal, Categoria, Contenido, Fuente, Importacion, hace_dias_oculta

# Lo que el reproductor de la app sabe reproducir. La app nueva lo dice al
# pedir los canales (?formatos=hls,dash,directo,rtsp,youtube,pagina); la
# 1.0.0 no dice nada y solo sabe HLS: a esa se le manda solo HLS (si no,
# mostraría canales que no puede abrir).
TIPOS_QUE_REPRODUCE_LA_APP = [Fuente.Tipo.HLS, Fuente.Tipo.DASH, Fuente.Tipo.DIRECTO, Fuente.Tipo.RTSP,
                              Fuente.Tipo.YOUTUBE, Fuente.Tipo.PAGINA]
TIPOS_DE_LA_APP_VIEJA = [Fuente.Tipo.HLS]


def tipos_pedidos(texto):
    """'hls,directo,cualquiera' -> los que existen. Vacío -> los de la app vieja."""
    pedidos = [t.strip() for t in (texto or '').split(',') if t.strip() in Fuente.Tipo.values]
    return pedidos or TIPOS_DE_LA_APP_VIEJA


def fuentes_usables(tipos=None):
    """
    Las que la app puede usar: activas, no caídas, no ocultas por fallar en
    los aparatos y de un tipo que sabe reproducir. Las "sin verificar" sí
    (todavía no se sabe que fallen).
    """
    return (Fuente.objects.filter(activa=True, tipo__in=tipos or TIPOS_QUE_REPRODUCE_LA_APP)
            .exclude(estado=Fuente.Estado.CAIDA)
            .exclude(oculta_desde__gt=hace_dias_oculta()))


def canales_disponibles(tipos=None, contenido=Contenido.VIVO):
    """
    Canales que la app puede mostrar: activos, del contenido pedido (en vivo,
    películas o series) y con al menos una fuente usable. Trae esas fuentes
    (ordenadas por prioridad) y su categoría.

    Más adelante acá se va a filtrar según el plan / los créditos del
    dispositivo que pregunta.
    """
    fuentes = fuentes_usables(tipos).order_by('prioridad', 'pk')
    return (
        Canal.objects
        .filter(activo=True, contenido=contenido, pk__in=fuentes_usables(tipos).values('canal'))
        .select_related('categoria')
        .prefetch_related(Prefetch('fuentes', queryset=fuentes, to_attr='fuentes_activas'))
        .order_by('categoria__orden', 'categoria__nombre', 'orden', 'nombre')
    )


def agrupar_por_categoria(canales):
    """[(categoría o None, [canales]), ...] en el orden en que vienen."""
    grupos = {}
    for canal in canales:
        grupos.setdefault(canal.categoria_id, (canal.categoria, []))[1].append(canal)
    return list(grupos.values())


def resumen():
    """Números para la pantalla de canales del panel."""
    por_estado = dict(
        Fuente.objects.filter(canal__eliminado_en__isnull=True)
        .order_by()   # sin el orden por defecto, que rompería el agrupado
        .values_list('estado').annotate(cantidad=Count('pk'))
    )
    return {
        'canales': Canal.objects.count(),
        'canales_en_la_app': canales_disponibles().count(),
        'canales_en_la_app_vieja': canales_disponibles(TIPOS_DE_LA_APP_VIEJA).count(),
        'quitados': Canal.objects.filter(activo=False).count(),
        'peliculas': Canal.objects.filter(contenido=Contenido.PELICULA).count(),
        'series': Canal.objects.filter(contenido=Contenido.SERIE).count(),
        'funcionan': por_estado.get(Fuente.Estado.FUNCIONA, 0),
        'caidas': por_estado.get(Fuente.Estado.CAIDA, 0),
        'sin_verificar': por_estado.get(Fuente.Estado.SIN_VERIFICAR, 0),
        'fuentes': sum(por_estado.values()),
    }


def ultimas_importaciones(limite=10):
    return Importacion.objects.select_related('usuario')[:limite]


# ── Catálogo: todos los canales, como los ve la app ──────────────────

def catalogo(texto='', categoria='', idioma='', estado='', sin_logo=False, origen='', contenido=''):
    """
    Todos los canales con sus números (cuántas fuentes, cuántas andan) y si
    la app los muestra. Filtros:
      estado: 'en_app' | 'fuera' (no se ven: sin fuentes que anden) | 'quitados' | '' (todos)
      idioma: 'es' | 'otro' | 'sin_dato'
      contenido: 'vivo' | 'pelicula' | 'serie' | '' (todo)
    """
    usables = fuentes_usables().filter(canal=OuterRef('pk'))
    canales = (
        Canal.objects.select_related('categoria')
        .annotate(
            fuentes_total=Count('fuentes', distinct=True),
            fuentes_funcionan=Count('fuentes', filter=Q(fuentes__estado=Fuente.Estado.FUNCIONA), distinct=True),
            fuentes_caidas=Count('fuentes', filter=Q(fuentes__estado=Fuente.Estado.CAIDA), distinct=True),
            tiene_usable=Exists(usables),
            fuentes_ocultas=Count('fuentes', filter=Q(fuentes__oculta_desde__gt=hace_dias_oculta()), distinct=True),
        )
        .prefetch_related(Prefetch('fuentes', queryset=Fuente.objects.order_by('prioridad', 'pk')))
        .order_by('categoria__orden', 'categoria__nombre', 'orden', 'nombre')
    )
    if texto:
        canales = canales.filter(Q(nombre__icontains=texto) | Q(tvg_id__icontains=texto))
    if categoria == 'ninguna':
        canales = canales.filter(categoria__isnull=True)
    elif categoria:
        canales = canales.filter(categoria_id=categoria)
    if idioma == 'sin_dato':
        canales = canales.filter(idioma='')
    elif idioma:
        canales = canales.filter(idioma=idioma)
    if estado == 'en_app':
        canales = canales.filter(activo=True, tiene_usable=True)
    elif estado == 'fuera':
        canales = canales.filter(activo=True, tiene_usable=False)
    elif estado == 'quitados':
        canales = canales.filter(activo=False)
    if contenido in Contenido.values:
        canales = canales.filter(contenido=contenido)
    if sin_logo:
        canales = canales.filter(logo='')
    if origen:
        canales = canales.filter(fuentes__origen=origen).distinct()
    return canales


def por_que_no_se_ve(canal):
    """Para el catálogo: '' si la app lo muestra, si no, el motivo."""
    if not canal.activo:
        return f'Quitado: {canal.motivo_quitado}' if canal.motivo_quitado else 'Quitado a mano.'
    if canal.tiene_usable:
        return ''
    if not canal.fuentes_total:
        return 'No tiene fuentes.'
    if canal.fuentes_caidas == canal.fuentes_total:
        return 'Todas sus fuentes están caídas.'
    if canal.fuentes_ocultas:
        oculta = next((f for f in canal.fuentes.all() if f.oculta_por_aparatos), None)
        if oculta:
            return (f'Oculto porque no se reproduce en los aparatos ({oculta.falla_en_aparatos}). '
                    f'La app lo vuelve a intentar el {oculta.vuelve_a_probarse:%d/%m}.')
    return 'Sus fuentes están apagadas a mano o son de un formato que la app no reproduce.'


def categorias_con_canales():
    return Categoria.objects.annotate(cantidad=Count('canales')).filter(cantidad__gt=0)


def origenes():
    """De qué listas vinieron las fuentes (para filtrar el catálogo)."""
    return (Fuente.objects.exclude(origen='').order_by('origen').values_list('origen', flat=True).distinct())
