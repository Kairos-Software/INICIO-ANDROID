"""
Utilidades para formularios de Django, reutilizables en cualquier app.

    from herramientas.formularios import EstiloBootstrapMixin, CampoFecha

    class ClienteForm(EstiloBootstrapMixin, forms.ModelForm):
        ...
"""

from django import forms


class CampoFecha(forms.DateInput):
    """Selector de fecha nativo del navegador (<input type="date">)."""

    input_type = 'date'

    def __init__(self, attrs=None):
        # El input type=date necesita el formato ISO (AAAA-MM-DD)
        super().__init__(attrs=attrs, format='%Y-%m-%d')


class EstiloBootstrapMixin:
    """
    Agrega a cada campo la clase de Bootstrap que le corresponde
    (form-control, form-select, form-check-input) y marca con is-invalid
    los campos con error. Así los templates no tienen que hacerlo a mano.
    """

    TEXTO_OPCION_VACIA = 'Elegir…'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nombre, campo in self.fields.items():
            widget = campo.widget

            # La opción vacía de los desplegables viene en inglés
            # ("Select an option"): se reemplaza por un texto propio.
            if isinstance(campo, forms.ChoiceField) and not isinstance(campo, forms.ModelChoiceField):
                opciones = list(campo.choices)
                if opciones and opciones[0][0] == '':
                    campo.choices = [('', self.TEXTO_OPCION_VACIA)] + opciones[1:]

            if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect, forms.CheckboxSelectMultiple)):
                clase = 'form-check-input'
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                clase = 'form-select'
            else:
                clase = 'form-control'
            clases = [widget.attrs.get('class', ''), clase]
            if self.is_bound and nombre in self.errors:
                clases.append('is-invalid')
            widget.attrs['class'] = ' '.join(c for c in clases if c)
