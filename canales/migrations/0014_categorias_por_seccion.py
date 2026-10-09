"""
Cada categoría pasa a ser de UNA sección (En vivo, Películas o Series): acá
se agrega la columna. La 0015 separa las que estaban compartidas y la 0016
saca las subcategorías (la 0013: no era lo que se buscaba).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('canales', '0013_subcategorias'),
    ]

    operations = [
        migrations.RemoveConstraint(model_name='categoria', name='categoria_nombre_unico'),
        migrations.AddField(
            model_name='categoria',
            name='contenido',
            field=models.CharField(choices=[('vivo', 'En vivo'), ('pelicula', 'Película'), ('serie', 'Serie')],
                                   db_index=True, default='vivo', max_length=10, verbose_name='sección'),
        ),
    ]
