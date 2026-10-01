import uuid
from datetime import timedelta
from pathlib import Path

from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin,
)
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from .catalogo_permisos import CODIGOS_PERMISOS, DESCRIPCION_PERMISO


# ══════════════════════════════════════════════════════════════════
#  ROL — paquete de permisos que se asigna a un usuario
# ══════════════════════════════════════════════════════════════════

class Rol(models.Model):
    nombre = models.CharField(max_length=60, unique=True)
    descripcion = models.TextField('descripción', blank=True)
    # Lista de códigos del catálogo, ej: ["ver_usuarios", "crear_usuarios"]
    permisos = models.JSONField(default=list, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    modificado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'rol'
        verbose_name_plural = 'roles'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    def get_permisos(self):
        """Códigos concedidos (ignora los que ya no existen en el catálogo)."""
        return set(self.permisos or []) & CODIGOS_PERMISOS

    def set_permisos(self, codigos):
        """Reemplaza los permisos (no guarda: llamar a save())."""
        self.permisos = sorted(set(codigos) & CODIGOS_PERMISOS)


# ══════════════════════════════════════════════════════════════════
#  USUARIO
# ══════════════════════════════════════════════════════════════════

def _ruta_foto_usuario(instance, filename):
    # Nombre aleatorio: no depende del username (que puede cambiar) y no
    # se puede adivinar la URL de la foto de otro usuario.
    return f'usuarios/fotos/{uuid.uuid4().hex}{Path(filename).suffix.lower()}'


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _crear(self, username, email, password, **extra):
        if not username:
            raise ValueError('El nombre de usuario es obligatorio.')
        email = self.normalize_email(email).lower() if email else None
        usuario = self.model(username=username.strip(), email=email, **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, username, email=None, password=None, **extra):
        extra.setdefault('is_staff', False)
        extra.setdefault('is_superuser', False)
        return self._crear(username, email, password, **extra)

    def create_superuser(self, username, email=None, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('is_active', True)
        return self._crear(username, email, password, **extra)

    def get_by_natural_key(self, username):
        # El login no distingue mayúsculas: "Juan" y "juan" son el mismo usuario.
        return self.get(username__iexact=username)


class Usuario(AbstractBaseUser, PermissionsMixin):

    class TipoDocumento(models.TextChoices):
        DNI = 'dni', 'DNI'
        CUIL_CUIT = 'cuil_cuit', 'CUIL / CUIT'
        PASAPORTE = 'pasaporte', 'Pasaporte'
        OTRO = 'otro', 'Otro'

    class Genero(models.TextChoices):
        MASCULINO = 'masculino', 'Masculino'
        FEMENINO = 'femenino', 'Femenino'
        OTRO = 'otro', 'Otro'
        NO_INFORMA = 'no_informa', 'Prefiere no decir'

    # ── Acceso al sistema ─────────────────────────────────────────
    username = models.CharField(
        'nombre de usuario', max_length=150, unique=True,
        validators=[UnicodeUsernameValidator()],
        help_text='Letras, números y los caracteres @ . + - _',
    )
    email = models.EmailField(
        'email', null=True, blank=True,
        help_text='Se usa para iniciar sesión y para recuperar la contraseña.',
    )
    rol = models.ForeignKey(
        Rol, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='usuarios',
    )
    is_active = models.BooleanField(
        'activo', default=True,
        help_text='Un usuario inactivo no puede iniciar sesión.',
    )
    is_staff = models.BooleanField(
        'acceso al admin de Django', default=False,
        help_text='Solo para el equipo técnico.',
    )
    debe_cambiar_password = models.BooleanField(
        'debe cambiar la contraseña', default=False,
        help_text='Se le pide una contraseña nueva al iniciar sesión.',
    )

    # ── Datos personales ──────────────────────────────────────────
    first_name = models.CharField('nombre/s', max_length=150, blank=True)
    last_name = models.CharField('apellido/s', max_length=150, blank=True)
    tipo_documento = models.CharField(
        'tipo de documento', max_length=15,
        choices=TipoDocumento.choices, blank=True,
    )
    numero_documento = models.CharField('número de documento', max_length=30, blank=True)
    fecha_nacimiento = models.DateField('fecha de nacimiento', null=True, blank=True)
    genero = models.CharField('género', max_length=15, choices=Genero.choices, blank=True)
    foto = models.ImageField('foto de perfil', upload_to=_ruta_foto_usuario, blank=True)

    # ── Contacto ──────────────────────────────────────────────────
    telefono = models.CharField('teléfono', max_length=30, blank=True)
    telefono_alternativo = models.CharField('teléfono alternativo', max_length=30, blank=True)

    # ── Domicilio ─────────────────────────────────────────────────
    calle = models.CharField(max_length=150, blank=True)
    numero = models.CharField('número', max_length=20, blank=True)
    piso_depto = models.CharField('piso / depto', max_length=30, blank=True)
    localidad = models.CharField(max_length=100, blank=True)
    provincia = models.CharField(max_length=100, blank=True)
    codigo_postal = models.CharField('código postal', max_length=15, blank=True)
    pais = models.CharField('país', max_length=100, blank=True, default='Argentina')

    # ── Contacto de emergencia ────────────────────────────────────
    emergencia_nombre = models.CharField('contacto de emergencia', max_length=150, blank=True)
    emergencia_telefono = models.CharField('teléfono de emergencia', max_length=30, blank=True)

    # ── Datos laborales / internos ────────────────────────────────
    puesto = models.CharField('puesto / cargo', max_length=100, blank=True)
    area = models.CharField('área', max_length=100, blank=True)
    fecha_ingreso = models.DateField('fecha de ingreso', null=True, blank=True)
    notas_internas = models.TextField(
        'notas internas', blank=True,
        help_text='Solo las ve quien gestiona usuarios, nunca el propio usuario.',
    )

    # ── Auditoría ─────────────────────────────────────────────────
    date_joined = models.DateTimeField('fecha de alta', default=timezone.now)
    modificado = models.DateTimeField('última modificación', auto_now=True)
    creado_por = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='creado por',
    )

    objects = UsuarioManager()

    USERNAME_FIELD = 'username'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'
        ordering = ['username']
        constraints = [
            # Únicos sin distinguir mayúsculas ("Juan" = "juan")
            models.UniqueConstraint(
                Lower('username'), name='usuario_username_unico_ci',
                violation_error_message='Ya existe un usuario con ese nombre de usuario.',
            ),
            models.UniqueConstraint(
                Lower('email'), name='usuario_email_unico_ci',
                violation_error_message='Ya existe un usuario con ese email.',
            ),
        ]

    def __str__(self):
        return self.username

    def clean(self):
        super().clean()
        # Un email vacío se guarda como NULL para no chocar con el unique
        self.email = self.__class__.objects.normalize_email(self.email).lower() if self.email else None

    def save(self, *args, **kwargs):
        if not self.email:
            self.email = None
        super().save(*args, **kwargs)

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.username

    def get_short_name(self):
        return self.first_name or self.username

    # Texto que se muestra cuando el usuario no tiene rol: sus permisos se
    # eligen uno por uno (pantalla de permisos individuales).
    TEXTO_SIN_ROL = 'Personalizado'

    @property
    def tiene_permisos_personalizados(self):
        return not self.is_superuser and self.rol_id is None

    @property
    def descripcion_rol(self):
        """'Superusuario', el nombre del rol, o 'Personalizado' si no tiene rol."""
        if self.is_superuser:
            return 'Superusuario'
        return self.rol.nombre if self.rol_id else self.TEXTO_SIN_ROL

    @property
    def iniciales(self):
        """Para el avatar cuando no hay foto: 'Juan Pérez' -> 'JP'."""
        partes = [p for p in (self.first_name, self.last_name) if p]
        if partes:
            return ''.join(p[0] for p in partes).upper()
        return self.username[:2].upper()

    @property
    def edad(self):
        if not self.fecha_nacimiento:
            return None
        hoy = timezone.localdate()
        nac = self.fecha_nacimiento
        return hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))

    @property
    def direccion_completa(self):
        calle = ' '.join(p for p in (self.calle, self.numero) if p)
        partes = [calle, self.piso_depto, self.localidad, self.provincia, self.pais]
        return ', '.join(p for p in partes if p)


# ══════════════════════════════════════════════════════════════════
#  PERMISO INDIVIDUAL — excepción al rol para un usuario puntual
# ══════════════════════════════════════════════════════════════════

class PermisoIndividual(models.Model):
    """
    concedido=True  -> tiene el permiso aunque su rol no lo tenga.
    concedido=False -> NO tiene el permiso aunque su rol sí lo tenga.
    Si no hay fila, manda el rol.
    """
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='permisos_individuales')
    # Código del catálogo (sin `choices` a propósito: sumar permisos al
    # catálogo no debe generar migraciones)
    permiso = models.CharField(max_length=60)
    concedido = models.BooleanField()

    class Meta:
        verbose_name = 'permiso individual'
        verbose_name_plural = 'permisos individuales'
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'permiso'], name='permiso_individual_unico'),
        ]

    def __str__(self):
        estado = 'PERMITE' if self.concedido else 'DENIEGA'
        return f'{self.usuario} — {estado} — {self.permiso}'

    @property
    def descripcion(self):
        return DESCRIPCION_PERMISO.get(self.permiso, self.permiso)


# ══════════════════════════════════════════════════════════════════
#  RECUPERACIÓN DE CONTRASEÑA — código de 6 dígitos enviado por mail
# ══════════════════════════════════════════════════════════════════

VIGENCIA_CODIGO_RECUPERACION = timedelta(minutes=15)
INTENTOS_MAXIMOS_CODIGO_RECUPERACION = 5


class CodigoRecuperacion(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='codigos_recuperacion')
    # Se guarda el hash, nunca el código en claro (igual que las contraseñas)
    codigo_hash = models.CharField(max_length=128)
    creado = models.DateTimeField(auto_now_add=True)
    usado = models.BooleanField(default=False)
    intentos = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'código de recuperación'
        verbose_name_plural = 'códigos de recuperación'
        ordering = ['-creado']

    def __str__(self):
        return f'{self.usuario} · {timezone.localtime(self.creado):%d/%m/%Y %H:%M}'

    @property
    def vencido(self):
        return timezone.now() > self.creado + VIGENCIA_CODIGO_RECUPERACION

    @property
    def vigente(self):
        return (
            not self.usado
            and not self.vencido
            and self.intentos < INTENTOS_MAXIMOS_CODIGO_RECUPERACION
        )
