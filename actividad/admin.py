from django.contrib import admin

from .models import RegistroActividad


@admin.register(RegistroActividad)
class RegistroActividadAdmin(admin.ModelAdmin):
    """Solo lectura: el registro no se edita ni se borra a mano."""
    list_display = ('fecha', 'usuario_texto', 'accion', 'modulo', 'descripcion', 'ip')
    list_filter = ('accion', 'modulo')
    search_fields = ('descripcion', 'usuario_texto', 'objeto_texto')
    date_hierarchy = 'fecha'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
