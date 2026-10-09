"""
Sin subcategorías (eran de la 0013) y los nombres de categoría, únicos dentro
de cada sección (la 0015 ya separó las compartidas).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('canales', '0015_separar_categorias_por_seccion'),
    ]

    operations = [
        migrations.RemoveField(model_name='categoria', name='padre'),
        migrations.AddConstraint(
            model_name='categoria',
            constraint=models.UniqueConstraint(condition=models.Q(('eliminado_en__isnull', True)),
                                               fields=('contenido', 'nombre'),
                                               name='categoria_nombre_unico_por_seccion'),
        ),
    ]
