from django.test import TestCase

from herramientas.tests.app_pruebas.models import Cosa, Hija
from usuarios.models import Usuario


class ModeloBaseTests(TestCase):

    def setUp(self):
        self.usuario = Usuario.objects.create_user('juan', None, 'x')
        self.otro = Usuario.objects.create_user('ana', None, 'x')

    def test_autor_y_fechas(self):
        cosa = Cosa(nombre='A')
        cosa.marcar_autor(self.usuario)
        cosa.save()
        self.assertEqual(cosa.creado_por, self.usuario)
        self.assertEqual(cosa.modificado_por, self.usuario)
        self.assertIsNotNone(cosa.creado)

        cosa.marcar_autor(self.otro)
        cosa.save()
        cosa.refresh_from_db()
        self.assertEqual(cosa.creado_por, self.usuario)   # no cambia
        self.assertEqual(cosa.modificado_por, self.otro)

    def test_baja_logica_y_restaurar(self):
        cosa = Cosa.objects.create(nombre='A')
        cosa.eliminar(self.usuario)
        self.assertFalse(Cosa.objects.filter(pk=cosa.pk).exists())
        self.assertTrue(Cosa.todos.filter(pk=cosa.pk).exists())
        self.assertTrue(Cosa.todos.get(pk=cosa.pk).esta_eliminado)
        self.assertEqual(Cosa.todos.get(pk=cosa.pk).eliminado_por, self.usuario)

        cosa.restaurar(self.otro)
        self.assertTrue(Cosa.objects.filter(pk=cosa.pk).exists())

    def test_lo_que_depende_sigue_viendo_al_eliminado(self):
        cosa = Cosa.objects.create(nombre='A')
        hija = Hija.objects.create(cosa=cosa)
        cosa.eliminar()
        hija = Hija.objects.get(pk=hija.pk)
        self.assertEqual(hija.cosa.nombre, 'A')

    def test_usuario_anonimo_no_se_guarda_como_autor(self):
        from django.contrib.auth.models import AnonymousUser
        cosa = Cosa(nombre='A')
        cosa.marcar_autor(AnonymousUser())
        cosa.save()
        self.assertIsNone(cosa.creado_por)
