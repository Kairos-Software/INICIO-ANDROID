"""Subir y descargar la APK. Los archivos van a una carpeta temporal (no a media/)."""

import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from descargas.models import VersionApp
from usuarios.models import Rol, Usuario

APK = b'PK\x03\x04' + b'contenido de mentira' * 10
CARPETA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=CARPETA)
class DescargasTests(TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(CARPETA, ignore_errors=True)

    def setUp(self):
        self.admin = Usuario.objects.create_superuser('admin', 'admin@test.com', 'x')
        self.revendedor = Usuario.objects.create_user('juan', None, 'x', rol=Rol.objects.create(nombre='Revendedor'))

    def subir(self, version='1.0.0', contenido=APK, nombre='app-release.apk'):
        return self.client.post(reverse('descargas:pagina'), {
            'version': version, 'archivo': SimpleUploadedFile(nombre, contenido), 'notas': 'Primera'})

    def test_publicar_y_descargar_sin_sesion(self):
        self.client.force_login(self.admin)
        self.subir()
        self.subir('1.0.1')
        self.client.logout()
        respuesta = self.client.get('/descargar/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/vnd.android.package-archive')
        self.assertIn('KairosTV-1.0.1.apk', respuesta['Content-Disposition'])   # siempre la última
        self.assertEqual(b''.join(respuesta.streaming_content), APK)

    def test_sin_versiones_da_404(self):
        self.assertEqual(self.client.get('/descargar/').status_code, 404)

    def test_rechaza_lo_que_no_es_apk(self):
        self.client.force_login(self.admin)
        self.assertContains(self.subir(nombre='foto.png'), 'Tiene que ser un archivo .apk.')
        self.assertContains(self.subir(contenido=b'hola'), 'no es una APK válida')
        self.subir()
        self.assertContains(self.subir(), 'Ya se subió esa versión')
        self.assertEqual(VersionApp.objects.count(), 1)

    def test_ocultar_una_version(self):
        self.client.force_login(self.admin)
        self.subir()
        self.subir('1.0.1')
        nueva = VersionApp.objects.get(version='1.0.1')
        self.client.post(reverse('descargas:cambiar_publicada', args=[nueva.pk]))
        self.client.logout()
        self.assertIn('1.0.0', self.client.get('/descargar/')['Content-Disposition'])
        self.assertEqual(self.client.get(reverse('descargas:descargar_version', args=[nueva.pk])).status_code, 404)

    def test_el_revendedor_ve_la_pagina_pero_no_publica(self):
        self.client.force_login(self.revendedor)
        respuesta = self.client.get(reverse('descargas:pagina'))
        self.assertContains(respuesta, 'Cómo instalarla')
        self.assertNotContains(respuesta, 'Publicar una versión nueva')
        self.assertEqual(self.subir().status_code, 403)

    def test_la_pagina_pide_sesion(self):
        self.assertEqual(self.client.get(reverse('descargas:pagina')).status_code, 302)

    def test_la_api_dice_cual_es_la_ultima_version(self):
        """GET /api/v1/app/: lo que consulta la app para avisar que hay una nueva (sin sesión)."""
        self.assertEqual(self.client.get('/api/v1/app/').json(), {'version': None})
        self.client.force_login(self.admin)
        self.subir()
        self.subir('1.1.0')
        nueva = VersionApp.objects.get(version='1.1.0')
        self.client.logout()
        datos = self.client.get('/api/v1/app/').json()
        self.assertEqual(datos['version'], '1.1.0')
        self.assertEqual(datos['notas'], 'Primera')
        self.assertTrue(datos['descarga'].endswith(f'/descargar/{nueva.pk}/'))
        # Si se oculta, vuelve a anunciar la anterior
        nueva.publicada = False
        nueva.save()
        self.assertEqual(self.client.get('/api/v1/app/').json()['version'], '1.0.0')
