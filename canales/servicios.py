"""
Lo que el sistema HACE con los canales (capa Base).
"""

from dataclasses import dataclass, field

from django.db import transaction

from actividad.models import Accion
from actividad.registro import registrar

from .m3u import leer_m3u, normalizar
from .models import Canal, Categoria, Fuente


@dataclass
class ResultadoImportacion:
    canales_nuevos: int = 0
    fuentes_nuevas: int = 0
    repetidas: int = 0
    errores: list = field(default_factory=list)

    def __str__(self):
        return (f'{self.canales_nuevos} canal(es) nuevo(s), {self.fuentes_nuevas} fuente(s) nueva(s), '
                f'{self.repetidas} ya existían.')


def _buscar_canal(entrada):
    """El mismo canal si ya existe: primero por tvg-id, si no por nombre (normalizado)."""
    if entrada.tvg_id:
        canal = Canal.objects.filter(tvg_id__iexact=entrada.tvg_id).first()
        if canal:
            return canal
    buscado = normalizar(entrada.nombre)
    primera_palabra = entrada.nombre.split()[0]
    for canal in Canal.objects.filter(nombre__icontains=primera_palabra):
        if normalizar(canal.nombre) == buscado:
            return canal
    return None


@transaction.atomic
def importar_m3u(texto, origen='', usuario=None):
    """
    Agrega los canales de una lista M3U. Nunca pisa lo que ya existe:
      - canal nuevo            -> se crea (con su categoría, logo y número)
      - canal que ya existía   -> la dirección se agrega como fuente alternativa
      - dirección repetida     -> se ignora
    """
    resultado = ResultadoImportacion()
    for entrada in leer_m3u(texto):
        canal = _buscar_canal(entrada)
        if canal is None:
            categoria = None
            if entrada.categoria:
                categoria, _ = Categoria.objects.get_or_create(nombre=entrada.categoria[:80])
            canal = Canal(
                nombre=entrada.nombre[:120], numero=entrada.numero[:10], logo=entrada.logo[:500],
                categoria=categoria, tvg_id=entrada.tvg_id[:120], pais=entrada.pais,
            )
            canal.marcar_autor(usuario)
            canal.save()
            resultado.canales_nuevos += 1

        if canal.fuentes.filter(url=entrada.url).exists():
            resultado.repetidas += 1
            continue
        prioridad = (canal.fuentes.order_by('-prioridad').values_list('prioridad', flat=True).first() or 0) + 1
        Fuente.objects.create(canal=canal, url=entrada.url[:1000], tipo=entrada.tipo,
                              prioridad=prioridad, origen=origen[:150])
        resultado.fuentes_nuevas += 1

    registrar(usuario, Accion.CREAR, f'Importó la lista de canales "{origen}": {resultado}', modulo='canales')
    return resultado
