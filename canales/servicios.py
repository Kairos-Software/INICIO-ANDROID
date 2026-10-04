"""
Lo que el sistema HACE con los canales (capa Base).

La verificación se recibe como parámetro (`verificar`) en vez de llamarla
directo: así los tests pasan una de mentira y no salen a internet.
La real es `canales.verificacion.verificar_varias(fuentes, cabeceras=...)`.
"""

from dataclasses import dataclass, field

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from actividad.models import Accion
from actividad.registro import registrar

from .m3u import leer_m3u, normalizar
from .models import Canal, Categoria, Fuente


@dataclass
class ResultadoImportacion:
    canales_nuevos: int = 0
    fuentes_nuevas: int = 0
    repetidas: int = 0
    funcionan: int = 0
    caidas: int = 0
    sin_verificar: int = 0
    # [(nombre del canal, dirección, motivo), ...] para mostrar en el panel
    detalle_caidas: list = field(default_factory=list)

    def __str__(self):
        texto = (f'{self.canales_nuevos} canal(es) nuevo(s), {self.fuentes_nuevas} fuente(s) nueva(s), '
                 f'{self.repetidas} ya existían.')
        if self.funcionan or self.caidas:
            texto += f' Funcionan {self.funcionan}, caídas {self.caidas}, sin verificar {self.sin_verificar}.'
        return texto


@dataclass
class ResultadoVerificacion:
    funcionan: int = 0
    caidas: int = 0
    sin_verificar: int = 0
    revividas: int = 0   # estaban caídas y volvieron
    nuevas_caidas: int = 0

    def __str__(self):
        return (f'Funcionan {self.funcionan}, caídas {self.caidas}, sin verificar {self.sin_verificar} '
                f'({self.revividas} volvieron, {self.nuevas_caidas} se cayeron).')


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


def importar_m3u(texto, origen='', usuario=None, verificar=None):
    """
    Agrega los canales de una lista M3U. Nunca pisa lo que ya existe:
      - canal nuevo            -> se crea (con su categoría, logo y número)
      - canal que ya existía   -> la dirección se agrega como fuente alternativa
      - dirección repetida     -> se ignora

    Con `verificar`, antes de guardar se prueban las direcciones nuevas:
    las que no responden se guardan igual, pero como CAÍDAS (la app no las
    usa hasta que una verificación posterior las encuentre funcionando).
    """
    entradas = leer_m3u(texto)
    estados = {}
    if verificar:
        # Fuera de la transacción: puede tardar y no conviene tener la base trabada
        ya_guardadas = set(Fuente.objects.filter(url__in=[e.url for e in entradas]).values_list('url', flat=True))
        nuevas = [e for e in entradas if e.url not in ya_guardadas]
        estados = verificar({e.url: e.tipo for e in nuevas},
                            cabeceras={e.url: (e.user_agent, e.referer) for e in nuevas if e.user_agent or e.referer})
    ahora = timezone.now()

    resultado = ResultadoImportacion()
    with transaction.atomic():
        for entrada in entradas:
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
            verificacion = estados.get(entrada.url)
            Fuente.objects.create(
                canal=canal, url=entrada.url[:1000], tipo=entrada.tipo, prioridad=prioridad, origen=origen[:150],
                user_agent=entrada.user_agent[:300], referer=entrada.referer[:500],
                estado=verificacion.estado if verificacion else Fuente.Estado.SIN_VERIFICAR,
                error=verificacion.error[:200] if verificacion else '',
                verificada=ahora if verificacion else None,
            )
            resultado.fuentes_nuevas += 1
            _contar(resultado, verificacion.estado if verificacion else Fuente.Estado.SIN_VERIFICAR)
            if verificacion and verificacion.estado == Fuente.Estado.CAIDA:
                resultado.detalle_caidas.append((canal.nombre, entrada.url, verificacion.error))

        registrar(usuario, Accion.CREAR, f'Importó la lista de canales "{origen}": {resultado}', modulo='canales')
    return resultado


def _contar(resultado, estado):
    if estado == Fuente.Estado.FUNCIONA:
        resultado.funcionan += 1
    elif estado == Fuente.Estado.CAIDA:
        resultado.caidas += 1
    else:
        resultado.sin_verificar += 1


def verificar_fuentes_guardadas(verificar, usuario=None):
    """
    Vuelve a probar TODAS las fuentes de los canales vigentes y actualiza su
    estado. Las caídas que volvieron pasan a "funciona" (y la app las vuelve
    a usar); las que se cayeron dejan de usarse. No toca `activa`.
    """
    fuentes = list(Fuente.objects.filter(canal__eliminado_en__isnull=True))
    estados = verificar({f.url: f.tipo for f in fuentes},
                        cabeceras={f.url: (f.user_agent, f.referer) for f in fuentes if f.user_agent or f.referer})
    ahora = timezone.now()

    resultado = ResultadoVerificacion()
    for fuente in fuentes:
        nuevo = estados[fuente.url]
        if fuente.estado == Fuente.Estado.CAIDA and nuevo.estado == Fuente.Estado.FUNCIONA:
            resultado.revividas += 1
        elif fuente.estado != Fuente.Estado.CAIDA and nuevo.estado == Fuente.Estado.CAIDA:
            resultado.nuevas_caidas += 1
        fuente.estado, fuente.error, fuente.verificada = nuevo.estado, nuevo.error[:200], ahora
        _contar(resultado, nuevo.estado)
    Fuente.objects.bulk_update(fuentes, ['estado', 'error', 'verificada'])

    registrar(usuario, Accion.EDITAR, f'Verificó las fuentes de los canales: {resultado}', modulo='canales')
    return resultado


# Una misma fuente se re-prueba como máximo una vez en este tiempo, aunque
# muchos aparatos avisen que falla a la vez (no se satura al servidor).
ESPERA_ENTRE_REVERIFICACIONES = 5 * 60   # segundos


def reverificar_por_aviso(fuente, verificar_url):
    """
    La app avisó que no pudo reproducir esta fuente. El servidor la vuelve a
    probar POR SU CUENTA (el aviso solo no alcanza: el problema puede ser la
    conexión de ese aparato): si al servidor también le falla, queda caída y
    la app deja de recibirla. Si ya la probó hace poco, no la vuelve a probar.
    Devuelve el estado con el que quedó.
    """
    clave = f'reverificar_fuente:{fuente.pk}'
    if not cache.add(clave, True, timeout=ESPERA_ENTRE_REVERIFICACIONES):
        return fuente.estado
    resultado = verificar_url(fuente.url, fuente.tipo, fuente.user_agent, fuente.referer)
    estado_anterior = fuente.estado
    fuente.estado, fuente.error, fuente.verificada = resultado.estado, resultado.error[:200], timezone.now()
    fuente.save(update_fields=['estado', 'error', 'verificada'])
    if estado_anterior != Fuente.Estado.CAIDA and fuente.estado == Fuente.Estado.CAIDA:
        registrar(None, Accion.SISTEMA, f'La fuente de {fuente.canal} se cayó (avisó la app): {fuente.error}',
                  modulo='canales')
    return fuente.estado
