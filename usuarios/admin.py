"""
Admin de Django (/admin/) — herramienta técnica para el equipo de desarrollo.
Los usuarios finales gestionan todo desde las pantallas propias del sistema.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CodigoRecuperacion, PermisoIndividual, Rol, Usuario


class PermisoIndividualInline(admin.TabularInline):
    model = PermisoIndividual
    extra = 0


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'rol', 'is_active', 'is_superuser')
    list_filter = ('is_active', 'is_superuser', 'rol')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'numero_documento')
    ordering = ('username',)
    readonly_fields = ('date_joined', 'last_login', 'modificado', 'creado_por')
    inlines = [PermisoIndividualInline]

    fieldsets = (
        ('Acceso', {'fields': ('username', 'password', 'email', 'rol', 'is_active', 'debe_cambiar_password')}),
        ('Datos personales', {'fields': (
            'first_name', 'last_name', 'tipo_documento', 'numero_documento',
            'fecha_nacimiento', 'genero', 'foto',
        )}),
        ('Contacto', {'fields': ('telefono', 'telefono_alternativo', 'emergencia_nombre', 'emergencia_telefono')}),
        ('Domicilio', {'fields': ('calle', 'numero', 'piso_depto', 'localidad', 'provincia', 'codigo_postal', 'pais')}),
        ('Datos laborales', {'fields': ('puesto', 'area', 'fecha_ingreso', 'notas_internas')}),
        ('Técnico', {'classes': ('collapse',), 'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Auditoría', {'fields': ('date_joined', 'last_login', 'modificado', 'creado_por')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('username', 'email', 'rol', 'password1', 'password2')}),
    )


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion', 'modificado')
    search_fields = ('nombre',)


@admin.register(CodigoRecuperacion)
class CodigoRecuperacionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'creado', 'usado', 'intentos')
    readonly_fields = ('usuario', 'codigo_hash', 'creado', 'usado', 'intentos')
