from django import forms

from herramientas.formularios import EstiloBootstrapMixin

from .m3u import leer_m3u

TAMANIO_MAXIMO = 5 * 1024 * 1024   # 5 MB: una lista de miles de canales pesa menos de 1 MB


class ImportarListaForm(EstiloBootstrapMixin, forms.Form):
    archivo = forms.FileField(
        label='Lista de canales',
        help_text='Archivo .m3u o .m3u8 (máximo 5 MB).',
        widget=forms.FileInput(attrs={'accept': '.m3u,.m3u8'}),
    )

    def clean_archivo(self):
        archivo = self.cleaned_data['archivo']
        if not archivo.name.lower().endswith(('.m3u', '.m3u8')):
            raise forms.ValidationError('Tiene que ser un archivo .m3u o .m3u8.')
        if archivo.size > TAMANIO_MAXIMO:
            raise forms.ValidationError('El archivo pesa más de 5 MB.')
        texto = archivo.read().decode('utf-8', errors='replace')
        if not leer_m3u(texto):
            raise forms.ValidationError('No se encontró ningún canal en el archivo. ¿Es una lista M3U?')
        self.texto = texto
        return archivo
