"""
Modelos que solo existen en la base de pruebas (la app se instala únicamente
al correr `manage.py test`, ver proyecto/settings.py). Sirven para probar
herramientas/modelos.py con un modelo real.
"""

from django.db import models

from herramientas.modelos import ModeloBase


class Cosa(ModeloBase):
    nombre = models.CharField(max_length=50)


class Hija(models.Model):
    cosa = models.ForeignKey(Cosa, on_delete=models.CASCADE, related_name='hijas')
