"""
Editar canales y fuentes puntuales se hace desde /admin/ (Django admin).
Importar listas, verificar fuentes y quitar canales está en el panel: /canales/.
"""

from django.contrib import admin

from .models import Canal, Categoria, Fuente


class FuenteInline(admin.TabularInline):
    model = Fuente
    extra = 1
    fields = ['prioridad', 'url', 'tipo', 'activa', 'estado', 'error', 'verificada', 'user_agent', 'origen']
    readonly_fields = ['estado', 'error', 'verificada']


@admin.register(Canal)
class CanalAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'numero', 'categoria', 'idioma', 'pais', 'activo', 'orden', 'cantidad_fuentes']
    list_filter = ['activo', 'idioma', 'categoria']
    list_editable = ['activo', 'orden']
    search_fields = ['nombre', 'tvg_id']
    inlines = [FuenteInline]

    @admin.display(description='fuentes')
    def cantidad_fuentes(self, canal):
        return canal.fuentes.count()

    def save_model(self, request, obj, form, change):
        obj.marcar_autor(request.user)
        super().save_model(request, obj, form, change)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'orden']
    list_editable = ['orden']

    def save_model(self, request, obj, form, change):
        obj.marcar_autor(request.user)
        super().save_model(request, obj, form, change)
