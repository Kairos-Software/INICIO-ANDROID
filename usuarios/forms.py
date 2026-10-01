from django import forms
from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, SetPasswordForm

from herramientas.formularios import CampoFecha, EstiloBootstrapMixin

from . import servicios
from .models import Rol, Usuario

TAMANIO_MAXIMO_FOTO_MB = 3


def ip_cliente(request):
    # Detrás de nginx la IP real llega en X-Real-IP (nginx la sobrescribe
    # siempre con `proxy_set_header X-Real-IP $remote_addr`). No se usa el
    # primer valor de X-Forwarded-For porque el navegador lo puede inventar.
    return request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR', '')


# ══════════════════════════════════════════════════════════════════
#  LOGIN
# ══════════════════════════════════════════════════════════════════

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Usuario o email',
        max_length=254,
        widget=forms.TextInput(attrs={
            'autofocus': True,
            'autocomplete': 'username',
            'autocapitalize': 'none',
            'spellcheck': 'false',
        }),
    )
    password = forms.CharField(
        label='Contraseña',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )
    recordarme = forms.BooleanField(label='Mantener la sesión iniciada', required=False)

    error_messages = {
        'invalid_login': 'Usuario o contraseña incorrectos.',
        'inactive': 'Esta cuenta está desactivada. Consultá con un administrador.',
        'bloqueado': (
            'Demasiados intentos fallidos. Esperá %(minutos)s minutos '
            'o recuperá tu contraseña.'
        ),
    }

    def clean(self):
        identificador = self.cleaned_data.get('username')
        ip = ip_cliente(self.request) if self.request else ''

        if servicios.login_bloqueado(identificador, ip):
            raise forms.ValidationError(
                self.error_messages['bloqueado'],
                code='bloqueado',
                params={'minutos': settings.LOGIN_BLOQUEO_MINUTOS},
            )
        try:
            cleaned = super().clean()
        except forms.ValidationError:
            servicios.registrar_login_fallido(identificador, ip)
            raise
        servicios.limpiar_login_fallidos(identificador, ip)
        return cleaned


# ══════════════════════════════════════════════════════════════════
#  GESTIÓN DE USUARIOS
# ══════════════════════════════════════════════════════════════════

# Campos agrupados por sección, en el orden en que se muestran.
# Las pantallas de alta, edición y detalle usan esta misma lista.
SECCIONES_USUARIO = [
    ('Acceso al sistema', ['username', 'email', 'rol']),
    ('Datos personales', [
        'first_name', 'last_name', 'tipo_documento', 'numero_documento',
        'fecha_nacimiento', 'genero',
    ]),
    ('Contacto', ['telefono', 'telefono_alternativo']),
    ('Domicilio', [
        'calle', 'numero', 'piso_depto', 'localidad', 'provincia',
        'codigo_postal', 'pais',
    ]),
    ('Contacto de emergencia', ['emergencia_nombre', 'emergencia_telefono']),
    ('Datos laborales', ['puesto', 'area', 'fecha_ingreso', 'notas_internas']),
]
CAMPOS_USUARIO = [campo for _, campos in SECCIONES_USUARIO for campo in campos] + ['foto']

# Lo que cada usuario puede editar de sí mismo en "Mi perfil". Lo demás
# (usuario, rol, documento, datos laborales) lo maneja la administración.
SECCIONES_PERFIL = [
    ('Datos personales', ['first_name', 'last_name', 'email', 'fecha_nacimiento', 'genero']),
    ('Contacto', ['telefono', 'telefono_alternativo']),
    ('Domicilio', [
        'calle', 'numero', 'piso_depto', 'localidad', 'provincia',
        'codigo_postal', 'pais',
    ]),
    ('Contacto de emergencia', ['emergencia_nombre', 'emergencia_telefono']),
]
CAMPOS_PERFIL = [campo for _, campos in SECCIONES_PERFIL for campo in campos] + ['foto']

# Datos que el usuario ve en su perfil pero no puede editar
SECCIONES_PERFIL_SOLO_LECTURA = [
    ('Datos de la cuenta', ['username', 'tipo_documento', 'numero_documento', 'puesto', 'area', 'fecha_ingreso']),
]

# Ancho de cada campo en la grilla (Bootstrap). Los que no están: col-md-6
ANCHO_CAMPOS = {
    'rol': 'col-md-12',
    'tipo_documento': 'col-md-4',
    'numero_documento': 'col-md-4',
    'fecha_nacimiento': 'col-md-4',
    'calle': 'col-md-6',
    'numero': 'col-md-3',
    'piso_depto': 'col-md-3',
    'localidad': 'col-md-6',
    'provincia': 'col-md-6',
    'codigo_postal': 'col-md-4',
    'pais': 'col-md-8',
    'fecha_ingreso': 'col-md-4',
    'puesto': 'col-md-4',
    'area': 'col-md-4',
    'notas_internas': 'col-12',
}


def datos_usuario(usuario, secciones=SECCIONES_USUARIO):
    """
    Datos del usuario listos para mostrar (pantallas de detalle y perfil),
    agrupados como `secciones`: [(título, [(etiqueta, valor), ...])].
    """
    resultado = []
    for titulo, campos in secciones:
        filas = []
        for nombre in campos:
            campo = Usuario._meta.get_field(nombre)
            if campo.choices:
                valor = getattr(usuario, f'get_{nombre}_display')()
            else:
                valor = getattr(usuario, nombre)
            if hasattr(valor, 'strftime'):
                valor = valor.strftime('%d/%m/%Y')
            filas.append((campo.verbose_name, valor))
        resultado.append((titulo, filas))
    return resultado


class UsuarioForm(EstiloBootstrapMixin, forms.ModelForm):
    """Datos del usuario (sin contraseña). Base del alta, la edición y el perfil."""

    SECCIONES = SECCIONES_USUARIO

    class Meta:
        model = Usuario
        fields = CAMPOS_USUARIO
        widgets = {
            'fecha_nacimiento': CampoFecha(),
            'fecha_ingreso': CampoFecha(),
            'notas_internas': forms.Textarea(attrs={'rows': 3}),
            'foto': forms.FileInput(attrs={'accept': 'image/*'}),
            'username': forms.TextInput(attrs={'autocapitalize': 'none', 'spellcheck': 'false'}),
        }

    quitar_foto = forms.BooleanField(label='Quitar la foto actual', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'rol' in self.fields:
            self.fields['rol'].empty_label = 'Personalizado (elegir los permisos uno por uno)'
            self.fields['rol'].help_text = (
                'Un rol trae un paquete de permisos ya armado. Si esta persona '
                'necesita otra combinación, elegí "Personalizado" y después '
                'marcale sus permisos.'
            )
        self.fields['email'].help_text = 'Necesario para que pueda recuperar su contraseña.'

    def secciones(self):
        """[(título, [(campo, ancho), ...]), ...] para dibujar el formulario por secciones."""
        return [
            (titulo, [(self[c], ANCHO_CAMPOS.get(c, 'col-md-6')) for c in campos])
            for titulo, campos in self.SECCIONES
        ]

    # Únicos sin distinguir mayúsculas. La base de datos también lo impide,
    # pero validarlo acá muestra el error junto al campo que corresponde.
    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if Usuario.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Ya existe un usuario con ese nombre de usuario.')
        return username

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if email and Usuario.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Ya existe un usuario con ese email.')
        return email or None

    def clean_foto(self):
        foto = self.cleaned_data.get('foto')
        if foto and hasattr(foto, 'size') and foto.size > TAMANIO_MAXIMO_FOTO_MB * 1024 * 1024:
            raise forms.ValidationError(f'La foto no puede pesar más de {TAMANIO_MAXIMO_FOTO_MB} MB.')
        return foto

    def clean(self):
        cleaned = super().clean()
        # "Quitar foto" sin subir una nueva: False le indica a Django que vacíe el campo
        if cleaned.get('quitar_foto') and 'foto' not in self.changed_data:
            cleaned['foto'] = False
        return cleaned


class PerfilForm(UsuarioForm):
    """Lo que el propio usuario puede editar de sí mismo."""

    SECCIONES = SECCIONES_PERFIL

    class Meta(UsuarioForm.Meta):
        fields = CAMPOS_PERFIL


class CambiarPasswordForm(EstiloBootstrapMixin, PasswordChangeForm):
    """Cambio de la propia contraseña (pide la actual)."""

    error_messages = {
        **PasswordChangeForm.error_messages,
        'password_incorrect': 'La contraseña actual no es correcta.',
        'password_mismatch': 'Las contraseñas no coinciden.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].label = 'Contraseña actual'
        self.fields['new_password1'].label = 'Contraseña nueva'
        self.fields['new_password2'].label = 'Repetir contraseña nueva'
        self.fields['new_password2'].help_text = ''

    def clean_new_password1(self):
        nueva = self.cleaned_data.get('new_password1')
        if nueva and self.user.check_password(nueva):
            raise forms.ValidationError('La contraseña nueva tiene que ser distinta de la actual.')
        return nueva


class UsuarioCrearForm(UsuarioForm):
    """
    Alta de usuario. La contraseña inicial puede ser cualquiera (no se le
    exigen las reglas de seguridad): es solo para el primer ingreso, y con
    "pedirle que la cambie" la persona elige la suya, que sí se valida.
    """

    password1 = forms.CharField(
        label='Contraseña inicial', strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text='Puede ser cualquiera: es solo para su primer ingreso.',
    )
    password2 = forms.CharField(
        label='Repetir contraseña inicial', strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    debe_cambiar_password = forms.BooleanField(
        label='Pedirle que elija su propia contraseña en el primer ingreso',
        required=False, initial=True,
    )

    class Meta(UsuarioForm.Meta):
        fields = CAMPOS_USUARIO + ['debe_cambiar_password']

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        return p2


class RestablecerPasswordForm(EstiloBootstrapMixin, forms.Form):
    password1 = forms.CharField(
        label='Contraseña nueva', strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label='Repetir contraseña nueva', strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    obligar_cambio = forms.BooleanField(
        label='Pedirle que la cambie en su próximo ingreso',
        required=False, initial=True,
    )

    def __init__(self, usuario, *args, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2:
            if p1 != p2:
                self.add_error('password2', 'Las contraseñas no coinciden.')
            else:
                try:
                    password_validation.validate_password(p1, self.usuario)
                except forms.ValidationError as error:
                    self.add_error('password1', error)
        return cleaned


# ══════════════════════════════════════════════════════════════════
#  ROLES
#  Los permisos no son un campo del formulario: llegan como una lista de
#  checkboxes llamados "permisos" y los procesa servicios.guardar_rol.
# ══════════════════════════════════════════════════════════════════

class RolForm(EstiloBootstrapMixin, forms.ModelForm):

    class Meta:
        model = Rol
        fields = ['nombre', 'descripcion']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 2})}
        help_texts = {'descripcion': 'Para qué sirve este rol o a quién se le asigna.'}
        error_messages = {'nombre': {'unique': 'Ya existe un rol con ese nombre.'}}


# ══════════════════════════════════════════════════════════════════
#  RECUPERACIÓN DE CONTRASEÑA
# ══════════════════════════════════════════════════════════════════

class SolicitarRecuperacionForm(EstiloBootstrapMixin, forms.Form):
    identificador = forms.CharField(
        label='Usuario o email',
        max_length=254,
        widget=forms.TextInput(attrs={
            'autofocus': True, 'autocomplete': 'username',
            'autocapitalize': 'none', 'spellcheck': 'false',
        }),
    )

    def clean_identificador(self):
        return self.cleaned_data['identificador'].strip()


class CodigoRecuperacionForm(EstiloBootstrapMixin, forms.Form):
    codigo = forms.CharField(
        label='Código de 6 dígitos',
        min_length=6, max_length=6,
        widget=forms.TextInput(attrs={
            'autofocus': True, 'inputmode': 'numeric', 'autocomplete': 'one-time-code',
            'pattern': '[0-9]{6}', 'class': 'campo-codigo', 'placeholder': '000000',
        }),
        error_messages={
            'min_length': 'El código tiene 6 dígitos.',
            'max_length': 'El código tiene 6 dígitos.',
        },
    )

    def clean_codigo(self):
        codigo = self.cleaned_data['codigo'].strip()
        if not codigo.isdigit():
            raise forms.ValidationError('El código tiene solo números.')
        return codigo


class NuevaPasswordForm(EstiloBootstrapMixin, SetPasswordForm):
    """Contraseña nueva al recuperar (no pide la actual: ya se verificó el código)."""

    error_messages = {
        **SetPasswordForm.error_messages,
        'password_mismatch': 'Las contraseñas no coinciden.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].label = 'Contraseña nueva'
        self.fields['new_password1'].widget.attrs['autofocus'] = True
        self.fields['new_password2'].label = 'Repetir contraseña nueva'
        self.fields['new_password2'].help_text = ''
