"""
Estima el idioma (y el país, si no lo tenía) de los canales que ya estaban
cargados antes de que existiera el campo. Los nuevos lo traen al importarse.
"""

from django.db import migrations


def estimar(apps, schema_editor):
    from canales.clasificar import idioma_y_pais

    Canal = apps.get_model('canales', 'Canal')
    canales = list(Canal.objects.select_related('categoria'))
    for canal in canales:
        canal.idioma, pais = idioma_y_pais(
            canal.nombre, canal.categoria.nombre if canal.categoria else '', canal.pais, canal.tvg_id)
        canal.pais = canal.pais or pais
    Canal.objects.bulk_update(canales, ['idioma', 'pais'], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ('canales', '0004_importaciones_y_formatos'),
    ]

    operations = [
        migrations.RunPython(estimar, migrations.RunPython.noop),
    ]
