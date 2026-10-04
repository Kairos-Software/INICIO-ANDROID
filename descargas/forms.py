from django import forms

from herramientas.formularios import EstiloBootstrapMixin

from .models import VersionApp

TAMANIO_MAXIMO = 200 * 1024 * 1024   # 200 MB (una APK de Flutter pesa ~20-60 MB)


class VersionAppForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = VersionApp
        fields = ['version', 'archivo', 'notas']
        widgets = {
            'archivo': forms.FileInput(attrs={'accept': '.apk'}),
            'notas': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_archivo(self):
        archivo = self.cleaned_data['archivo']
        if not archivo.name.lower().endswith('.apk'):
            raise forms.ValidationError('Tiene que ser un archivo .apk.')
        if archivo.size > TAMANIO_MAXIMO:
            raise forms.ValidationError('El archivo pesa más de 200 MB.')
        # Una APK es un ZIP: siempre empieza con "PK". Evita subir cualquier cosa renombrada.
        inicio = archivo.read(4)
        archivo.seek(0)
        if inicio != b'PK\x03\x04':
            raise forms.ValidationError('El archivo no es una APK válida.')
        return archivo

    def clean_version(self):
        version = self.cleaned_data['version'].strip()
        if VersionApp.objects.filter(version=version).exists():
            raise forms.ValidationError('Ya se subió esa versión. Cambiá el número en pubspec.yaml y volvé a compilar.')
        return version
