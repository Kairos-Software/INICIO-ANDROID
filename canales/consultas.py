"""
Lo que el sistema BUSCA de los canales (capa Base).
"""

from django.db.models import Count, Prefetch

from .models import Canal, Fuente


# Lo que el reproductor de la app sabe reproducir. YouTube todavía no: un
# canal que solo tiene fuentes de YouTube no se manda (la app mostraría error).
TIPOS_QUE_REPRODUCE_LA_APP = [Fuente.Tipo.HLS]


def fuentes_usables():
    """
    Las que la app puede usar: activas, no caídas y de un tipo que sabe
    reproducir. Las "sin verificar" sí (todavía no se sabe que fallen).
    """
    return (Fuente.objects.filter(activa=True, tipo__in=TIPOS_QUE_REPRODUCE_LA_APP)
            .exclude(estado=Fuente.Estado.CAIDA))


def canales_disponibles():
    """
    Canales que la app puede mostrar: activos y con al menos una fuente
    usable. Trae esas fuentes (ordenadas por prioridad) y su categoría.

    Más adelante acá se va a filtrar según el plan / los créditos del
    dispositivo que pregunta.
    """
    fuentes = fuentes_usables().order_by('prioridad', 'pk')
    return (
        Canal.objects
        .filter(activo=True, pk__in=fuentes_usables().values('canal'))
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
        'funcionan': por_estado.get(Fuente.Estado.FUNCIONA, 0),
        'caidas': por_estado.get(Fuente.Estado.CAIDA, 0),
        'sin_verificar': por_estado.get(Fuente.Estado.SIN_VERIFICAR, 0),
    }


def fuentes_caidas(limite=100):
    """Las fuentes caídas de canales vigentes, las verificadas más recientemente primero."""
    return (
        Fuente.objects
        .filter(estado=Fuente.Estado.CAIDA, canal__eliminado_en__isnull=True)
        .select_related('canal')
        .order_by('-verificada', 'canal__nombre')[:limite]
    )
