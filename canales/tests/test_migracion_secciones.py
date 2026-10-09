"""Las migraciones 0014 a 0016: separa por sección las categorías compartidas y saca las subcategorías, sin perder nada."""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class SepararPorSeccionTests(TransactionTestCase):

    antes = [('canales', '0013_subcategorias')]
    despues = [('canales', '0016_sin_subcategorias')]

    def _migrar(self, destino):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(destino)
        return executor.loader.project_state(destino).apps

    def tearDown(self):
        self._migrar(MigrationExecutor(connection).loader.graph.leaf_nodes())

    def test_separa_las_compartidas_y_aplana_las_subcategorias(self):
        apps = self._migrar(self.antes)
        Categoria = apps.get_model('canales', 'Categoria')
        Canal = apps.get_model('canales', 'Canal')
        infantil = Categoria.objects.create(nombre='Infantil', orden=3, otros_nombres='Kids')
        series_infantiles = Categoria.objects.create(nombre='Series Infantiles')
        pocoyo = Categoria.objects.create(nombre='Pocoyo', padre=series_infantiles)
        Categoria.objects.create(nombre='Películas de terror')   # vacía
        for nombre in ('Zenón', 'Pakapaka'):
            Canal.objects.create(nombre=nombre, contenido='vivo', categoria=infantil)
        Canal.objects.create(nombre='Toy Story', contenido='pelicula', categoria=infantil)
        for n in range(3):
            Canal.objects.create(nombre=f'Video {n}', contenido='serie', categoria=pocoyo)

        apps = self._migrar(self.despues)
        Categoria = apps.get_model('canales', 'Categoria')
        Canal = apps.get_model('canales', 'Canal')
        secciones = sorted(Categoria.objects.values_list('nombre', 'contenido'))
        self.assertEqual(secciones, [('Infantil', 'pelicula'), ('Infantil', 'vivo'), ('Películas de terror', 'pelicula'),
                                     ('Pocoyo', 'serie'), ('Series Infantiles', 'serie')])
        # Cada cosa quedó en la categoría de su sección, con el mismo nombre
        for canal in Canal.objects.select_related('categoria'):
            self.assertEqual(canal.categoria.contenido, canal.contenido, canal.nombre)
        self.assertEqual(Canal.objects.get(nombre='Toy Story').categoria.otros_nombres, 'Kids')
        self.assertEqual(Canal.objects.filter(categoria__nombre='Pocoyo').count(), 3)
