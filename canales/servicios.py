"""
Lo que el sistema HACE con los canales (capa Base).

Importar una lista es en dos pasos, para que una lista de miles de canales
no trabe el servidor:

    importacion = crear_importacion(texto, 'lista.m3u')   # analiza todo (rápido, no sale a internet)
    procesar_lote(importacion, verificar_varias)          # verifica las próximas 50 y agrega las que andan
    procesar_lote(importacion, verificar_varias)          # ...y así hasta que no quede ninguna pendiente

La pantalla del panel llama a procesar_lote una y otra vez y muestra el
avance. `importar_m3u()` hace todo de una vez (para la consola y las pruebas).

La verificación se recibe como parámetro (`verificar`) en vez de llamarla
directo: así los tests pasan una de mentira y no salen a internet.
La real es `canales.verificacion.verificar_varias(fuentes, cabeceras=..., hasta=...)`.
"""

import time
from dataclasses import dataclass
from datetime import timedelta

from django.core.cache import cache
from django.db import DatabaseError, transaction
from django.db.models import Count, Max
from django.utils import timezone

from actividad.models import Accion
from actividad.registro import registrar

from . import clasificar
from .m3u import leer_m3u, normalizar
from .models import Canal, Categoria, EntradaImportada, Fuente, Importacion

# De a cuántas se verifican, y cuánto puede tardar como máximo una tanda en
# EMPEZAR verificaciones (las que no llegan quedan para la tanda siguiente).
TAMANIO_LOTE = 50
SEGUNDOS_POR_LOTE = 40

Estado = EntradaImportada.Estado


@dataclass
class ResultadoImportacion:
    canales_nuevos: int = 0
    fuentes_nuevas: int = 0
    repetidas: int = 0
    funcionan: int = 0
    caidas: int = 0
    sin_verificar: int = 0
    descartadas: int = 0

    def __str__(self):
        texto = (f'{self.canales_nuevos} canal(es) nuevo(s), {self.fuentes_nuevas} fuente(s) nueva(s), '
                 f'{self.repetidas} ya existían, {self.descartadas} descartada(s).')
        if self.funcionan or self.caidas:
            texto += f' Funcionan {self.funcionan}, no funcionan {self.caidas}, sin verificar {self.sin_verificar}.'
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

    def sumar(self, otro):
        for campo in ('funcionan', 'caidas', 'sin_verificar', 'revividas', 'nuevas_caidas'):
            setattr(self, campo, getattr(self, campo) + getattr(otro, campo))


# ── Paso 1: analizar la lista ────────────────────────────────────────

def _sin_nombre(nombre):
    """Sin nombre de verdad: vacío, solo números/símbolos, o "Canal" a secas."""
    simple = clasificar.sin_acentos(nombre).strip()
    return not any(c.isalpha() for c in simple) or simple in ('canal', 'channel', 'sin nombre')


def _motivo_de_descarte(entrada, importacion, contenido, tipo, idioma, pais, nombre):
    """Por qué se descarta sin verificarla ('' = no se descarta)."""
    if importacion.descartar_vod and contenido != EntradaImportada.Contenido.VIVO:
        que = 'una película' if contenido == EntradaImportada.Contenido.PELICULA else 'un capítulo de serie'
        return f'Es {que}, no un canal en vivo.'
    if importacion.descartar_adultos and clasificar.para_adultos(entrada.nombre, entrada.categoria):
        return 'Es contenido para adultos.'
    if tipo == 'rtmp':
        return 'Es RTMP: la app todavía no reproduce ese formato.'
    if _sin_nombre(nombre):
        return 'No tiene un nombre definido.'
    if importacion.solo_espanol and idioma == 'otro':
        return f'No está en español (país: {pais}).' if pais else 'No está en español.'
    if importacion.descartar_sin_logo and not entrada.logo.strip():
        return 'No tiene logo.'
    return ''


def crear_importacion(texto, archivo='', usuario=None, solo_espanol=False, descartar_sin_logo=False,
                      descartar_vod=False, descartar_adultos=True):
    """
    Lee la lista y guarda cada canal como una EntradaImportada, con lo que se
    sabe de él (idioma, país, si es en vivo o película, formato). Las que no
    sirven quedan descartadas desde ya, con el motivo; las demás, pendientes
    de verificar. No sale a internet: tarda segundos aunque sean miles.
    """
    importacion = Importacion.objects.create(
        archivo=archivo[:150], usuario=usuario if getattr(usuario, 'pk', None) else None,
        solo_espanol=solo_espanol, descartar_sin_logo=descartar_sin_logo, descartar_vod=descartar_vod,
        descartar_adultos=descartar_adultos,
    )
    ya_guardadas = set(Fuente.objects.values_list('url', flat=True))
    vistas = set()
    entradas = []
    for posicion, entrada in enumerate(leer_m3u(texto), start=1):
        nombre = clasificar.limpiar_nombre(entrada.nombre)
        idioma, pais = clasificar.idioma_y_pais(entrada.nombre, entrada.categoria, entrada.pais,
                                                entrada.tvg_id, entrada.idioma)
        contenido = clasificar.contenido(entrada.url, entrada.categoria)
        tipo = clasificar.formato(entrada.url)

        estado, motivo = Estado.PENDIENTE, ''
        if entrada.url in vistas:
            estado, motivo = Estado.REPETIDA, 'La misma dirección aparece antes en esta lista.'
        elif entrada.url in ya_guardadas:
            estado, motivo = Estado.REPETIDA, 'Esta dirección ya estaba cargada.'
        else:
            motivo = _motivo_de_descarte(entrada, importacion, contenido, tipo, idioma, pais, nombre)
            if motivo:
                estado = Estado.DESCARTADA
        vistas.add(entrada.url)

        entradas.append(EntradaImportada(
            importacion=importacion, posicion=posicion,
            nombre_original=entrada.nombre[:200], nombre=(nombre or 'Sin nombre')[:120],
            logo=entrada.logo[:500], categoria=entrada.categoria[:80], numero=entrada.numero[:10],
            tvg_id=entrada.tvg_id[:120], pais=pais, idioma=idioma, contenido=contenido,
            url=entrada.url[:1000], tipo=tipo, user_agent=entrada.user_agent[:300], referer=entrada.referer[:500],
            estado=estado, motivo=motivo,
        ))
    EntradaImportada.objects.bulk_create(entradas, batch_size=1000)

    importacion.total = len(entradas)
    importacion.para_verificar = sum(1 for e in entradas if e.estado == Estado.PENDIENTE)
    if not importacion.para_verificar:
        importacion.terminada = timezone.now()
    importacion.save(update_fields=['total', 'para_verificar', 'terminada'])
    registrar(usuario, Accion.CREAR,
              f'Subió la lista de canales "{archivo}": {importacion.total} canal(es), '
              f'{importacion.para_verificar} para verificar.', modulo='canales')
    return importacion


# ── Paso 2: verificar de a tandas y agregar las que andan ────────────

class _IndiceDeCanales:
    """
    Los canales existentes por nombre normalizado, para reconocer el mismo
    canal escrito distinto ("ES: (HD) DAZN F1" = "DAZN F1 FHD"). Si los dos
    tienen país y no coincide, se toman como canales distintos (la ESPN de
    España no es la de Argentina). Una película nunca se junta con un canal
    en vivo del mismo nombre.
    """

    def __init__(self):
        self.por_nombre = {}
        for canal in Canal.objects.all():
            self.agregar(canal)

    def agregar(self, canal):
        self.por_nombre.setdefault((normalizar(canal.nombre), canal.contenido), []).append(canal)

    def buscar(self, nombre, pais='', contenido=Canal.contenido.field.default):
        for canal in self.por_nombre.get((normalizar(nombre), contenido), []):
            if not (canal.pais and pais and canal.pais != pais):
                return canal
        return None


def _agregar(entrada, resultado, indice, categorias, origen, usuario, ahora):
    """Crea el canal (si no existe) y la fuente. Devuelve True si el canal es nuevo."""
    canal = indice.buscar(entrada.nombre, entrada.pais, entrada.contenido)
    nuevo = canal is None
    if nuevo:
        categoria = None
        if entrada.categoria:
            if entrada.categoria not in categorias:
                categorias[entrada.categoria], _ = Categoria.objects.get_or_create(nombre=entrada.categoria[:80])
            categoria = categorias[entrada.categoria]
        canal = Canal(nombre=entrada.nombre, numero=entrada.numero, logo=entrada.logo, categoria=categoria,
                      tvg_id=entrada.tvg_id, pais=entrada.pais, idioma=entrada.idioma, contenido=entrada.contenido)
        canal.marcar_autor(usuario)
        canal.save()
        indice.agregar(canal)
    elif not canal.logo and entrada.logo:
        canal.logo = entrada.logo   # el canal no tenía logo y esta lista sí lo trae
        canal.save(update_fields=['logo', 'modificado'])

    tipo = (resultado.tipo if resultado and resultado.tipo else entrada.tipo) or 'hls'
    estado = resultado.estado if resultado else Fuente.Estado.SIN_VERIFICAR
    prioridad = (canal.fuentes.aggregate(maximo=Max('prioridad'))['maximo'] or 0) + 1
    user_agent = entrada.user_agent or (resultado.user_agent if resultado else '')
    Fuente.objects.create(
        canal=canal, url=entrada.url, tipo=tipo, prioridad=prioridad, origen=origen[:150],
        user_agent=user_agent, referer=entrada.referer, estado=estado,
        error=resultado.error[:200] if resultado else '', verificada=ahora if resultado else None,
    )

    motivos = ['Canal nuevo.' if nuevo else f'Se sumó como fuente alternativa de "{canal.nombre}".']
    if resultado and resultado.user_agent:
        motivos.append('Anda presentándose como VLC.')
    if resultado and resultado.estado == Fuente.Estado.SIN_VERIFICAR:
        motivos.append(resultado.error or 'No se pudo verificar.')
    elif not resultado:
        motivos.append('Sin verificar.')
    entrada.estado, entrada.motivo, entrada.canal, entrada.tipo = Estado.AGREGADA, ' '.join(motivos), canal, tipo
    return nuevo


def procesar_lote(importacion, verificar=None, tamanio=TAMANIO_LOTE, segundos=SEGUNDOS_POR_LOTE):
    """
    Verifica las próximas `tamanio` entradas pendientes y agrega las que
    funcionan (las que no, quedan como "No funciona" con el motivo). Sin
    `verificar`, las agrega sin probar. Devuelve el avance (ver `progreso`),
    más cuántos canales nuevos se crearon en esta tanda.

    Si otra pestaña ya está procesando esta misma importación, no hace nada
    y devuelve el avance con "ocupada": la pantalla espera y vuelve a pedir.
    """
    canales_nuevos = 0
    with transaction.atomic():
        try:
            Importacion.objects.select_for_update(nowait=True).get(pk=importacion.pk)
        except DatabaseError:
            return {**progreso(importacion), 'ocupada': True, 'canales_nuevos': 0}

        pendientes = list(importacion.entradas.filter(estado=Estado.PENDIENTE).order_by('posicion')[:tamanio])
        indice = _IndiceDeCanales()
        a_verificar = []
        for entrada in pendientes:
            canal = indice.buscar(entrada.nombre, entrada.pais, entrada.contenido)
            if canal is not None and not canal.activo:
                # Lo quitaron a mano: no se vuelve a meter por la ventana
                entrada.estado, entrada.canal = Estado.DESCARTADA, canal
                entrada.motivo = f'El canal "{canal.nombre}" está quitado ({canal.motivo_quitado or "a mano"}).'[:200]
            elif Fuente.objects.filter(url=entrada.url).exists():   # la cargó otra importación mientras tanto
                entrada.estado, entrada.motivo = Estado.REPETIDA, 'Esta dirección ya estaba cargada.'
            else:
                a_verificar.append(entrada)

        resultados = {}
        if verificar and a_verificar:
            hasta = time.monotonic() + segundos if segundos else None
            resultados = verificar(
                {e.url: e.tipo or 'hls' for e in a_verificar},
                cabeceras={e.url: (e.user_agent, e.referer) for e in a_verificar if e.user_agent or e.referer},
                hasta=hasta,
            )

        ahora = timezone.now()
        categorias = {}
        for entrada in a_verificar:
            resultado = resultados.get(entrada.url)
            if verificar and resultado is None:
                continue   # no llegó a probarse: sigue pendiente para la próxima tanda
            if resultado and resultado.estado == Fuente.Estado.CAIDA:
                entrada.estado, entrada.motivo = Estado.CAIDA, resultado.error[:200]
                entrada.tipo = resultado.tipo or entrada.tipo
                continue
            canales_nuevos += _agregar(entrada, resultado, indice, categorias, importacion.archivo,
                                       importacion.usuario, ahora)

        EntradaImportada.objects.bulk_update(pendientes, ['estado', 'motivo', 'canal', 'tipo'])

        if not importacion.entradas.filter(estado=Estado.PENDIENTE).exists():
            importacion.terminada = ahora
            importacion.save(update_fields=['terminada'])
            avance = progreso(importacion)
            registrar(importacion.usuario, Accion.CREAR,
                      f'Terminó de importar "{importacion.archivo}": {avance["agregadas"]} agregada(s), '
                      f'{avance["caidas"]} no funcionan, {avance["descartadas"]} descartada(s), '
                      f'{avance["repetidas"]} ya estaban.', modulo='canales')
    return {**progreso(importacion), 'canales_nuevos': canales_nuevos}


def progreso(importacion):
    """Cuántas hay en cada estado y el porcentaje de avance (sobre las que había que verificar)."""
    por_estado = dict(importacion.entradas.order_by().values_list('estado').annotate(cantidad=Count('pk')))
    pendientes = por_estado.get(Estado.PENDIENTE, 0)
    base = max(importacion.para_verificar, pendientes)
    porcentaje = 100 if not base else round(100 * (base - pendientes) / base)
    return {
        'total': importacion.total,
        'para_verificar': base,
        'verificadas': base - pendientes,
        'pendientes': pendientes,
        'agregadas': por_estado.get(Estado.AGREGADA, 0),
        'caidas': por_estado.get(Estado.CAIDA, 0),
        'descartadas': por_estado.get(Estado.DESCARTADA, 0),
        'repetidas': por_estado.get(Estado.REPETIDA, 0),
        'porcentaje': porcentaje,
        'terminada': pendientes == 0,
    }


def reintentar_caidas(importacion, usuario=None):
    """Las que no funcionaron vuelven a quedar pendientes (a veces es algo del momento)."""
    cantidad = importacion.entradas.filter(estado=Estado.CAIDA).update(estado=Estado.PENDIENTE, motivo='')
    if cantidad:
        importacion.para_verificar, importacion.terminada = cantidad, None
        importacion.save(update_fields=['para_verificar', 'terminada'])
        registrar(usuario, Accion.EDITAR, f'Reintenta {cantidad} canal(es) de "{importacion.archivo}".',
                  modulo='canales')
    return cantidad


def importar_m3u(texto, origen='', usuario=None, verificar=None, **opciones):
    """
    Todo de una vez (consola y pruebas): crea la importación y la procesa
    entera. Nunca pisa lo que ya existe:
      - canal nuevo            -> se crea (con su categoría, logo y número)
      - canal que ya existía   -> la dirección se agrega como fuente alternativa
      - dirección repetida     -> se ignora
      - no funciona            -> no se agrega (queda en el informe de la importación, con el motivo)
    """
    importacion = crear_importacion(texto, origen, usuario, **opciones)
    nuevos = 0
    pendientes_antes = None
    while True:
        avance = procesar_lote(importacion, verificar, segundos=None)
        nuevos += avance['canales_nuevos']
        if avance['terminada'] or avance['pendientes'] == pendientes_antes:   # no avanzó: no insistir
            break
        pendientes_antes = avance['pendientes']
    agregadas = importacion.entradas.filter(estado=Estado.AGREGADA).values('url')
    por_estado = dict(Fuente.objects.filter(url__in=agregadas).order_by().values_list('estado')
                      .annotate(cantidad=Count('pk')))
    return ResultadoImportacion(
        canales_nuevos=nuevos, fuentes_nuevas=avance['agregadas'], repetidas=avance['repetidas'],
        funcionan=por_estado.get(Fuente.Estado.FUNCIONA, 0), caidas=avance['caidas'],
        sin_verificar=por_estado.get(Fuente.Estado.SIN_VERIFICAR, 0), descartadas=avance['descartadas'],
    )


# ── Volver a verificar las fuentes guardadas ─────────────────────────

def aplicar_resultado(fuente, resultado, ahora):
    """Le pone a la fuente lo que dio la verificación (estado, motivo, formato real y User-Agent que anduvo)."""
    fuente.estado, fuente.error, fuente.verificada = resultado.estado, resultado.error[:200], ahora
    if resultado.tipo:
        fuente.tipo = resultado.tipo
    if resultado.user_agent and not fuente.user_agent:
        fuente.user_agent = resultado.user_agent


CAMPOS_DE_VERIFICACION = ['estado', 'error', 'verificada', 'tipo', 'user_agent']


def _fuentes_vigentes():
    return Fuente.objects.filter(canal__eliminado_en__isnull=True)


def verificar_lote_de_fuentes(verificar, desde=0, tamanio=TAMANIO_LOTE, segundos=SEGUNDOS_POR_LOTE, usuario=None):
    """
    Vuelve a probar las próximas `tamanio` fuentes (en orden de id, a partir
    de `desde`) y actualiza su estado. Las caídas que volvieron pasan a
    "funciona" (y la app las vuelve a usar); las que se cayeron dejan de
    usarse. No toca `activa`. Devuelve el avance y `siguiente`: el `desde`
    para la próxima tanda.
    """
    fuentes = list(_fuentes_vigentes().filter(pk__gt=desde).order_by('pk')[:tamanio])
    hasta = time.monotonic() + segundos if segundos else None
    estados = verificar({f.url: f.tipo for f in fuentes},
                        cabeceras={f.url: (f.user_agent, f.referer) for f in fuentes if f.user_agent or f.referer},
                        hasta=hasta)
    ahora = timezone.now()

    resultado = ResultadoVerificacion()
    verificadas = []
    siguiente = desde
    corte = False
    for fuente in fuentes:
        nuevo = estados.get(fuente.url)
        if nuevo is None:
            corte = True   # no llegó: desde acá se sigue en la próxima tanda
            continue
        if not corte:
            siguiente = fuente.pk
        if fuente.estado == Fuente.Estado.CAIDA and nuevo.estado == Fuente.Estado.FUNCIONA:
            resultado.revividas += 1
        elif fuente.estado != Fuente.Estado.CAIDA and nuevo.estado == Fuente.Estado.CAIDA:
            resultado.nuevas_caidas += 1
        aplicar_resultado(fuente, nuevo, ahora)
        _contar(resultado, nuevo.estado)
        verificadas.append(fuente)
    Fuente.objects.bulk_update(verificadas, CAMPOS_DE_VERIFICACION)

    total = _fuentes_vigentes().count()
    terminado = not _fuentes_vigentes().filter(pk__gt=siguiente).exists()
    if terminado:
        registrar(usuario, Accion.EDITAR, 'Volvió a verificar todas las fuentes de los canales.', modulo='canales')
    hechas = _fuentes_vigentes().filter(pk__lte=siguiente).count()
    return {
        'siguiente': siguiente, 'total': total, 'verificadas': hechas, 'terminado': terminado,
        'porcentaje': 100 if not total else round(100 * hechas / total),
        'funcionan': resultado.funcionan, 'caidas': resultado.caidas, 'sin_verificar': resultado.sin_verificar,
        'revividas': resultado.revividas, 'nuevas_caidas': resultado.nuevas_caidas,
    }


def verificar_fuentes_guardadas(verificar, usuario=None):
    """Todas de una vez (consola / cron): tanda tras tanda hasta terminar."""
    total = ResultadoVerificacion()
    desde = 0
    while True:
        avance = verificar_lote_de_fuentes(verificar, desde, segundos=None, usuario=usuario)
        total.sumar(ResultadoVerificacion(**{c: avance[c] for c in (
            'funcionan', 'caidas', 'sin_verificar', 'revividas', 'nuevas_caidas')}))
        if avance['terminado']:
            return total
        desde = avance['siguiente']


def _contar(resultado, estado):
    if estado == Fuente.Estado.FUNCIONA:
        resultado.funcionan += 1
    elif estado == Fuente.Estado.CAIDA:
        resultado.caidas += 1
    else:
        resultado.sin_verificar += 1


# ── Quitar canales / volver a mostrarlos ─────────────────────────────

def quitar_canales(canales, motivo='', usuario=None):
    """Los saca de la app (no los borra). Si vuelven en otra lista, siguen quitados."""
    motivo = (motivo or 'Quitado a mano.').strip()[:200]
    cantidad = canales.filter(activo=True).update(activo=False, motivo_quitado=motivo, modificado=timezone.now(),
                                                   modificado_por=usuario if getattr(usuario, 'pk', None) else None)
    if cantidad:
        registrar(usuario, Accion.EDITAR, f'Quitó {cantidad} canal(es) de la app: {motivo}', modulo='canales')
    return cantidad


def mostrar_canales(canales, usuario=None):
    """Deshace "quitar": vuelven a la app (si tienen alguna fuente que ande)."""
    cantidad = canales.filter(activo=False).update(activo=True, motivo_quitado='', modificado=timezone.now(),
                                                    modificado_por=usuario if getattr(usuario, 'pk', None) else None)
    if cantidad:
        registrar(usuario, Accion.EDITAR, f'Volvió a mostrar {cantidad} canal(es) en la app.', modulo='canales')
    return cantidad


# ── Editar un canal desde el panel ───────────────────────────────────

def guardar_canal(form, fuentes, usuario=None, verificar_url=None):
    """
    Guarda el formulario del canal (CanalForm) y el de sus fuentes
    (FuentesFormSet: prioridad, apagar o borrar). Si se escribió una fuente
    nueva, se crea y se prueba en el momento. Devuelve (canal, fuente_nueva o None).
    """
    with transaction.atomic():
        canal = form.save(commit=False)
        canal.marcar_autor(usuario)
        canal.save()
        fuentes.save()
    nueva = None
    if form.cleaned_data.get('nueva_fuente'):
        nueva = agregar_fuente(canal, form.cleaned_data['nueva_fuente'], verificar_url, usuario)
    registrar(usuario, Accion.EDITAR, f'Editó el canal "{canal.nombre}".', modulo='canales')
    return canal, nueva


def agregar_fuente(canal, url, verificar_url=None, usuario=None):
    """Suma una dirección al canal (al final de la lista) y, si se puede, la prueba."""
    tipo = clasificar.formato(url) or Fuente.Tipo.HLS
    prioridad = (canal.fuentes.aggregate(maximo=Max('prioridad'))['maximo'] or 0) + 1
    fuente = Fuente(canal=canal, url=url[:1000], tipo=tipo, prioridad=prioridad, origen='Agregada a mano')
    if verificar_url:
        aplicar_resultado(fuente, verificar_url(url, tipo), timezone.now())
    fuente.save()
    return fuente


def crear_canal_a_mano(form, url, resultado, user_agent='', referer='', usuario=None):
    """
    Crea un canal con una dirección ya probada en "Probar un link": los
    datos vienen del formulario (CanalNuevoForm) y el estado y formato, de la prueba.
    """
    with transaction.atomic():
        canal = form.save(commit=False)
        canal.marcar_autor(usuario)
        canal.save()
        fuente = Fuente(canal=canal, url=url[:1000], prioridad=1, origen='Agregada a mano',
                        user_agent=user_agent[:300], referer=referer[:500],
                        tipo=clasificar.formato(url) or Fuente.Tipo.HLS)
        aplicar_resultado(fuente, resultado, timezone.now())
        fuente.save()
    registrar(usuario, Accion.CREAR, f'Agregó a mano el canal "{canal.nombre}".', modulo='canales')
    return canal


# ── Limpiar los nombres de los canales que ya estaban ────────────────

def limpiar_nombres(usuario=None):
    """
    Pasa los nombres viejos al formato limpio ("ES: (FHD) DAZN 1" -> "DAZN 1"),
    como se hace al importar. Si al limpiarlo queda igual a otro canal (mismo
    contenido y país compatible), se juntan: las fuentes pasan al que ya
    estaba (quedan como alternativas) y el repetido se da de baja.
    Devuelve (renombrados, juntados).
    """
    renombrados = juntados = 0
    with transaction.atomic():
        indice = _IndiceDeCanales()
        indice.por_nombre = {}
        for canal in Canal.objects.order_by('pk'):
            limpio = clasificar.limpiar_nombre(canal.nombre)[:120]
            igual = indice.buscar(limpio, canal.pais, canal.contenido)
            if igual is not None and igual.pk != canal.pk:
                _juntar(canal, igual, usuario)
                juntados += 1
                continue
            if limpio != canal.nombre:
                canal.nombre = limpio
                canal.marcar_autor(usuario)
                canal.save()
                renombrados += 1
            indice.agregar(canal)
    if renombrados or juntados:
        registrar(usuario, Accion.EDITAR,
                  f'Limpió los nombres de los canales: {renombrados} renombrado(s), {juntados} juntado(s).',
                  modulo='canales')
    return renombrados, juntados


def _juntar(repetido, destino, usuario):
    """Las fuentes de `repetido` pasan a `destino` (al final) y `repetido` se da de baja."""
    ya_tiene = set(destino.fuentes.values_list('url', flat=True))
    prioridad = destino.fuentes.aggregate(maximo=Max('prioridad'))['maximo'] or 0
    for fuente in repetido.fuentes.order_by('prioridad', 'pk'):
        if fuente.url in ya_tiene:
            fuente.delete()
            continue
        prioridad += 1
        fuente.canal, fuente.prioridad = destino, prioridad
        fuente.save(update_fields=['canal', 'prioridad'])
    if not destino.logo and repetido.logo:
        destino.logo = repetido.logo
        destino.save(update_fields=['logo', 'modificado'])
    repetido.eliminar(usuario)


# ── Avisos de la app ─────────────────────────────────────────────────

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
    aplicar_resultado(fuente, resultado, timezone.now())
    fuente.save(update_fields=CAMPOS_DE_VERIFICACION)
    if estado_anterior != Fuente.Estado.CAIDA and fuente.estado == Fuente.Estado.CAIDA:
        registrar(None, Accion.SISTEMA, f'La fuente de {fuente.canal} se cayó (avisó la app): {fuente.error}',
                  modulo='canales')
    return fuente.estado


# Lo que la app manda al avisar una falla ("motivo"), en palabras del panel.
MOTIVOS_DE_LOS_APARATOS = {
    'formato': 'el aparato no puede leer el formato del video',
    'rechazo': 'el servidor de la señal rechaza al aparato',
    'tiempo': 'tarda demasiado en arrancar',
    'conexion': 'no se puede conectar con la señal',
    'error': 'da error al reproducir',
}
# Cuántos avisos (de aparatos distintos, o del mismo pero separados por
# ESPERA_ENTRE_AVISOS) en un día hacen falta para ocultarla.
AVISOS_PARA_OCULTAR = 3
ESPERA_ENTRE_AVISOS = 30 * 60   # segundos


def registrar_falla_en_aparato(fuente, quien, motivo, detalle=''):
    """
    Cuenta un aviso de falla de un aparato (`quien`: algo que lo identifique,
    ej. el id de su sesión). Con AVISOS_PARA_OCULTAR en un día, la fuente se
    oculta DIAS_OCULTA días aunque al servidor le ande: se ve que en los
    aparatos no se reproduce. El mismo aparato cuenta una vez cada
    ESPERA_ENTRE_AVISOS (reintentar diez veces seguidas no la oculta).
    Devuelve True si quedó oculta.
    """
    if fuente.oculta_por_aparatos:
        return True
    if not cache.add(f'falla_aparato:{fuente.pk}:{quien}', True, timeout=ESPERA_ENTRE_AVISOS):
        return False
    ahora = timezone.now()
    if fuente.primer_aviso is None or ahora - fuente.primer_aviso > timedelta(days=1):
        fuente.avisos_de_aparatos, fuente.primer_aviso = 0, ahora
    fuente.avisos_de_aparatos += 1
    texto = MOTIVOS_DE_LOS_APARATOS.get(motivo, MOTIVOS_DE_LOS_APARATOS['error'])
    fuente.falla_en_aparatos = (f'{texto}: {detalle}' if detalle else texto)[:200]
    if fuente.avisos_de_aparatos >= AVISOS_PARA_OCULTAR:
        fuente.oculta_desde = ahora
        registrar(None, Accion.SISTEMA,
                  f'Se ocultó una fuente de {fuente.canal}: no se reproduce en los aparatos ({texto}).',
                  modulo='canales')
    fuente.save(update_fields=['avisos_de_aparatos', 'primer_aviso', 'falla_en_aparatos', 'oculta_desde'])
    return fuente.oculta_desde is not None and fuente.oculta_por_aparatos

