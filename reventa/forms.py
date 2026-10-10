from django import forms
from django.contrib.auth.password_validation import validate_password

from herramientas.formularios import EstiloBootstrapMixin
from usuarios.models import Usuario

from .models import Cliente, Paquete, Revendedor


class RevendedorNuevoForm(EstiloBootstrapMixin, forms.Form):
    """Crea el usuario del panel y su perfil de revendedor de una sola vez."""

    username = forms.CharField(label='Usuario (para entrar al panel)', max_length=150)
    first_name = forms.CharField(label='Nombre', max_length=150)
    last_name = forms.CharField(label='Apellido', max_length=150, required=False)
    telefono = forms.CharField(label='Teléfono', max_length=30, required=False)
    password = forms.CharField(label='Contraseña inicial', widget=forms.PasswordInput(render_value=True),
                               help_text='Se le va a pedir que la cambie al entrar por primera vez.')
    precio_pantalla = forms.DecimalField(label='Precio por dispositivo', min_value=0, decimal_places=2, initial=0,
                                         help_text='Lo que cobra cada 30 días por dispositivo (lo puede cambiar).')

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if Usuario.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Ya existe un usuario con ese nombre.')
        return username

    def clean_password(self):
        password = self.cleaned_data['password']
        validate_password(password)
        return password


class PrecioForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Revendedor
        fields = ['precio_pantalla']


class CreditosForm(EstiloBootstrapMixin, forms.Form):
    """Regalar (cantidad > 0) o ajustar (+/−) créditos."""

    cantidad = forms.IntegerField(label='Cantidad')
    detalle = forms.CharField(label='Motivo / nota', max_length=200, required=False)


class PaqueteForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Paquete
        fields = ['nombre', 'creditos', 'precio', 'activo']

    def clean_creditos(self):
        creditos = self.cleaned_data['creditos']
        if creditos < 1:
            raise forms.ValidationError('Tiene que tener al menos 1 crédito.')
        return creditos


class ElegirPaqueteForm(EstiloBootstrapMixin, forms.Form):
    paquete = forms.ModelChoiceField(label='Paquete', queryset=Paquete.objects.filter(activo=True))


class ClienteForm(EstiloBootstrapMixin, forms.ModelForm):
    """Para el administrador aparece además el campo revendedor (al crear)."""

    class Meta:
        model = Cliente
        fields = ['revendedor', 'nombre', 'telefono', 'notas', 'suspendido']
        widgets = {'notas': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, elegir_revendedor=False, **kwargs):
        # Los campos que no van se sacan de la clase antes de armar el formulario
        # (así ni se dibujan ni se validan). Lo que se ajusta después de
        # super().__init__ (la lista de revendedores, si es obligatorio) también
        # cuenta al validar: EstiloBootstrapMixin valida recién en full_clean.
        instancia = kwargs.get('instance')
        sacar = set()
        if not elegir_revendedor:
            sacar.add('revendedor')
        if instancia is None or instancia.pk is None:
            sacar.add('suspendido')   # recién creado no tiene sentido
        self.base_fields = {nombre: campo for nombre, campo in type(self).base_fields.items() if nombre not in sacar}
        super().__init__(*args, **kwargs)
        if elegir_revendedor:
            campo = self.fields['revendedor']
            campo.queryset = Revendedor.objects.select_related('usuario')
            campo.required = False
            campo.empty_label = '— Cliente directo (sin revendedor, no gasta créditos) —'



class RenovarForm(EstiloBootstrapMixin, forms.Form):
    """Activar o renovar: cuántos dispositivos por los próximos 30 días (1 crédito cada uno)."""

    dispositivos = forms.IntegerField(label='Dispositivos', min_value=1, max_value=20, initial=1,
                                      help_text='Cada dispositivo usa 1 crédito por 30 días.')
    monto_cobrado = forms.DecimalField(label='Monto cobrado', min_value=0, decimal_places=2, required=False,
                                       help_text='Vacío = el precio sugerido (precio por dispositivo × dispositivos).')
