"""
Las secciones de la app: las tres fijas (En vivo, Películas, Series) y las
que se crean desde el panel (Música, Radio...; modelo Seccion).

    secciones.todas()            -> [('vivo', 'En vivo'), ('pelicula', 'Películas'), ('serie', 'Series'), ('musica', 'Música')]
    secciones.nombre('musica')   -> 'Música'
    secciones.forma('musica')    -> 'pelicula'   (a demanda; 'vivo' para una radio)
    secciones.es_valida('radio') -> True
    secciones.crear('Música', 'pelicula', 'musica', usuario) -> Seccion (clave 'musica')

Lo que está en una sección guarda su clave en `contenido` (Canal, Categoria,
EntradaImportada). La FORMA dice cómo se comporta: una sección nueva "a
demanda" funciona como Películas (se elige un video y se ve de principio a
fin) y una "en vivo", como En vivo (radios o canales que transmiten ahora).
Las series no van en secciones nuevas: necesitan temporadas y capítulos.
"""

import re

from django.db import transaction

from actividad.models import Accion
from actividad.registro import registrar

from .clasificar import sin_acentos
from .models import Canal, Categoria, Contenido, Seccion

FIJAS = {Contenido.VIVO: 'En vivo', Contenido.PELICULA: 'Películas', Contenido.SERIE: 'Series'}


class NoSePuede(Exception):
    """Algo que no se puede hacer con las secciones (el mensaje se le muestra al usuario)."""


def nuevas():
    """Las secciones creadas desde el panel, en el orden del menú."""
    return list(Seccion.objects.order_by('orden', 'nombre'))


def todas():
    """[(clave, nombre)]: primero las fijas y después las nuevas."""
    return [*FIJAS.items(), *((s.clave, s.nombre) for s in nuevas())]


def nombre(clave):
    if clave in FIJAS:
        return FIJAS[clave]
    seccion = Seccion.objects.filter(clave=clave).first()
    return seccion.nombre if seccion else ''


def forma(clave):
    """'vivo', 'pelicula' o 'serie' ('' si no existe)."""
    if clave in FIJAS:
        return clave
    seccion = Seccion.objects.filter(clave=clave).first()
    return seccion.forma if seccion else ''


def es_valida(clave):
    return clave in FIJAS or Seccion.objects.filter(clave=clave).exists()


def es_nueva(clave):
    return bool(clave) and clave not in FIJAS and Seccion.objects.filter(clave=clave).exists()


def _clave_para(texto):
    """'Música 80s' -> 'musica80s' (sin repetir otra ni las fijas)."""
    base = re.sub(r'[^a-z0-9]', '', sin_acentos(texto).lower())[:8] or 'seccion'
    usadas = set(Seccion.todos.values_list('clave', flat=True)) | set(FIJAS)
    clave, numero = base, 2
    while clave in usadas:
        clave = f'{base[:8]}{numero}'
        numero += 1
    return clave


def _nombre_limpio(texto):
    texto = ' '.join((texto or '').split())[:30]
    if not texto:
        raise NoSePuede('Escribí el nombre de la sección (por ejemplo, Música).')
    return texto


def _repetida(texto, menos=None):
    comparable = sin_acentos(texto).lower()
    if comparable in {sin_acentos(n).lower() for n in FIJAS.values()} | {'pelicula', 'serie', 'vivo'}:
        return True
    otras = Seccion.objects.exclude(pk=getattr(menos, 'pk', None))
    return any(sin_acentos(s.nombre).lower() == comparable for s in otras)


def crear(texto, forma_, icono=Seccion.Icono.OTRO, usuario=None):
    texto = _nombre_limpio(texto)
    if forma_ not in Seccion.Forma.values:
        raise NoSePuede('Elegí si es en vivo (radios, canales) o a demanda (videos que se eligen).')
    if _repetida(texto):
        raise NoSePuede(f'Ya hay una sección "{texto}".')
    seccion = Seccion(nombre=texto, forma=forma_, clave=_clave_para(texto),
                      icono=icono if icono in Seccion.Icono.values else Seccion.Icono.OTRO,
                      orden=Seccion.objects.count() + 1)
    seccion.marcar_autor(usuario)
    seccion.save()
    registrar(usuario, Accion.CREAR, f'Creó la sección "{seccion}" ({seccion.get_forma_display()}).',
              objeto=seccion, modulo='canales')
    return seccion


def editar(seccion, texto, icono, orden, usuario=None):
    """Nombre, ícono y orden (la clave y la forma no cambian: lo que tiene sigue igual)."""
    texto = _nombre_limpio(texto)
    if _repetida(texto, menos=seccion):
        raise NoSePuede(f'Ya hay una sección "{texto}".')
    seccion.nombre = texto
    if icono in Seccion.Icono.values:
        seccion.icono = icono
    seccion.orden = max(0, int(orden or 0))
    seccion.marcar_autor(usuario)
    seccion.save()
    registrar(usuario, Accion.EDITAR, f'Editó la sección "{seccion}".', objeto=seccion, modulo='canales')
    return seccion


@transaction.atomic
def borrar(seccion, usuario=None, con_contenido=False):
    """
    La borra. Si tiene algo cargado, solo con `con_contenido` (se borra todo
    lo que tiene, sus categorías incluidas). Devuelve cuántos se borraron.
    """
    from .organizar import eliminar_contenido   # (organizar usa este módulo)
    canales = Canal.objects.filter(contenido=seccion.clave)
    cantidad = canales.count()
    if cantidad and not con_contenido:
        raise NoSePuede(f'"{seccion}" tiene {cantidad} cargado(s): borrala "con todo lo que tiene", o pasá eso '
                        f'a otra sección antes.')
    if cantidad:
        eliminar_contenido(canales, usuario)
    for categoria in Categoria.objects.filter(contenido=seccion.clave):
        categoria.eliminar(usuario)
    seccion.eliminar(usuario)
    registrar(usuario, Accion.ELIMINAR, f'Borró la sección "{seccion}"'
              + (f' con {cantidad} cargado(s).' if cantidad else '.'), modulo='canales')
    return cantidad
