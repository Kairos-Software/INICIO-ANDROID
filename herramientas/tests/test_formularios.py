"""EstiloBootstrapMixin: las clases de Bootstrap, y que valide con el formulario ya armado."""

from django import forms
from django.test import SimpleTestCase

from herramientas.formularios import EstiloBootstrapMixin


class ConOpcionesArmadasDespues(EstiloBootstrapMixin, forms.Form):
    """Como los formularios del panel que llenan un desplegable con lo que hay en la base."""
    nombre = forms.CharField()
    color = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['color'].choices = [('', 'Ninguno'), ('rojo', 'Rojo')]


class EstiloBootstrapTests(SimpleTestCase):

    def test_valida_con_las_opciones_que_arma_el_formulario(self):
        # Antes validaba dentro de __init__, con el desplegable todavía vacío: "rojo" salía "no válido"
        form = ConOpcionesArmadasDespues({'nombre': 'x', 'color': 'rojo'})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(ConOpcionesArmadasDespues({'nombre': 'x', 'color': 'verde'}).is_valid())

    def test_marca_los_campos_con_error(self):
        form = ConOpcionesArmadasDespues({'nombre': '', 'color': ''})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.fields['nombre'].widget.attrs['class'], 'form-control is-invalid')
        self.assertEqual(form.fields['color'].widget.attrs['class'], 'form-select')
        form.full_clean()   # validar dos veces no repite la marca
        self.assertEqual(form.fields['nombre'].widget.attrs['class'], 'form-control is-invalid')
