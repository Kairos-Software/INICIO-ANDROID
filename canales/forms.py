import zipfile

from django import forms
from django.core.validators import URLValidator

from herramientas.formularios import EstiloBootstrapMixin

from . import organizar
from .m3u import leer_m3u
from .models import Canal, Categoria, Contenido, Fuente

# Una lista con películas y series (miles de entradas) puede pesar varios MB.
# OJO: nginx también tiene que aceptarlo (client_max_body_size en despliegue/nginx).
TAMANIO_MAXIMO = 20 * 1024 * 1024


def _texto_del_archivo(archivo):
    """El texto de la lista. Si es un .zip, el de la primera lista .m3u/.m3u8 que tenga adentro."""
    if archivo.name.lower().endswith('.zip'):
        try:
            with zipfile.ZipFile(archivo) as comprimido:
                for nombre in comprimido.namelist():
                    if nombre.lower().endswith(('.m3u', '.m3u8')):
                        with comprimido.open(nombre) as adentro:
                            return adentro.read(TAMANIO_MAXIMO * 3).decode('utf-8', errors='replace')
        except zipfile.BadZipFile:
            raise forms.ValidationError('El .zip está dañado.')
        raise forms.ValidationError('El .zip no tiene ninguna lista .m3u o .m3u8 adentro.')
    return archivo.read().decode('utf-8', errors='replace')


# ── Importar directo en una categoría (listas M3U y YouTube) ──

def _opciones_de_categorias(vacia):
    """Las categorías para elegir, con las subcategorías debajo de su principal ("— Rock")."""
    from .consultas import categorias_en_arbol
    return [('', vacia)] + [(str(c.pk), f'{"— " if nivel else ""}{c.nombre}') for c, nivel in categorias_en_arbol()]


def _campo_categoria_nueva():
    return forms.CharField(label='O una categoría nueva', max_length=80, required=False,
                           help_text='Si escribís acá, se crea (o se usa la que ya se llame así).')


def _nombre_de_la_categoria(datos):
    """La categoría elegida para todo lo importado: su nombre ('' = la que diga cada entrada)."""
    nueva = ' '.join((datos.get('categoria_nueva') or '').split())
    if nueva:
        return nueva
    elegida = Categoria.objects.filter(pk=datos.get('categoria_destino') or 0).first()
    return elegida.nombre if elegida else ''


class EditarDesdeOrganizarForm(forms.Form):
    """La edición rápida de "Organizar contenido" (la categoría se lee aparte: views._categoria_elegida)."""
    nombre = forms.CharField(max_length=120)
    logo = forms.URLField(max_length=500, required=False)
    numero = forms.CharField(max_length=10, required=False)
    contenido = forms.ChoiceField(choices=Contenido.choices, required=False)
    activo = forms.BooleanField(required=False)


class TraerDeYoutubeForm(EstiloBootstrapMixin, forms.Form):
    """Traer las películas de un canal oficial de YouTube (canales/youtube.py)."""
    url = forms.CharField(
        label='Link del canal de YouTube', max_length=300,
        help_text='Ej: https://www.youtube.com/@MovieCentralEspanol. Solo canales OFICIALES, del dueño de lo que '
                  'suben (con la tilde de verificado).',
        widget=forms.TextInput(attrs={'placeholder': 'https://www.youtube.com/@canal', 'inputmode': 'url'}),
    )
    categoria_destino = forms.ChoiceField(
        label='Categoría', required=False,
        help_text='Sin elegir: cada película va según el género que dice su título (Acción, Terror...).',
    )
    categoria_nueva = _campo_categoria_nueva()
    minimo_minutos = forms.IntegerField(
        label='Solo videos de al menos (minutos)', min_value=1, max_value=600, initial=60,
        help_text='Saca avances, clips y Shorts. Películas: 60. Dibujos: 20.',
    )
    solo_espanol = forms.BooleanField(label='Descartar los que dicen estar en inglés', required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria_destino'].choices = _opciones_de_categorias('Según el género de cada título')

    def categoria(self):
        return _nombre_de_la_categoria(self.cleaned_data)


class ImportarListaForm(EstiloBootstrapMixin, forms.Form):
    archivo = forms.FileField(
        label='Lista de canales',
        help_text='Archivo .m3u, .m3u8 o un .zip que la contenga (máximo 20 MB).',
        widget=forms.FileInput(attrs={'accept': '.m3u,.m3u8,.zip'}),
    )
    descartar_vod = forms.BooleanField(
        label='Descartar películas y series', required=False, initial=False,
        help_text='Sin marcar se importa todo. Ojo: hay listas con miles y verificarlas tarda horas.',
    )
    a_fondo = forms.BooleanField(
        label='Prueba a fondo (recomendado)', required=False, initial=True,
        help_text='Además de ver si responde: que tenga sonido, el idioma del audio, la resolución, un formato que '
                  'lean todos los aparatos, que llegue fluido y, en vivo, que no esté congelada. Baja hasta 1 MB '
                  'de cada una y tarda más.',
    )
    solo_espanol = forms.BooleanField(
        label='Solo en español', required=False, initial=True,
        help_text='Descarta lo que se sabe que es de otro idioma (por país, categoría o prefijo) y, con la prueba '
                  'a fondo, lo que tiene el audio en otro idioma (si trae español entre varios, pasa).',
    )
    descartar_adultos = forms.BooleanField(label='Descartar contenido para adultos', required=False, initial=True,
                                           help_text='XXX / +18, por el nombre o la categoría.')
    descartar_sin_logo = forms.BooleanField(label='Descartar los que no tienen logo', required=False)
    categoria_destino = forms.ChoiceField(
        label='Poner todo en la categoría', required=False,
        help_text='Sin elegir: cada canal va a la categoría que dice la lista (group-title).',
    )
    categoria_nueva = _campo_categoria_nueva()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria_destino'].choices = _opciones_de_categorias('La que dice la lista')

    def clean_archivo(self):
        archivo = self.cleaned_data['archivo']
        if not archivo.name.lower().endswith(('.m3u', '.m3u8', '.zip')):
            raise forms.ValidationError('Tiene que ser un archivo .m3u, .m3u8 o .zip.')
        if archivo.size > TAMANIO_MAXIMO:
            raise forms.ValidationError('El archivo pesa más de 20 MB.')
        texto = _texto_del_archivo(archivo)
        if not leer_m3u(texto):
            raise forms.ValidationError('No se encontró ningún canal en el archivo. ¿Es una lista M3U?')
        self.texto = texto
        return archivo

    def opciones(self):
        opciones = {campo: self.cleaned_data[campo] for campo in ('descartar_vod', 'solo_espanol', 'descartar_adultos',
                                                                  'descartar_sin_logo', 'a_fondo')}
        return {**opciones, 'categoria': _nombre_de_la_categoria(self.cleaned_data)}


class QuitarCanalesForm(forms.Form):
    """Quitar de la app los canales elegidos (o todos los del filtro)."""
    motivo = forms.CharField(max_length=200, required=False)


class CanalForm(EstiloBootstrapMixin, forms.ModelForm):
    """Editar un canal desde el panel. La categoría se elige o se crea escribiéndola."""
    nueva_categoria = forms.CharField(
        label='O una categoría nueva', max_length=80, required=False,
        help_text='Si escribís acá, se crea (o se usa la que ya se llame así) en vez de la de arriba.',
    )
    nueva_fuente = forms.CharField(
        label='Agregar una fuente', max_length=1000, required=False,
        validators=[URLValidator(schemes=['http', 'https', 'rtsp', 'rtsps'])],
        help_text='Una dirección más para este canal (.m3u8, video directo, YouTube, Twitch...). '
                  'Se prueba al guardar.',
    )

    class Meta:
        model = Canal
        fields = ['nombre', 'logo', 'numero', 'categoria', 'contenido', 'idioma', 'pais', 'orden',
                  'activo', 'motivo_quitado']
        labels = {'activo': 'Se muestra en la app', 'motivo_quitado': 'Si no se muestra, por qué'}
        widgets = {'logo': forms.URLInput(attrs={'placeholder': 'https://.../logo.png'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].queryset = Categoria.objects.order_by('nombre')
        self.fields['categoria'].required = False
        self.fields['pais'].widget.attrs.update({'maxlength': 2, 'style': 'text-transform:uppercase'})

    def clean_pais(self):
        return self.cleaned_data['pais'].strip().upper()

    def clean_nueva_fuente(self):
        url = self.cleaned_data['nueva_fuente'].strip()
        if url and Fuente.objects.filter(canal=self.instance, url=url).exists():
            raise forms.ValidationError('Este canal ya tiene esa dirección.')
        return url

    def clean(self):
        datos = super().clean()
        if datos.get('activo'):
            datos['motivo_quitado'] = ''
        nueva = (datos.get('nueva_categoria') or '').strip()
        if nueva:
            datos['categoria'] = organizar.categoria_por_nombre(nueva)
            self.instance.categoria = datos['categoria']
        return datos


FuentesFormSet = forms.modelformset_factory(
    Fuente, fields=['prioridad', 'activa'], extra=0, can_delete=True,
    widgets={'prioridad': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'style': 'width:5rem',
                                                   'min': 0}),
             'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'})},
)


class ProbarLinkForm(EstiloBootstrapMixin, forms.Form):
    """Una dirección para ver si anda (y, opcionalmente, cómo pedirla)."""
    url = forms.CharField(
        label='Dirección', max_length=1000,
        validators=[URLValidator(schemes=['http', 'https', 'rtsp', 'rtsps'])],
        widget=forms.URLInput(attrs={'placeholder': 'https://.../playlist.m3u8, http://servidor:8080/..., youtube.com/...',
                                     'autofocus': True}),
    )
    user_agent = forms.CharField(label='User-Agent (opcional)', max_length=300, required=False,
                                 help_text='Solo si el canal lo exige. Si no, se prueba como la app y como VLC.')
    referer = forms.CharField(label='Referer (opcional)', max_length=500, required=False)


class CanalNuevoForm(EstiloBootstrapMixin, forms.ModelForm):
    """Los datos del canal que se crea a mano con una dirección ya probada."""
    nueva_categoria = forms.CharField(label='O una categoría nueva', max_length=80, required=False)

    class Meta:
        model = Canal
        fields = ['nombre', 'logo', 'numero', 'categoria', 'contenido', 'idioma', 'pais']
        widgets = {'logo': forms.URLInput(attrs={'placeholder': 'https://.../logo.png'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].queryset = Categoria.objects.order_by('nombre')
        self.fields['categoria'].required = False
        self.fields['pais'].widget.attrs.update({'maxlength': 2, 'style': 'text-transform:uppercase'})

    def clean_pais(self):
        return self.cleaned_data['pais'].strip().upper()

    def clean(self):
        datos = super().clean()
        nueva = (datos.get('nueva_categoria') or '').strip()
        if nueva:
            datos['categoria'] = organizar.categoria_por_nombre(nueva)
            self.instance.categoria = datos['categoria']
        return datos
