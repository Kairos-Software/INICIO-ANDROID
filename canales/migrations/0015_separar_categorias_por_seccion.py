"""
Separa por sección las categorías compartidas (ver la 0014): la original queda
en la sección donde tiene más, y para cada otra sección se crea una igual
(mismo nombre, orden y otros nombres) con lo de esa sección. Las vacías quedan
en "En vivo"... salvo que su nombre diga película/serie.

Va sola: PostgreSQL no deja cambiar la tabla en la misma migración en que se
movieron datos.
"""

from django.db import migrations


def separar_por_seccion(apps, schema_editor):
    Categoria = apps.get_model('canales', 'Categoria')
    Canal = apps.get_model('canales', 'Canal')
    for categoria in Categoria.objects.filter(eliminado_en__isnull=True):
        cuantos = {}
        for contenido in Canal.objects.filter(categoria=categoria, eliminado_en__isnull=True).values_list(
                'contenido', flat=True):
            cuantos[contenido] = cuantos.get(contenido, 0) + 1
        if not cuantos:
            nombre = categoria.nombre.lower()
            categoria.contenido = 'serie' if 'serie' in nombre else ('pelicula' if 'pel' in nombre else 'vivo')
            categoria.save(update_fields=['contenido'])
            continue
        secciones = sorted(cuantos, key=lambda c: -cuantos[c])
        categoria.contenido = secciones[0]
        categoria.save(update_fields=['contenido'])
        for contenido in secciones[1:]:
            copia = Categoria.objects.create(nombre=categoria.nombre, contenido=contenido, orden=categoria.orden,
                                             otros_nombres=categoria.otros_nombres)
            Canal.objects.filter(categoria=categoria, contenido=contenido).update(categoria=copia)


class Migration(migrations.Migration):

    dependencies = [
        ('canales', '0014_categorias_por_seccion'),
    ]

    operations = [
        migrations.RunPython(separar_por_seccion, migrations.RunPython.noop),
    ]
