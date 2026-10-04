"""
Lo que el sistema BUSCA de los canales (capa Base).
"""

from django.db.models import Prefetch

from .models import Canal, Fuente


def canales_disponibles():
    """
    Canales que la app puede mostrar: activos y con al menos una fuente
    activa. Trae sus fuentes (ordenadas por prioridad) y su categoría.

    Más adelante acá se va a filtrar según el plan / los créditos del
    dispositivo que pregunta.
    """
    fuentes = Fuente.objects.filter(activa=True).order_by('prioridad', 'pk')
    return (
        Canal.objects
        .filter(activo=True, fuentes__activa=True)
        .distinct()
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
