"""
Traer de YouTube como UNA serie (Masha y el Oso, Pocoyó...): la importación
recuerda el nombre de la serie y la temporada para numerar los capítulos.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('canales', '0016_sin_subcategorias'),
    ]

    operations = [
        migrations.AddField(
            model_name='importacion',
            name='serie',
            field=models.CharField(blank=True, max_length=90, verbose_name='serie'),
        ),
        migrations.AddField(
            model_name='importacion',
            name='temporada',
            field=models.PositiveSmallIntegerField(default=1),
        ),
    ]
