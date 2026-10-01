from django import forms

from herramientas.formularios import EstiloBootstrapMixin

from .models import EstadoMantenimiento


class EstadoMantenimientoForm(EstiloBootstrapMixin, forms.ModelForm):

    class Meta:
        model = EstadoMantenimiento
        fields = ['activo', 'mensaje', 'vuelve_aprox']
        labels = {'activo': 'Activar el modo mantenimiento'}
        widgets = {
            'mensaje': forms.Textarea(attrs={
                'rows': 2, 'placeholder': 'Estamos haciendo mejoras en el sistema. Volvé a intentar en unos minutos.',
            }),
        }
