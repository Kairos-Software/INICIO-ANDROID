from django.contrib import admin

from .models import TokenAcceso


@admin.register(TokenAcceso)
class TokenAccesoAdmin(admin.ModelAdmin):
    """Ver quién tiene sesión abierta en la app y, si hace falta, cerrarla (borrar el token)."""
    list_display = ['usuario', 'dispositivo', 'creado', 'ultimo_uso']
    search_fields = ['usuario__username', 'dispositivo']
    readonly_fields = ['usuario', 'dispositivo', 'creado', 'ultimo_uso']
    exclude = ['clave_hash', 'huella_password']

    def has_add_permission(self, request):
        return False   # los tokens solo se crean iniciando sesión desde la app
