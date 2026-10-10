"""
Lo más visto: lo que cuenta la app y el ranking para el panel.

La app junta cuánto se mira cada cosa y lo manda de a ratos. Acá se suma en
totales por día (Visto, FavoritoAgregado). NO se guarda quién miró qué:
solo cuánto se miró en total. El ranking lo ve solo quien tenga el permiso
`ver_estadisticas`.

    from canales.estadisticas import registrar, lo_mas_visto
    registrar([{'id': 12, 'segundos': 300, 'vista': True}], ['c:12', 's:Flash Gordon'])
    lo_mas_visto(dias=30)  -> Ranking(vivo=[Fila...], pelicula=[...], serie=[...], totales={...})
"""

import re
from dataclasses import dataclass, field
from datetime import timedelta

from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from . import clasificar
from .models import Canal, Contenido, FavoritoAgregado, Seccion, Visto

# Lo que se acepta en un aviso de la app (más es un error o un abuso)
MAXIMO_DE_ELEMENTOS = 50
MAXIMO_DE_SEGUNDOS = 6 * 3600   # de una misma cosa, en un mismo aviso

_CLAVE_FAVORITO = re.compile(r'^(c:\d{1,10}|s:.{1,128})$', re.S)

# Cuántos se muestran de cada tipo en el panel
PUESTOS = 50
PERIODOS = (7, 30, 90)


# ── Lo que manda la app ──────────────────────────────────────────────

def registrar(vistos, favoritos=(), hoy=None):
    """
    Suma al día de hoy lo que mandó la app.
      vistos:    [{'id': <canal>, 'segundos': 300, 'vista': True}, ...]
                 ('vista': es la primera vez que se cuenta ese rato: suma una vista)
      favoritos: claves que se agregaron a favoritos ("c:12", "s:Flash Gordon").
    Lo que no se entiende o no existe se ignora. Devuelve cuántos elementos se sumaron.
    """
    hoy = hoy or timezone.localdate()
    sumas = {}
    for elemento in list(vistos or [])[:MAXIMO_DE_ELEMENTOS]:
        try:
            pk = int(elemento['id'])
            segundos = max(0, min(int(elemento.get('segundos') or 0), MAXIMO_DE_SEGUNDOS))
        except (KeyError, TypeError, ValueError):
            continue
        vista = 1 if elemento.get('vista') is True else 0
        if segundos or vista:
            anterior = sumas.get(pk, (0, 0))
            sumas[pk] = (anterior[0] + segundos, anterior[1] + vista)
    existen = set(Canal.objects.filter(pk__in=sumas).values_list('pk', flat=True))
    claves = [c for c in list(favoritos or [])[:MAXIMO_DE_ELEMENTOS]
              if isinstance(c, str) and _CLAVE_FAVORITO.match(c)]

    with transaction.atomic():
        for pk, (segundos, vistas) in sumas.items():
            if pk in existen:
                fila, _ = Visto.objects.get_or_create(canal_id=pk, fecha=hoy)
                Visto.objects.filter(pk=fila.pk).update(segundos=F('segundos') + segundos,
                                                        vistas=F('vistas') + vistas)
        for clave in claves:
            fila, _ = FavoritoAgregado.objects.get_or_create(clave=clave, fecha=hoy)
            FavoritoAgregado.objects.filter(pk=fila.pk).update(veces=F('veces') + 1)
    return len(existen & set(sumas)) + len(claves)


# ── El ranking para el panel ─────────────────────────────────────────

@dataclass
class Fila:
    nombre: str
    logo: str = ''
    segundos: int = 0
    vistas: int = 0
    favoritos: int = 0
    canal: Canal | None = None   # para enlazar a su edición (canales y películas)
    capitulos: int = 0           # series: cuántos capítulos distintos se miraron
    en_la_app: bool = True       # False: se quitó del catálogo (igual cuenta lo que se miró)

    @property
    def tiempo(self):
        """'3 h 20 min', '12 min', 'menos de 1 min'."""
        minutos = self.segundos // 60
        if not minutos:
            return 'menos de 1 min' if self.segundos else '—'
        horas, minutos = divmod(minutos, 60)
        return f'{horas} h {minutos} min' if horas else f'{minutos} min'


@dataclass
class Ranking:
    dias: int
    vivo: list = field(default_factory=list)
    pelicula: list = field(default_factory=list)
    serie: list = field(default_factory=list)
    totales: dict = field(default_factory=dict)   # {'vivo': Fila(total), ...}


def _ordenar(filas):
    return sorted(filas, key=lambda f: (-f.segundos, -f.favoritos, -f.vistas, f.nombre.lower()))[:PUESTOS]


def lo_mas_visto(dias=30, hoy=None):
    """Lo más visto en los últimos `dias` días, separado en canales en vivo, películas y series."""
    hoy = hoy or timezone.localdate()
    desde = hoy - timedelta(days=dias - 1)
    vistos = {
        fila['canal']: fila
        for fila in (Visto.objects.filter(fecha__gte=desde, fecha__lte=hoy).values('canal')
                     .annotate(total_segundos=Sum('segundos'), total_vistas=Sum('vistas')))
    }
    favoritos = dict(FavoritoAgregado.objects.filter(fecha__gte=desde, fecha__lte=hoy)
                     .values('clave').annotate(total=Sum('veces')).values_list('clave', 'total'))
    ids_favoritos = {int(c[2:]) for c in favoritos if c.startswith('c:')}
    canales = Canal.objects.in_bulk(set(vistos) | ids_favoritos)

    ranking = Ranking(dias=dias)
    series = {}
    # Lo de las secciones nuevas va con lo de su forma: Música con películas, Radio con en vivo
    formas = {s.clave: s.forma for s in Seccion.todos.all()}
    for pk, canal in canales.items():
        visto = vistos.get(pk, {})
        segundos, vistas = visto.get('total_segundos') or 0, visto.get('total_vistas') or 0
        if canal.contenido == Contenido.SERIE:
            nombre = clasificar.episodio(canal.nombre)[0]
            serie = series.setdefault(nombre.lower(), Fila(nombre=nombre, logo=canal.logo, en_la_app=False))
            serie.segundos += segundos
            serie.vistas += vistas
            serie.capitulos += 1 if segundos or vistas else 0
            serie.logo = serie.logo or canal.logo
            serie.en_la_app = serie.en_la_app or canal.activo
            continue
        forma = formas.get(canal.contenido, canal.contenido)
        if forma not in (Contenido.VIVO, Contenido.PELICULA):
            continue
        getattr(ranking, forma).append(Fila(
            nombre=canal.nombre, logo=canal.logo, segundos=segundos, vistas=vistas,
            favoritos=favoritos.get(f'c:{pk}', 0), canal=canal, en_la_app=canal.activo))
    # Los favoritos de las series van por nombre (la app guarda la serie entera)
    for clave, total in favoritos.items():
        if clave.startswith('s:'):
            serie = series.setdefault(clave[2:].lower(), Fila(nombre=clave[2:]))
            serie.favoritos += total
    ranking.serie = list(series.values())

    for contenido in Contenido.values:
        filas = getattr(ranking, contenido)
        ranking.totales[contenido] = Fila(
            nombre='Total', segundos=sum(f.segundos for f in filas), vistas=sum(f.vistas for f in filas),
            favoritos=sum(f.favoritos for f in filas))
        setattr(ranking, contenido, _ordenar(filas))
    return ranking
