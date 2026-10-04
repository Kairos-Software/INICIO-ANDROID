"""
Por ahora los canales se administran desde /admin/ (Django admin). Más
adelante tendrán sus pantallas en el panel web.
"""

from django.contrib import admin

from .models import Canal, Categoria, Fuente


class FuenteInline(admin.TabularInline):
    model = Fuente
    extra = 1
    fields = ['prioridad', 'url', 'tipo', 'activa', 'origen']


@admin.register(Canal)
class CanalAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'numero', 'categoria', 'activo', 'orden', 'cantidad_fuentes']
    list_filter = ['activo', 'categoria']
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
